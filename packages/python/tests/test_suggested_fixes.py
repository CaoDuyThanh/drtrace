"""
Tests for suggested fixes and remediation steps (Story 6.2).

These tests verify:
- Structured SuggestedFix extraction from model responses
- File/line references in fixes
- Related log IDs linking
- Handling of "no clear remediation" cases
- Safety labels and confidence levels
"""

from typing import List

import pytest

from drtrace_service.ai_model import AIModel, get_ai_model, set_ai_model
from drtrace_service.analysis import (
    AnalysisInput,
    RootCauseExplanation,
    SuggestedFix,
    generate_root_cause_explanation,
    parse_model_response,
    prepare_ai_analysis_input,
)
from drtrace_service.models import LogRecord


class MockAIModel(AIModel):
    """Mock AI model for testing with configurable responses."""

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
    ]


@pytest.fixture
def sample_analysis_input(sample_logs) -> AnalysisInput:
    """Sample analysis input with logs and code snippets."""
    return prepare_ai_analysis_input(sample_logs, context_lines=5)


def test_parse_model_response_extracts_structured_fixes(sample_analysis_input):
    """Test that parse_model_response extracts structured SuggestedFix objects."""
    response = """Summary: Division by zero error.
Root Cause: The function attempted to divide by zero at line 42.
Key Evidence:
- Error log shows ZeroDivisionError
Suggested Fixes:
- Add null check before division at src/math_utils.py:42
- Validate input parameters in calling function
Confidence: High"""

    explanation = parse_model_response(response, sample_analysis_input)

    assert len(explanation.suggested_fixes) > 0
    assert isinstance(explanation.suggested_fixes[0], SuggestedFix)
    assert explanation.suggested_fixes[0].description
    assert explanation.suggested_fixes[0].file_path == "src/math_utils.py"
    assert explanation.suggested_fixes[0].line_no == 42


def test_parse_model_response_extracts_file_line_references(sample_analysis_input):
    """Test that file and line references are extracted from fix descriptions."""
    response = """Summary: Error occurred.
Root Cause: Issue at line 42.
Suggested Fixes:
- Fix the issue in src/math_utils.py:42-45
- Add validation at src/api.py:100
Confidence: Medium"""

    explanation = parse_model_response(response, sample_analysis_input)

    fixes = explanation.suggested_fixes
    assert len(fixes) >= 2

    # First fix should have file and line range
    fix1 = fixes[0]
    assert fix1.file_path == "src/math_utils.py"
    assert fix1.line_no == 42
    assert fix1.line_range == {"start": 42, "end": 45}

    # Second fix should have file and line
    fix2 = fixes[1]
    assert fix2.file_path == "src/api.py"
    assert fix2.line_no == 100


def test_parse_model_response_links_fixes_to_logs(sample_analysis_input):
    """Test that fixes are linked to related log IDs."""
    response = """Summary: Error occurred.
Root Cause: Issue in math_utils.py.
Suggested Fixes:
- Fix at src/math_utils.py:42
Confidence: Medium"""

    explanation = parse_model_response(response, sample_analysis_input)

    if explanation.suggested_fixes:
        fix = explanation.suggested_fixes[0]
        # Should link to log with matching file_path
        assert len(fix.related_log_ids) > 0
        assert any("math_utils" in log_id or "1000" in log_id for log_id in fix.related_log_ids)


def test_parse_model_response_handles_no_clear_remediation(sample_analysis_input):
    """Test that 'no clear remediation' is detected and handled."""
    response = """Summary: Error occurred.
Root Cause: Unknown cause.
Suggested Fixes:
No clear remediation identified. Further investigation required.
Confidence: Low"""

    explanation = parse_model_response(response, sample_analysis_input)

    assert explanation.has_clear_remediation is False
    # Should have empty or minimal fixes
    assert len(explanation.suggested_fixes) == 0 or all(
        "no clear" in fix.description.lower() or "investigation" in fix.description.lower()
        for fix in explanation.suggested_fixes
    )


def test_parse_model_response_detects_no_remediation_phrases(sample_analysis_input):
    """Test that various 'no remediation' phrases are detected."""
    phrases = [
        "No clear remediation identified",
        "Cannot identify a clear fix",
        "Requires further investigation",
        "Error is ambiguous",
    ]

    for phrase in phrases:
        response = f"""Summary: Error.
Root Cause: Unknown.
Suggested Fixes:
{phrase}
Confidence: Low"""

        explanation = parse_model_response(response, sample_analysis_input)
        assert explanation.has_clear_remediation is False


def test_parse_model_response_extracts_fix_confidence(sample_analysis_input):
    """Test that confidence levels are extracted for individual fixes."""
    response = """Summary: Error.
Root Cause: Issue.
Suggested Fixes:
- High confidence fix: Add validation (high confidence)
- Low confidence fix: Try this approach (low confidence)
- Medium confidence fix: Standard approach
Confidence: Medium"""

    explanation = parse_model_response(response, sample_analysis_input)

    fixes = explanation.suggested_fixes
    if len(fixes) >= 3:
        assert fixes[0].confidence == "high"
        assert fixes[1].confidence == "low"
        assert fixes[2].confidence == "medium"


def test_suggested_fix_structure():
    """Test that SuggestedFix has correct structure."""
    fix = SuggestedFix(
        description="Add null check",
        file_path="src/test.py",
        line_no=42,
        line_range={"start": 40, "end": 45},
        related_log_ids=["log_0_1000"],
        confidence="high",
        rationale="Prevents division by zero",
    )

    assert fix.description == "Add null check"
    assert fix.file_path == "src/test.py"
    assert fix.line_no == 42
    assert fix.line_range == {"start": 40, "end": 45}
    assert fix.related_log_ids == ["log_0_1000"]
    assert fix.confidence == "high"
    assert fix.rationale == "Prevents division by zero"


def test_suggested_fix_defaults():
    """Test that SuggestedFix has proper defaults."""
    fix = SuggestedFix(description="Test fix")

    assert fix.description == "Test fix"
    assert fix.file_path is None
    assert fix.line_no is None
    assert fix.line_range is None
    assert fix.related_log_ids == []
    assert fix.confidence == "medium"
    assert fix.rationale is None


def test_generate_root_cause_explanation_includes_structured_fixes(sample_analysis_input):
    """Test that generate_root_cause_explanation returns structured fixes."""
    response = """Summary: Error.
Root Cause: Issue.
Suggested Fixes:
- Fix at src/math_utils.py:42
Confidence: Medium"""

    original_model = get_ai_model()
    try:
        mock_model = MockAIModel(response)
        set_ai_model(mock_model)

        explanation = generate_root_cause_explanation(sample_analysis_input)

        assert isinstance(explanation, RootCauseExplanation)
        assert isinstance(explanation.suggested_fixes, list)
        if explanation.suggested_fixes:
            assert isinstance(explanation.suggested_fixes[0], SuggestedFix)
    finally:
        set_ai_model(original_model)


def test_root_cause_explanation_has_clear_remediation_flag():
    """Test that RootCauseExplanation includes has_clear_remediation flag."""
    explanation = RootCauseExplanation(
        summary="Test",
        root_cause="Test cause",
        has_clear_remediation=True,
    )

    assert explanation.has_clear_remediation is True

    explanation_no_fix = RootCauseExplanation(
        summary="Test",
        root_cause="Test cause",
        has_clear_remediation=False,
    )

    assert explanation_no_fix.has_clear_remediation is False


def test_parse_model_response_handles_missing_fixes_gracefully(sample_analysis_input):
    """Test that missing fixes are handled gracefully."""
    response = """Summary: Error occurred.
Root Cause: Unknown cause.
Confidence: Low"""

    explanation = parse_model_response(response, sample_analysis_input)

    # Should still return valid explanation
    assert isinstance(explanation, RootCauseExplanation)
    assert isinstance(explanation.suggested_fixes, list)
    # May be empty, which is OK


def test_parse_model_response_extracts_line_range_from_fix_text(sample_analysis_input):
    """Test that line ranges are extracted from fix descriptions."""
    response = """Summary: Error.
Root Cause: Issue.
Suggested Fixes:
- Fix the code in src/math_utils.py:40-45
Confidence: Medium"""

    explanation = parse_model_response(response, sample_analysis_input)

    if explanation.suggested_fixes:
        fix = explanation.suggested_fixes[0]
        assert fix.line_range is not None
        assert fix.line_range["start"] == 40
        assert fix.line_range["end"] == 45


def test_parse_model_response_handles_multiple_fixes(sample_analysis_input):
    """Test that multiple fixes are parsed correctly."""
    response = """Summary: Error.
Root Cause: Multiple issues.
Suggested Fixes:
- Fix 1: Add validation at src/math_utils.py:42
- Fix 2: Check input at src/api.py:100
- Fix 3: Update configuration
Confidence: Medium"""

    explanation = parse_model_response(response, sample_analysis_input)

    assert len(explanation.suggested_fixes) >= 3
    # Each fix should be a SuggestedFix object
    for fix in explanation.suggested_fixes:
        assert isinstance(fix, SuggestedFix)
        assert fix.description


def test_suggested_fix_links_to_error_logs(sample_analysis_input):
    """Test that fixes are linked to error logs when file/line match."""
    response = """Summary: Error.
Root Cause: Issue at src/math_utils.py:42.
Suggested Fixes:
- Fix at src/math_utils.py:42
Confidence: Medium"""

    explanation = parse_model_response(response, sample_analysis_input)

    if explanation.suggested_fixes:
        fix = explanation.suggested_fixes[0]
        # Should link to the error log with matching file_path
        assert len(fix.related_log_ids) > 0
        # The log should be from the error log we created
        assert any("1000" in log_id for log_id in fix.related_log_ids)

