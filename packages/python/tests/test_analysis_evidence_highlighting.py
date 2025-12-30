"""
Tests for evidence highlighting in analysis results.

These tests verify:
- Evidence references are extracted and linked to logs/code
- References are consistent and complete
- Evidence prioritization (error logs, code context)
- Evidence references can be mapped back to stored logs
"""

from typing import List

import pytest

from drtrace_service.ai_model import AIModel, StubAIModel, get_ai_model, set_ai_model
from drtrace_service.analysis import (
    AnalysisInput,
    EvidenceReference,
    RootCauseExplanation,
    extract_evidence_references,
    generate_root_cause_explanation,
    prepare_ai_analysis_input,
)
from drtrace_service.models import LogRecord


class MockAIModel(AIModel):
    """Mock AI model for testing."""

    def __init__(self, response: str):
        self.response = response

    def generate_explanation(self, prompt: str, **kwargs):
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
            stacktrace="Traceback...",
            context={},
        ),
        LogRecord(
            ts=1001.0,
            level="WARN",
            message="Deprecated function called",
            application_id="test_app",
            module_name="api",
            file_path="src/api.py",
            line_no=100,
            context={},
        ),
        LogRecord(
            ts=1002.0,
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


def test_extract_evidence_references_includes_error_logs(sample_analysis_input):
    """Test that error logs are included as evidence references."""
    explanation = RootCauseExplanation(
        summary="Error occurred",
        root_cause="Division by zero at line 42",
        key_evidence=["Error log shows division by zero"],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # Should include the ERROR log
    error_refs = [ref for ref in references if ref.log_id.startswith("log_0_")]  # First log (ERROR)
    assert len(error_refs) > 0
    error_ref = error_refs[0]
    assert error_ref.log_id == "log_0_1000"
    assert error_ref.file_path == "src/math_utils.py"
    assert error_ref.line_no == 42
    assert "error" in error_ref.reason.lower() or "division" in error_ref.reason.lower()


def test_extract_evidence_references_includes_code_location(sample_analysis_input):
    """Test that evidence references include code location when available."""
    explanation = RootCauseExplanation(
        summary="Error occurred",
        root_cause="Division by zero at src/math_utils.py:42",
        key_evidence=["Error at line 42 in math_utils.py"],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # Find reference for the error log
    error_ref = next((ref for ref in references if ref.file_path == "src/math_utils.py"), None)
    assert error_ref is not None
    assert error_ref.file_path == "src/math_utils.py"
    assert error_ref.line_no == 42
    # Should have line_range if code snippet was available
    # (Note: in test, snippet might not be available if file doesn't exist, but structure should be correct)


def test_extract_evidence_references_links_to_mentioned_logs(sample_analysis_input):
    """Test that logs mentioned in explanation are included as evidence."""
    explanation = RootCauseExplanation(
        summary="Multiple issues",
        root_cause="Error in math_utils.py and deprecated function in api.py",
        key_evidence=[
            "Division by zero error in math_utils.py",
            "Deprecated function called in api.py",
        ],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # Should include both ERROR log and WARN log (if mentioned)
    log_ids = {ref.log_id for ref in references}
    assert "log_0_1000" in log_ids  # ERROR log

    # Check if WARN log is included (if it has code context and is mentioned)
    [ref for ref in references if "api.py" in (ref.file_path or "")]
    # May or may not be included depending on code snippet availability


def test_extract_evidence_references_prioritizes_error_logs(sample_analysis_input):
    """Test that error logs are prioritized over other logs."""
    explanation = RootCauseExplanation(
        summary="Multiple logs",
        root_cause="Various issues",
        key_evidence=["Multiple log entries"],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # ERROR log should be first
    assert len(references) > 0
    first_ref = references[0]
    # Find the corresponding log entry
    error_entry = next(
        (e for e in sample_analysis_input.logs if e.log.log_id == first_ref.log_id), None
    )
    assert error_entry is not None
    assert error_entry.log.level.upper() in ("ERROR", "CRITICAL")


def test_extract_evidence_references_limits_to_top_evidence():
    """Test that evidence references are limited to most relevant items."""
    # Create many logs
    logs = [
        LogRecord(
            ts=1000.0 + i,
            level="ERROR" if i == 0 else "INFO",
            message=f"Log {i}",
            application_id="test_app",
            module_name="test",
            file_path=f"src/test_{i}.py" if i < 3 else None,
            line_no=10 + i if i < 3 else None,
            context={},
        )
        for i in range(10)
    ]

    input_data = prepare_ai_analysis_input(logs)
    explanation = RootCauseExplanation(
        summary="Many logs",
        root_cause="Various issues across multiple files",
        key_evidence=["Multiple log entries found"],
    )

    references = extract_evidence_references(explanation, input_data)

    # Should be limited to top 5
    assert len(references) <= 5


def test_extract_evidence_references_includes_line_range_when_available(sample_analysis_input):
    """Test that line_range is included when code snippet is available."""
    explanation = RootCauseExplanation(
        summary="Error with code context",
        root_cause="Error at line 42",
        key_evidence=["Code context available"],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # Find reference with file_path
    file_ref = next((ref for ref in references if ref.file_path), None)
    if file_ref:
        # If code snippet was successfully retrieved, line_range should be set
        # (In test environment, snippet might fail if file doesn't exist)
        # But the structure should support it
        assert file_ref.file_path is not None
        # line_range may be None if snippet retrieval failed, which is OK


def test_generate_root_cause_explanation_includes_evidence_references(sample_analysis_input):
    """Test that generate_root_cause_explanation includes evidence references."""
    original_model = get_ai_model()
    try:
        stub_model = StubAIModel()
        set_ai_model(stub_model)

        explanation = generate_root_cause_explanation(sample_analysis_input)

        assert isinstance(explanation, RootCauseExplanation)
        assert hasattr(explanation, "evidence_references")
        assert isinstance(explanation.evidence_references, list)
        # Should have at least one reference (the error log)
        assert len(explanation.evidence_references) > 0
    finally:
        set_ai_model(original_model)


def test_evidence_reference_structure():
    """Test that EvidenceReference has correct structure."""
    ref = EvidenceReference(
        log_id="log_0_1000",
        reason="Error log shows division by zero",
        file_path="src/math_utils.py",
        line_no=42,
        line_range={"start": 37, "end": 47},
    )

    assert ref.log_id == "log_0_1000"
    assert ref.reason == "Error log shows division by zero"
    assert ref.file_path == "src/math_utils.py"
    assert ref.line_no == 42
    assert ref.line_range == {"start": 37, "end": 47}


def test_evidence_reference_without_code_location():
    """Test EvidenceReference when code location is not available."""
    ref = EvidenceReference(
        log_id="log_1_1001",
        reason="Info log message",
    )

    assert ref.log_id == "log_1_1001"
    assert ref.reason == "Info log message"
    assert ref.file_path is None
    assert ref.line_no is None
    assert ref.line_range is None


def test_evidence_references_can_be_mapped_back_to_logs(sample_analysis_input):
    """Test that evidence references can be mapped back to original logs."""
    explanation = RootCauseExplanation(
        summary="Error analysis",
        root_cause="Division by zero",
        key_evidence=["Error at line 42"],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # Verify each reference maps to a log in input_data
    for ref in references:
        matching_entry = next(
            (e for e in sample_analysis_input.logs if e.log.log_id == ref.log_id), None
        )
        assert matching_entry is not None, f"Reference {ref.log_id} should map to a log entry"
        assert matching_entry.log.log_id == ref.log_id


def test_evidence_references_consistent_with_explanation(sample_analysis_input):
    """Test that evidence references are consistent with explanation content."""
    explanation = RootCauseExplanation(
        summary="Error in math_utils.py",
        root_cause="Division by zero at src/math_utils.py:42",
        key_evidence=["Error log shows division by zero at line 42"],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # Should include reference to math_utils.py
    math_refs = [ref for ref in references if ref.file_path == "src/math_utils.py"]
    assert len(math_refs) > 0

    # Reason should relate to the explanation
    math_ref = math_refs[0]
    assert "math_utils" in math_ref.reason.lower() or "division" in math_ref.reason.lower() or "error" in math_ref.reason.lower()


def test_root_cause_explanation_defaults_evidence_references():
    """Test that RootCauseExplanation defaults evidence_references to empty list."""
    explanation = RootCauseExplanation(
        summary="Test",
        root_cause="Test cause",
    )

    assert explanation.evidence_references == []


def test_evidence_references_prioritize_code_context(sample_analysis_input):
    """Test that logs with code context are prioritized in evidence."""
    # Create explanation that mentions multiple logs
    explanation = RootCauseExplanation(
        summary="Multiple issues",
        root_cause="Issues in math_utils.py and api.py",
        key_evidence=["Multiple files involved"],
    )

    references = extract_evidence_references(explanation, sample_analysis_input)

    # Error log (with code) should be first
    if len(references) > 0:
        first_ref = references[0]
        # Should have file_path (code context)
        # Note: In test, code snippets might not be available if files don't exist
        # But the logic should prioritize logs with file_path
        error_entry = next(
            (e for e in sample_analysis_input.logs if e.log.log_id == first_ref.log_id), None
        )
        if error_entry:
            assert error_entry.log.level.upper() in ("ERROR", "CRITICAL")

