from src.main import APP_VERSION, app


def test_service_entrypoint_metadata_and_routes():
    assert APP_VERSION == "4.0.0-alpha"
    assert app.title == "DREAMVFIA Brain Core"

    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/metrics" in paths
    assert any(path.startswith("/api/v1") for path in paths)
