import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    # Force ProactorEventLoop on Windows for Playwright compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    print("[INFO] Starting FiFy Backend with ProactorEventLoop...")
    # NOTE: reload=True on Windows often forces SelectorEventLoop, 
    # which breaks Playwright. Set to False for scraper stability.
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        loop="asyncio"
    )
