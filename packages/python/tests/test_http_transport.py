import logging

from drtrace_client.transport import HttpTransport  # type: ignore[import]


def test_http_transport_swallows_errors_and_logs(monkeypatch, caplog):
  # Force urlopen to always fail
  import urllib.request as req  # type: ignore[import]

  def boom(*args, **kwargs):
    raise req.URLError("daemon unavailable")

  monkeypatch.setattr(req, "urlopen", boom)

  transport = HttpTransport(
    endpoint="http://localhost:9999/logs/ingest",
    application_id="test-app",
    max_retries=2,
    base_backoff_seconds=0.0,
  )

  with caplog.at_level(logging.WARNING, logger="drtrace_client.transport"):
    transport.send([{"message": "hello"}])

  # We should see at least one warning logged but no exception raised.
  assert any("HTTP transport failed to reach daemon" in msg for msg in caplog.text.splitlines())


