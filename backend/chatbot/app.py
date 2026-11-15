from backend.chatbot.middleware import ChatBodyLimitMiddleware
"""Optional chatbot-only server: no CLIP, Qdrant, crawler, or catalog imports."""
from fastapi import FastAPI
from backend.chatbot.router import router
app = FastAPI(title='FiFy FAQ Assistant')
app.add_middleware(ChatBodyLimitMiddleware)
app.include_router(router)
