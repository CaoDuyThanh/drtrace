import multiprocessing as mp
import os
import time

from drtrace_client.queue import LogQueue  # type: ignore[import]


def test_log_queue_single_process_behavior():
  """Single-process behavior should remain unchanged.

  We verify that enqueuing records in a single process results in the
  sender being called with the expected batch.
  """
  results: mp.Queue = mp.Queue()

  def sender(batch):
    results.put(batch)

  log_queue = LogQueue(sender=sender, maxsize=10, batch_size=3)

  # Enqueue a few records
  log_queue.enqueue({"i": 1})
  log_queue.enqueue({"i": 2})
  log_queue.enqueue({"i": 3})

  # Give worker time to process
  time.sleep(0.2)

  batch = results.get(timeout=2.0)
  assert len(batch) == 3
  assert {r["i"] for r in batch} == {1, 2, 3}


def test_log_queue_sends_from_child_process():
  """After fork, child process should still send logs via LogQueue.

  This simulates a process-based server which forks worker processes after
  `LogQueue` has been created in the parent.
  """
  results: mp.Queue = mp.Queue()

  # Create the queue in the parent before forking, as setup_logging() would.
  def sender(batch):
    results.put(batch)

  log_queue = LogQueue(sender=sender, maxsize=10, batch_size=1)

  pid = os.fork()
  if pid == 0:
    try:
      # In the child: enqueue a record. LogQueue must detect PID change and
      # start a worker thread in this process when enqueue() is called.
      log_queue.enqueue({"msg": "from-child"})

      # Give worker time to send
      time.sleep(0.2)
    finally:
      os._exit(0)

  # Parent: wait for child and verify we received a batch
  os.waitpid(pid, 0)
  batch = results.get(timeout=2.0)
  assert len(batch) == 1
  assert batch[0]["msg"] == "from-child"


{
  "cells": [],
  "metadata": {
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 2
}
