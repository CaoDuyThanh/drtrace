from fastapi.testclient import TestClient

from drtrace_service import status as status_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]


def test_status_endpoint_healthy(monkeypatch):
  client = TestClient(app)

  def fake_get_status():
    return {
      "status": "healthy",
      "service_name": "drtrace_daemon",
      "version": "0.1.0",
      "host": "localhost",
      "port": 8001,
    }

  monkeypatch.setattr(status_mod, "get_status", fake_get_status)

  resp = client.get("/status")
  assert resp.status_code == 200
  data = resp.json()
  assert data["status"] == "healthy"
  assert data["service_name"] == "drtrace_daemon"


