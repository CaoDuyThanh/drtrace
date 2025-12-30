"""
Tests for unified multi-language log schema validation.

This validates that the schema supports Python, C++, and other languages
without requiring schema changes or breaking compatibility.
"""

import time
from typing import Any, Dict

from drtrace_service.models import LogBatch, LogRecord  # type: ignore[import]


def _make_python_log_record(
  application_id: str = "test-python-app",
  service_name: str = "api",
  module_name: str = "myapp.handlers",
  level: str = "INFO",
  message: str = "Processing request",
  **kwargs: Any,
) -> Dict[str, Any]:
  """Create a representative Python log record payload."""
  base: Dict[str, Any] = {
    "ts": time.time(),
    "level": level,
    "message": message,
    "application_id": application_id,
    "service_name": service_name,
    "module_name": module_name,
    "context": {"request_id": "req-123", "user_id": "user-456"},
  }
  base.update(kwargs)
  return base


def _make_cpp_log_record(
  application_id: str = "test-cpp-app",
  service_name: str = "engine",
  module_name: str = "renderer",
  level: str = "INFO",
  message: str = "Frame rendered",
  **kwargs: Any,
) -> Dict[str, Any]:
  """Create a representative C++ log record payload."""
  base: Dict[str, Any] = {
    "ts": time.time(),
    "level": level,
    "message": message,
    "application_id": application_id,
    "service_name": service_name,
    "module_name": module_name,
    "context": {
      "language": "cpp",
      "thread_id": "12345",
      "process_id": "67890",
    },
  }
  base.update(kwargs)
  return base


def test_python_log_record_validates():
  """Python log record validates against unified schema."""
  payload = _make_python_log_record()
  record = LogRecord(**payload)
  assert record.application_id == "test-python-app"
  assert record.service_name == "api"
  assert record.module_name == "myapp.handlers"
  assert record.level == "INFO"
  assert record.message == "Processing request"
  assert "request_id" in record.context


def test_cpp_log_record_validates():
  """C++ log record validates against unified schema."""
  payload = _make_cpp_log_record()
  record = LogRecord(**payload)
  assert record.application_id == "test-cpp-app"
  assert record.service_name == "engine"
  assert record.module_name == "renderer"
  assert record.level == "INFO"
  assert record.message == "Frame rendered"
  assert record.context.get("language") == "cpp"


def test_python_error_with_stacktrace():
  """Python error log with stacktrace validates."""
  payload = _make_python_log_record(
    level="ERROR",
    message="Division by zero",
    file_path="/app/handlers.py",
    line_no=42,
    exception_type="ZeroDivisionError",
    stacktrace="Traceback (most recent call last):\n  File ...",
  )
  record = LogRecord(**payload)
  assert record.level == "ERROR"
  assert record.file_path == "/app/handlers.py"
  assert record.line_no == 42
  assert record.exception_type == "ZeroDivisionError"
  assert record.stacktrace is not None


def test_cpp_error_with_stacktrace():
  """C++ error log with stacktrace validates."""
  payload = _make_cpp_log_record(
    level="ERROR",
    message="Segmentation fault",
    file_path="/src/renderer.cpp",
    line_no=128,
    exception_type="std::runtime_error",
    stacktrace="#0  0x00007f8b4c123456 in renderer::draw() at renderer.cpp:128",
    context={
      "language": "cpp",
      "thread_id": "12345",
      "signal": "SIGSEGV",
    },
  )
  record = LogRecord(**payload)
  assert record.level == "ERROR"
  assert record.file_path == "/src/renderer.cpp"
  assert record.line_no == 128
  assert record.exception_type == "std::runtime_error"
  assert record.stacktrace is not None
  assert record.context.get("signal") == "SIGSEGV"


def test_batch_with_mixed_languages():
  """Batch containing both Python and C++ logs validates."""
  python_log = _make_python_log_record()
  cpp_log = _make_cpp_log_record()
  batch = LogBatch(
    application_id="mixed-app",
    logs=[
      LogRecord(**python_log),
      LogRecord(**cpp_log),
    ],
  )
  assert len(batch.logs) == 2
  assert batch.logs[0].module_name == "myapp.handlers"
  assert batch.logs[1].module_name == "renderer"


def test_optional_fields_can_be_omitted():
  """Optional fields (file_path, line_no, etc.) can be omitted for any language."""
  minimal_python = {
    "ts": time.time(),
    "level": "INFO",
    "message": "Simple log",
    "application_id": "app",
    "module_name": "module",
  }
  minimal_cpp = {
    "ts": time.time(),
    "level": "INFO",
    "message": "Simple log",
    "application_id": "app",
    "module_name": "module",
  }
  assert LogRecord(**minimal_python)
  assert LogRecord(**minimal_cpp)


def test_context_field_is_extensible():
  """Context field allows language-specific metadata without schema changes."""
  python_with_extras = _make_python_log_record(
    context={
      "request_id": "req-123",
      "python_version": "3.8.10",
      "framework": "django",
    }
  )
  cpp_with_extras = _make_cpp_log_record(
    context={
      "language": "cpp",
      "compiler": "g++",
      "build_config": "release",
      "cpu_arch": "x86_64",
    }
  )
  python_record = LogRecord(**python_with_extras)
  cpp_record = LogRecord(**cpp_with_extras)
  assert python_record.context.get("framework") == "django"
  assert cpp_record.context.get("cpu_arch") == "x86_64"


def test_service_name_is_optional():
  """service_name is optional for all languages."""
  without_service = {
    "ts": time.time(),
    "level": "INFO",
    "message": "Log without service",
    "application_id": "app",
    "module_name": "module",
  }
  record = LogRecord(**without_service)
  assert record.service_name is None

