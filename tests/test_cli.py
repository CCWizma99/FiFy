from unittest.mock import patch
from backend import cli


def test_cli_uses_configured_host_and_port(monkeypatch):
    monkeypatch.setattr(cli.settings, 'api_host', '127.0.0.2')
    monkeypatch.setattr(cli.settings, 'api_port', 8123)
    with patch.object(cli.uvicorn, 'run') as run:
        cli.main()
    run.assert_called_once_with('backend.main:app', host='127.0.0.2', port=8123,
                                reload=False, loop='asyncio')


def test_run_server_delegates():
    import runpy
    with patch('backend.cli.main') as main:
        runpy.run_path('run_server.py', run_name='__main__')
    main.assert_called_once_with()
