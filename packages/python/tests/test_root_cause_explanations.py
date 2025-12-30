"""
Tests for root-cause explanation generation.

These tests verify:
- Prompt building from analysis input
- Model response parsing
- Handling of incomplete/ambiguous responses
- Error location extraction
"""

from typing import List, Optional

import pytest

from drtrace_service.ai_model import AIModel, StubAIModel, get_ai_model, set_ai_model
from drtrace_service.analysis import (
    AnalysisInput,
    RootCauseExplanation,
    build_analysis_prompt,
    generate_root_cause_explanation,
    parse_model_response,
    prepare_ai_analysis_input,
)
from drtrace_service.models import LogRecord


class MockAIModel(AIModel):
    """Mock AI model for testing with configurable responses."""

    def __init__(self, response: str):
        self.response = response
        self.last_prompt: Optional[str] = None

    def generate_explanation(self, prompt: str, **kwargs):
        self.last_prompt = prompt
        return self.response


@pytest.fixture
def sample_logs() -> List[LogRecord]:
    """Sample log records for testing."""
    return [
        LogRecord(
            ts=1000.0,
            level="ERROR",
            message="Division by zero",
            application_id="test_app",
            module_name="math_utils",
            file_path="src/math_utils.py",
            line_no=42,
            exception_type="ZeroDivisionError",
            stacktrace="Traceback (most recent call last):\n  File 'math_utils.py', line 42, in divide\n    return a / b\nZeroDivisionError: division by zero",
            context={},
        ),
        LogRecord(
            ts=1001.0,
            level="INFO",
            message="Processing request",
            application_id="test_app",
            module_name="api",
            context={},
        ),
    ]


@pytest.fixture
def sample_analysis_input(sample_logs) -> AnalysisInput:
    """Sample analysis input with logs and code snippets."""
    return prepare_ai_analysis_input(sample_logs, context_lines=5)


def test_build_analysis_prompt_includes_logs_and_code(sample_analysis_input):
    """Test that prompt includes all log entries and code snippets."""
    prompt = build_analysis_prompt(sample_analysis_input)

    # Check summary section
    assert "Total logs analyzed: 2" in prompt
    assert "Error logs: 1" in prompt

    # Check log entries are included
    assert "Division by zero" in prompt
    assert "ERROR" in prompt
    assert "math_utils.py" in prompt
    assert "Line: 42" in prompt
    assert "ZeroDivisionError" in prompt

    # Check instructions section
    assert "Instructions" in prompt
    assert "root cause" in prompt.lower()


def test_build_analysis_prompt_handles_missing_code_snippets():
    """Test prompt building when code snippets are unavailable."""
    logs = [
        LogRecord(
            ts=1000.0,
            level="ERROR",
            message="Test error",
            application_id="test_app",
            module_name="test",
            file_path="missing.py",
            line_no=10,
            context={},
        )
    ]
    input_data = prepare_ai_analysis_input(logs)
    prompt = build_analysis_prompt(input_data)

    # Should still include the log entry
    assert "Test error" in prompt
    assert "missing.py" in prompt
    # Should mention code context unavailable if snippet failed
    assert "Code context" in prompt or "unavailable" in prompt.lower()


def test_parse_model_response_structured_format():
    """Test parsing a well-structured model response."""
    response = """## Root Cause Analysis

**Summary**: Division by zero error occurred in math_utils.py at line 42.

**Root Cause**: The function attempted to divide by zero when the denominator (b) was 0. This is a runtime error that should be caught with input validation.

**Key Evidence**:
- Error log shows ZeroDivisionError at line 42
- Stack trace indicates the division operation failed
- No input validation was performed before the division

**Suggested Fixes**:
- Add input validation to check if denominator is zero before division
- Return a meaningful error or default value when division by zero would occur
- Add unit tests to cover edge cases

**Confidence**: High - Clear error location and cause identified."""

    logs = [
        LogRecord(
            ts=1000.0,
            level="ERROR",
            message="Division by zero",
            application_id="test_app",
            module_name="math_utils",
            file_path="src/math_utils.py",
            line_no=42,
            context={},
        )
    ]
    input_data = prepare_ai_analysis_input(logs)
    explanation = parse_model_response(response, input_data)

    assert "Division by zero" in explanation.summary
    assert "denominator" in explanation.root_cause.lower()
    assert len(explanation.key_evidence) > 0
    assert len(explanation.suggested_fixes) > 0
    assert explanation.confidence == "high"
    assert explanation.error_location is not None
    assert explanation.error_location["file_path"] == "src/math_utils.py"
    assert explanation.error_location["line_no"] == 42


def test_parse_model_response_incomplete_format():
    """Test parsing an incomplete or ambiguous model response."""
    response = """This is an error. Something went wrong."""

    logs = [
        LogRecord(
            ts=1000.0,
            level="ERROR",
            message="Test error",
            application_id="test_app",
            module_name="test",
            context={},
        )
    ]
    input_data = prepare_ai_analysis_input(logs)
    explanation = parse_model_response(response, input_data)

    # Should still return a valid explanation with fallback content
    assert explanation.summary
    assert explanation.root_cause
    assert explanation.raw_response == response
    # Should default to medium confidence when unclear
    assert explanation.confidence in ("low", "medium", "high")


def test_parse_model_response_missing_sections():
    """Test parsing when some sections are missing."""
    response = """Summary: An error occurred.
Root Cause: Unknown."""

    logs = [
        LogRecord(
            ts=1000.0,
            level="ERROR",
            message="Test",
            application_id="test_app",
            module_name="test",
            context={},
        )
    ]
    input_data = prepare_ai_analysis_input(logs)
    explanation = parse_model_response(response, input_data)

    assert "error occurred" in explanation.summary.lower()
    assert "unknown" in explanation.root_cause.lower()
    # Lists should be empty but valid
    assert isinstance(explanation.key_evidence, list)
    assert isinstance(explanation.suggested_fixes, list)


def test_parse_model_response_extracts_error_location():
    """Test that error location is extracted from input data."""
    response = "Some analysis text."

    logs = [
        LogRecord(
            ts=1000.0,
            level="ERROR",
            message="Error",
            application_id="test_app",
            module_name="test",
            file_path="src/test.py",
            line_no=100,
            context={},
        )
    ]
    input_data = prepare_ai_analysis_input(logs)
    explanation = parse_model_response(response, input_data)

    assert explanation.error_location is not None
    assert explanation.error_location["file_path"] == "src/test.py"
    assert explanation.error_location["line_no"] == 100


def test_parse_model_response_no_error_location_when_missing():
    """Test that error_location is None when file/line not available."""
    response = "Some analysis."

    logs = [
        LogRecord(
            ts=1000.0,
            level="INFO",
            message="Info message",
            application_id="test_app",
            module_name="test",
            context={},
        )
    ]
    input_data = prepare_ai_analysis_input(logs)
    explanation = parse_model_response(response, input_data)

    assert explanation.error_location is None


def test_generate_root_cause_explanation_full_flow(sample_analysis_input):
    """Test the full flow from analysis input to explanation."""
    # Use stub model
    original_model = get_ai_model()
    try:
        stub_model = StubAIModel()
        set_ai_model(stub_model)

        explanation = generate_root_cause_explanation(sample_analysis_input)

        assert isinstance(explanation, RootCauseExplanation)
        assert explanation.summary
        assert explanation.root_cause
        assert explanation.raw_response
    finally:
        set_ai_model(original_model)


def test_generate_root_cause_explanation_with_mock_model(sample_analysis_input):
    """Test explanation generation with a mock model."""
    mock_response = """Summary: Test summary.
Root Cause: Test root cause.
Key Evidence:
- Evidence 1
- Evidence 2
Suggested Fixes:
- Fix 1
- Fix 2
Confidence: High"""

    mock_model = MockAIModel(mock_response)
    original_model = get_ai_model()
    try:
        set_ai_model(mock_model)

        explanation = generate_root_cause_explanation(sample_analysis_input)

        assert "Test summary" in explanation.summary
        assert "Test root cause" in explanation.root_cause
        assert len(explanation.key_evidence) >= 2
        assert len(explanation.suggested_fixes) >= 2
        assert mock_model.last_prompt is not None
        assert "Division by zero" in mock_model.last_prompt
    finally:
        set_ai_model(original_model)


def test_generate_root_cause_explanation_handles_incomplete_response(sample_analysis_input):
    """Test that incomplete model responses are handled gracefully."""
    incomplete_response = "Partial response without structure."

    mock_model = MockAIModel(incomplete_response)
    original_model = get_ai_model()
    try:
        set_ai_model(mock_model)

        explanation = generate_root_cause_explanation(sample_analysis_input)

        # Should still return valid explanation
        assert isinstance(explanation, RootCauseExplanation)
        assert explanation.summary
        assert explanation.root_cause
        assert explanation.raw_response == incomplete_response
    finally:
        set_ai_model(original_model)


def test_stub_ai_model_returns_response():
    """Test that StubAIModel returns a response."""
    stub = StubAIModel()
    response = stub.generate_explanation("Test prompt")

    assert isinstance(response, str)
    assert len(response) > 0
    assert "Root Cause" in response or "Analysis" in response


def test_stub_ai_model_detects_error_in_prompt():
    """Test that StubAIModel detects error keywords in prompt."""
    stub = StubAIModel()
    error_response = stub.generate_explanation("This is an error message")
    normal_response = stub.generate_explanation("This is a normal log message")

    # Error response should mention error-related content
    assert "error" in error_response.lower() or "exception" in error_response.lower()
    # Normal response should be different
    assert error_response != normal_response


def test_root_cause_explanation_defaults():
    """Test that RootCauseExplanation has proper defaults."""
    explanation = RootCauseExplanation(
        summary="Test",
        root_cause="Test cause",
    )

    assert explanation.key_evidence == []
    assert explanation.suggested_fixes == []
    assert explanation.confidence == "medium"
    assert explanation.error_location is None
    assert explanation.raw_response is None


def test_root_cause_explanation_with_all_fields():
    """Test RootCauseExplanation with all fields populated."""
    explanation = RootCauseExplanation(
        summary="Summary",
        root_cause="Root cause",
        error_location={"file_path": "test.py", "line_no": 10},
        key_evidence=["Evidence 1", "Evidence 2"],
        suggested_fixes=["Fix 1"],
        confidence="high",
        raw_response="Raw response",
    )

    assert explanation.summary == "Summary"
    assert explanation.root_cause == "Root cause"
    assert explanation.error_location["file_path"] == "test.py"
    assert len(explanation.key_evidence) == 2
    assert len(explanation.suggested_fixes) == 1
    assert explanation.confidence == "high"
    assert explanation.raw_response == "Raw response"

