"""
AI model integration abstraction for root-cause analysis.

This module provides a thin abstraction layer for calling AI models
to generate root-cause explanations. The POC implementation can be
stubbed or wired to actual model providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class AIModel(ABC):
    """
    Abstract interface for AI model integration.

    This abstraction allows the analysis pipeline to work with different
    AI providers (OpenAI, Anthropic, local models, etc.) without tight coupling.
    """

    @abstractmethod
    def generate_explanation(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate a root-cause explanation from a prompt.

        Args:
            prompt: The analysis prompt containing logs and code context
            **kwargs: Additional model-specific parameters (temperature, max_tokens, etc.)

        Returns:
            Raw text response from the model
        """
        raise NotImplementedError


class StubAIModel(AIModel):
    """
    Stub implementation for testing and development.

    Returns predefined responses based on prompt content.
    """

    def generate_explanation(self, prompt: str, **kwargs: Any) -> str:
        """Return a stub response for testing."""
        # Simple heuristic: if prompt mentions "error" or "exception", return error explanation
        if "error" in prompt.lower() or "exception" in prompt.lower():
            return """## Root Cause Analysis

**Error Location**: The error occurred in the code at the location specified in the logs.

**Root Cause**: Based on the log messages and code context, this appears to be a runtime error that requires further investigation.

**Key Evidence**:
- Error log messages indicate an exception occurred
- Code context shows the location where the error was raised

**Suggested Fixes**:
1. Review the error message and stack trace for specific details
2. Check input validation at the error location
3. Verify dependencies and external resources

**Confidence**: Medium - Analysis based on available log and code context."""
        else:
            return """## Root Cause Analysis

**Summary**: No errors detected in the provided logs.

**Analysis**: The logs show normal application behavior without critical errors.

**Confidence**: High - No error indicators found."""


# Global model instance (can be replaced for testing)
_model: Optional[AIModel] = None


def get_ai_model() -> AIModel:
    """
    Get the global AI model instance.

    In tests, this can be monkeypatched to use a stub or mock.
    """
    global _model
    if _model is None:
        # Default to stub for POC (no external dependencies)
        _model = StubAIModel()
    return _model


def set_ai_model(model: AIModel) -> None:
    """Set the global AI model instance (useful for testing or custom providers)."""
    global _model
    _model = model

