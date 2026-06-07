"""Pytest fixtures: isolated sqlite DB + async HTTP client over the ASGI app."""
import os
import tempfile

import pytest

# Use a temp sqlite file per test session before importing the app/config.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["ENVIRONMENT"] = "development"


@pytest.fixture
async def client():
    import httpx

    from app.core.database import init_db
    from app.main import app

    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
