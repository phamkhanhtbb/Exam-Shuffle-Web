"""
Basic health and smoke tests for the ExamShuffling API.
These tests verify the server starts correctly and endpoints respond.
Requires all backend dependencies to be installed (run in CI or with venv).
"""
import pytest

# Skip entire module if server dependencies are missing (e.g. local dev without venv)
pytest.importorskip("prometheus_fastapi_instrumentator", reason="Server dependencies not installed")

from httpx import AsyncClient, ASGITransport
from server import app


@pytest.mark.asyncio
async def test_docs_endpoint():
    """FastAPI /docs should return 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Prometheus /metrics endpoint should return 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_preview_no_file():
    """POST /api/preview without file should return 422 (Unprocessable Entity)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/preview")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_status_not_found():
    """GET /api/status/nonexistent should return 404 or 500 (no DynamoDB in test)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status/nonexistent-job-id")
        # In test env without real DynamoDB, this will fail with 500
        assert response.status_code in (404, 500)
