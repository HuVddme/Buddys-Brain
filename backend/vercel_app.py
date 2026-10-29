"""Vercel preserves /api on ingress; mount the existing API at that prefix.

Other hosts continue to run app.main:app at the root without any route changes.
"""
from fastapi import FastAPI

from app.main import app as backend

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", backend)
