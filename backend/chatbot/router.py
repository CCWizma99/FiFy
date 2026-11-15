import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from google.genai import errors
from backend.config import settings
from backend.chatbot import service
from backend.chatbot.limits import UsageLimiter

router = APIRouter()
STATIC = Path(__file__).with_name('static')
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000, strict=True)]


class Turn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'assistant']
    content: Text


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bot_id: Literal['fify-demo']
    message: Text
    history: list[Turn] = Field(default_factory=list, max_length=8)


class Reply(BaseModel):
    text: str = Field(max_length=2000)


class ChatResponse(BaseModel):
    reply: Reply


@lru_cache
def get_limiter():
    return UsageLimiter(settings.chatbot_usage_db, settings.chatbot_rate_limit, settings.chatbot_daily_limit)


@router.post('/api/chatbot/message', response_model=ChatResponse)
async def message(payload: ChatRequest, request: Request, limiter=Depends(get_limiter)):
    if not settings.google_api_key:
        raise HTTPException(503, 'The assistant is not configured yet. Please try again later.')
    try:
        limited = limiter.consume(request.client.host if request.client else 'unknown')
    except Exception:
        raise HTTPException(503, 'The assistant is temporarily unavailable. Please try again later.') from None
    if limited:
        detail, seconds = limited
        raise HTTPException(429, detail, headers={'Retry-After': str(seconds)})
    try:
        text = await asyncio.wait_for(service.generate_reply(payload.message, payload.history), timeout=25)
        return ChatResponse(reply=Reply(text=text))
    except (asyncio.TimeoutError, TimeoutError):
        raise HTTPException(504, 'The assistant took too long to respond. Please try again.') from None
    except errors.APIError as exc:
        if exc.code == 429:
            raise HTTPException(429, 'The AI service is busy or its quota is exhausted. Please try again later.', headers={'Retry-After': '60'}) from None
        raise HTTPException(502, 'The AI service is temporarily unavailable. Please try again later.') from None
    except Exception:
        raise HTTPException(502, 'The assistant could not respond. Please try again later.') from None


@router.get('/widget.js', include_in_schema=False)
async def widget_script():
    return FileResponse(STATIC / 'widget.js', media_type='application/javascript', headers={'Cache-Control': 'no-cache'})


@router.get('/chatbot/frame', include_in_schema=False)
async def widget_frame():
    return FileResponse(STATIC / 'frame.html', headers={
        'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'",
        'Referrer-Policy': 'no-referrer',
    })


@router.get('/chatbot/frame.js', include_in_schema=False)
async def widget_frame_script():
    return FileResponse(STATIC / 'frame.js', media_type='application/javascript')


@router.get('/chatbot/frame.css', include_in_schema=False)
async def widget_frame_style():
    return FileResponse(STATIC / 'frame.css', media_type='text/css')


@router.get('/embed-test.html', include_in_schema=False)
async def embed_demo():
    return FileResponse(STATIC / 'embed-test.html')
