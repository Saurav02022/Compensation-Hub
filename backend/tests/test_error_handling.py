from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from compensation_hub.main import create_app


def failing_session_factory() -> None:
    raise OperationalError(
        "SELECT 1", {}, ConnectionRefusedError("connection to server at localhost failed")
    )


def test_database_outage_returns_controlled_503_without_details() -> None:
    app = create_app()
    app.state.session_factory = failing_session_factory
    client = TestClient(app)

    response = client.get("/employees")

    assert response.status_code == 503
    assert response.json() == {"detail": "The database is unavailable."}
    assert "localhost" not in response.text


def test_health_does_not_depend_on_the_database() -> None:
    app = create_app()
    app.state.session_factory = failing_session_factory

    assert TestClient(app).get("/health").status_code == 200
