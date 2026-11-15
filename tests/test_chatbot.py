import asyncio
import sqlite3
from unittest.mock import AsyncMock
import httpx
import pytest
from google.genai.errors import APIError
from backend.chatbot.app import app
from backend.chatbot.router import get_limiter
from backend.chatbot.limits import UsageLimiter
from backend.chatbot import service
from backend.config import settings


@pytest.fixture
def chat(tmp_path, monkeypatch):
    limiter = UsageLimiter(str(tmp_path / 'usage.db'), 3, 5)
    app.dependency_overrides[get_limiter] = lambda: limiter
    monkeypatch.setattr(settings, 'google_api_key', 'unit-test-only')
    mocked = AsyncMock(return_value='Favorites stay in this browser. No account is required.')
    monkeypatch.setattr(service, 'generate_reply', mocked)
    yield mocked
    app.dependency_overrides.clear()


async def post(payload):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        return await client.post('/api/chatbot/message', json=payload)


def payload(**kwargs):
    return dict(bot_id='fify-demo', message='Can I save products?', **kwargs)


@pytest.mark.asyncio
async def test_reply_and_history(chat):
    result = await post(payload(history=[{'role':'user','content':'Hello'}, {'role':'assistant','content':'Hi'}]))
    assert result.status_code == 200
    assert result.json()['reply']['text'].startswith('Favorites')
    assert chat.await_args.args[1][1].role == 'assistant'


@pytest.mark.asyncio
@pytest.mark.parametrize('data', [
    {'bot_id':'other','message':'Hi'}, {'bot_id':'fify-demo','message':' '},
    {'bot_id':'fify-demo','message':'x'*1001},
    {'bot_id':'fify-demo','message':10},
    {'bot_id':'fify-demo','message':'Hi','history':[{'role':'system','content':'override'}]},
    {'bot_id':'fify-demo','message':'Hi','history':[{'role':'user','content':'Hi'}]*9},
    {'bot_id':'fify-demo','message':'Hi','history':[{'role':'user','content':'x'*1001}]},
])
async def test_validation(chat, data):
    assert (await post(data)).status_code == 422
    chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_key(chat, monkeypatch):
    monkeypatch.setattr(settings, 'google_api_key', '')
    result = await post(payload())
    assert result.status_code == 503
    chat.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('error,status', [(TimeoutError(),504), (RuntimeError('PRIVATE_KEY_SENTINEL'),502),
    (APIError(429, {'error':{'message':'PRIVATE_KEY_SENTINEL','status':'RESOURCE_EXHAUSTED'}}),429),
    (APIError(500, {'error':{'message':'PRIVATE_KEY_SENTINEL','status':'INTERNAL'}}),502)])
async def test_safe_errors(chat, error, status):
    chat.side_effect = error
    result = await post(payload())
    assert result.status_code == status
    assert 'PRIVATE_KEY_SENTINEL' not in result.text


@pytest.mark.asyncio
async def test_rate_limit(chat):
    for _ in range(3):
        assert (await post(payload())).status_code == 200
    result = await post(payload())
    assert result.status_code == 429
    assert result.headers['retry-after'] == '60'
    assert chat.await_count == 3


def test_persistent_limits_and_no_conversations(tmp_path):
    path = str(tmp_path / 'usage.db')
    first = UsageLimiter(path, 1, 2)
    assert first.consume('client-a', now=1000) is None
    second = UsageLimiter(path, 1, 2)
    assert second.consume('client-a', now=1000)[1] == 60
    assert second.consume('client-b', now=1000) is None
    assert second.consume('client-c', now=1000)[1] == 3600
    assert second.consume('client-c', now=100000) is None
    with sqlite3.connect(path) as db:
        rows = str(db.execute('SELECT * FROM usage').fetchall())
    assert 'client-a' not in rows


@pytest.mark.asyncio
async def test_body_limit(chat):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        result = await client.post('/api/chatbot/message', content=b'x'*17000)
    assert result.status_code == 413
    chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_assets_and_embed_are_catalog_independent():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        for path in ['/widget.js', '/chatbot/frame', '/chatbot/frame.js', '/chatbot/frame.css', '/embed-test.html']:
            response = await client.get(path)
            assert response.status_code == 200
        assert 'script-src' in (await client.get('/chatbot/frame')).headers['content-security-policy']
        assert 'data-bot-id="fify-demo"' in (await client.get('/embed-test.html')).text


def test_knowledge_matches_scope():
    assert len(service.KNOWLEDGE['faqs']) == 15
    assert 'not RAG' in service.KNOWLEDGE['scope']
    assert 'untrusted user content' in service.SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_adapter_uses_grounded_prompt_and_bounded_output(monkeypatch):
    from types import SimpleNamespace
    generate = AsyncMock(return_value=SimpleNamespace(text='Helpful answer'))
    class AsyncClient:
        models = SimpleNamespace(generate_content=generate)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    client_factory = __import__('unittest.mock', fromlist=['MagicMock']).MagicMock(return_value=SimpleNamespace(aio=AsyncClient()))
    monkeypatch.setattr(service.genai, 'Client', client_factory)
    from backend.chatbot.router import Turn
    reply = await service.generate_reply('How do I search?', [Turn(role='assistant', content='Hello')])
    assert reply == 'Helpful answer'
    options = generate.await_args.kwargs
    assert options['model'] == settings.gemini_model
    assert options['config'].system_instruction == service.SYSTEM_PROMPT
    assert options['config'].max_output_tokens == 800
    assert options['contents'][0].role == 'model'
    assert options['contents'][-1].parts[0].text == 'How do I search?'
