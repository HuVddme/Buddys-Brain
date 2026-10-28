"""Use real FastAPI routes with fake storage/embeddings and no network access."""
import socket
import sys
from types import ModuleType
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

database = ModuleType("app.database")
database.collection = Mock()
sys.modules["app.database"] = database
embeddings = ModuleType("app.utils.embeddings")
embeddings.get_embedding = Mock(return_value=[0.1, 0.2])
sys.modules["app.utils.embeddings"] = embeddings

from app.main import app
from app.routes import resources, search


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Tests must not use the network")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("RESOURCE_ADMIN_TOKEN", raising=False)
    for variable in ("OPENAI_MODEL", "OPENAI_REASONING_EFFORT", "OPENAI_MAX_COMPLETION_TOKENS"):
        monkeypatch.delenv(variable, raising=False)
    from app.utils.processing import get_ai_client
    get_ai_client.cache_clear()
    yield
    get_ai_client.cache_clear()


@pytest.fixture
def db(monkeypatch):
    collection = Mock()
    collection.insert_one = AsyncMock()
    collection.insert_many = AsyncMock()
    collection.find_one = AsyncMock()
    collection.delete_one = AsyncMock()
    monkeypatch.setattr(resources, "collection", collection)
    monkeypatch.setattr(search, "collection", collection)
    return collection


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
