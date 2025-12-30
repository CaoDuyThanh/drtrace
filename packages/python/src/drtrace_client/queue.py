from __future__ import annotations

import os
import queue
import threading
from typing import Any, Callable, Dict, List, Optional

LogRecordDict = Dict[str, Any]
BatchSender = Callable[[List[LogRecordDict]], None]


class LogQueue:
  """
  In-process queue for log events.

  For the POC this is a simple, per-process queue plus a single background
  worker thread that drains a bounded queue and sends batches via the provided
  sender.

  The implementation is **multi-process aware**:
  - We track the process ID (PID) and detect when the process has forked.
  - Each process that emits logs starts its own worker thread on demand.
  - Single-process behavior is unchanged.
  """

  def __init__(
    self,
    sender: BatchSender,
    maxsize: int = 1000,
    batch_size: int = 50,
  ) -> None:
    self._queue: "queue.Queue[LogRecordDict]" = queue.Queue(maxsize=maxsize)
    self._sender: BatchSender = sender
    self._batch_size = batch_size
    self._thread: Optional[threading.Thread] = None
    self._stopped = threading.Event()
    # Track PID to detect forks and ensure a per-process worker thread.
    self._pid = os.getpid()
    self._lock = threading.Lock()

  def start(self) -> None:
    """
    Start the background worker thread.

    Safe to call multiple times and across forked processes:
    - In the same process: subsequent calls are no-ops once the thread is running.
    - In a child process after fork: we detect the PID change, reset internal
      thread state, and start a fresh worker thread for the child.
    """
    current_pid = os.getpid()
    with self._lock:
      if self._pid != current_pid:
        # We are in a new process (after fork). Reset thread state and event.
        self._pid = current_pid
        self._stopped = threading.Event()
        self._thread = None

      if self._thread is not None and self._thread.is_alive():
        return

      self._thread = threading.Thread(
        target=self._run, name="drtrace-client-queue", daemon=True
      )
      self._thread.start()

  def stop(self) -> None:
    self._stopped.set()
    if self._thread and self._thread.is_alive():
      self._thread.join(timeout=1.0)

  def enqueue(self, record: LogRecordDict) -> None:
    """
    Enqueue a record for batched delivery.

    This method is safe to call from forked worker processes: it will ensure
    that a worker thread is running in the current process before enqueuing.
    """
    # Lazy-start the worker thread in the current process if needed.
    self.start()

    try:
      self._queue.put_nowait(record)
    except queue.Full:
      # Drop on the floor for POC; future stories can add metrics/backpressure.
      pass

  def _run(self) -> None:
    while not self._stopped.is_set():
      batch: List[LogRecordDict] = []
      try:
        item = self._queue.get(timeout=0.5)
      except queue.Empty:
        continue

      batch.append(item)
      while len(batch) < self._batch_size:
        try:
          item = self._queue.get_nowait()
        except queue.Empty:
          break
        batch.append(item)

      if batch:
        try:
          print(batch)
          self._sender(batch)
        except Exception:
          # For the POC we swallow errors; higher-level logging can be added later.
          continue


