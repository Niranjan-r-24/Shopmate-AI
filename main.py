"""
ShopMate AI - Application Entrypoint for Google Cloud Run and Local Production.

This module exposes the ASGI application instance `app` from `app.main`
so the server can be started using the standard Cloud Run command:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import os
import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    host = os.environ.get("HOST", settings.HOST)
    uvicorn.run("main:app", host=host, port=port)
