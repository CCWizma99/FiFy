"""Shared command-line entry point for the backend."""
import asyncio
import sys
import uvicorn
from backend.config import settings


def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run('backend.main:app', host=settings.api_host, port=settings.api_port,
                reload=False, loop='asyncio')
