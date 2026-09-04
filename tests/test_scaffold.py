"""Tests for the initial project scaffold."""

from fastapi.testclient import TestClient

from app.main import app


def test_api_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_application_packages_import() -> None:
    import app.data
    import app.engine
    import app.llm
    import app.models

    assert app.data is not None
    assert app.engine is not None
    assert app.llm is not None
    assert app.models is not None
