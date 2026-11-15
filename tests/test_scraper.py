"""Local profile persistence tests. No model or network calls."""
import json
import pytest
from scraper.site_analyzer import agent


@pytest.fixture
def configs(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, 'CONFIGS_DIR', tmp_path)
    return tmp_path


def layout(selector='.card'):
    return {'product_card_selector': selector, 'fields': {'name': '.title'},
            'listing_url_pattern': 'https://example.test/items'}


def test_missing_profile(configs):
    assert agent.load_config('example.test') is None


def test_persist_and_reload(configs):
    agent.save_variant('example.test', layout())
    profile = agent.load_config('example.test')
    assert profile['site_domain'] == 'example.test'
    assert profile['variants'][0]['fields'] == {'name': '.title'}
    assert json.loads((configs / 'example_test.json').read_text()) == profile


def test_identical_layout_deduplicated(configs):
    agent.save_variant('example.test', layout(), 'https://example.test/a')
    agent.save_variant('example.test', layout(), 'https://example.test/b')
    assert len(agent.load_config('example.test')['variants']) == 1


def test_distinct_layouts_retained(configs):
    agent.save_variant('example.test', layout())
    agent.save_variant('example.test', layout('.tile'))
    changed = layout()
    changed['fields'] = {'name': '.different-title'}
    agent.save_variant('example.test', changed)
    assert [v['id'] for v in agent.load_config('example.test')['variants']] == ['v1', 'v2', 'v3']


def test_legacy_migration_is_persisted_and_idempotent(configs):
    path = configs / 'example_test.json'
    path.write_text(json.dumps(layout()))
    migrated = agent.load_config('example.test')
    assert migrated['variants'][0]['id'] == 'legacy_primary'
    assert migrated['variants'][0]['sample_url'] == layout()['listing_url_pattern']
    assert json.loads(path.read_text()) == migrated
    assert agent.load_config('example.test') == migrated
