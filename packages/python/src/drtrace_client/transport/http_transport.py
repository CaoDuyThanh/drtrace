from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib import error, request

LogRecordDict = Dict[str, Any]


_logger = logging.getLogger("drtrace_client.transport")


@dataclass
class HttpTransport:
  """
  Minimal HTTP transport that posts log batches to the local daemon.

  This uses the Python standard library only. Network failures are
  handled with a small retry loop and logged at WARNING level, but
  never raise back to the caller.
  """

  endpoint: str
  application_id: str
  max_retries: int = 3
  base_backoff_seconds: float = 0.1

  def send(self, batch: List[LogRecordDict]) -> None:
    if not batch:
      return

    payload = {
      "application_id": self.application_id,
      "logs": batch,
    }
    data = json.dumps(payload).encode("utf-8")

    for attempt in range(1, self.max_retries + 1):
      req = request.Request(
        self.endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
      )

      try:
        # We do not care about the response body for the POC.
        request.urlopen(req, timeout=1.0)  # nosec B310
        return
      except (error.URLError, error.HTTPError, TimeoutError, OSError) as exc:
        _logger.warning(
          "drtrace_client HTTP transport failed to reach daemon (attempt %s/%s): %s",
          attempt,
          self.max_retries,
          exc,
        )
        if attempt == self.max_retries:
          # Give up; events are dropped for this batch.
          return
        # Simple linear backoff; executed in the background queue thread.
        time.sleep(self.base_backoff_seconds * attempt)


