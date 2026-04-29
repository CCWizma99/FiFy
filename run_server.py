import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    # Force ProactorEventLoop on Windows for Playwright compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    print("🚀 Starting FiFy Backend with ProactorEventLoop...")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
