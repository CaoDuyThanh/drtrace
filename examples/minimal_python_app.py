import logging
import os
import time

from drtrace_client import setup_logging  # type: ignore[import]


def main() -> None:
  # Minimal configuration via environment variables
  os.environ.setdefault("DRTRACE_APPLICATION_ID", "example-app")

  logger = logging.getLogger("example_app")
  logging.basicConfig(level=logging.INFO)

  setup_logging(logger)

  logger.info("Example INFO log from minimal app")
  try:
    1 / 0
  except ZeroDivisionError:
    logger.exception("Example ERROR log with exception")

  # Give the background log queue a brief moment to flush before exit
  time.sleep(0.5)


if __name__ == "__main__":
  main()


