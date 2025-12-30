from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from . import storage
from .ai_model import get_ai_model
from .code_context import SnippetResult, get_code_snippet
from .models import LogRecord


@dataclass(frozen=True)
class LogWithSnippet:
  log: LogRecord
  snippet: SnippetResult


def map_log_to_snippet(
  log: LogRecord,
  context_lines: int = 5,
  roots: Optional[List[Path]] = None,
) -> LogWithSnippet:
  """
  Map a single log record with file/line metadata to a code snippet.
  """
  file_path = log.file_path or ""
  line_no = log.line_no or 0
  snippet = get_code_snippet(file_path=file_path, line_no=line_no, context_lines=context_lines, roots=roots)
  return LogWithSnippet(log=log, snippet=snippet)


def map_logs_to_snippets(
  logs: List[LogRecord],
  context_lines: int = 5,
  roots: Optional[List[Path]] = None,
) -> List[LogWithSnippet]:
  """
  Map a batch of logs to snippets, reusing file contents via an in-memory cache
  within this call to avoid re-reading the same file.
  """
  cache: Dict[tuple[str, int, int], SnippetResult] = {}
  results: List[LogWithSnippet] = []

  for log in logs:
    key = (log.file_path or "", log.line_no or 0, context_lines)
    if key not in cache:
      cache[key] = get_code_snippet(
        file_path=log.file_path or "",
        line_no=log.line_no or 0,
        context_lines=context_lines,
        roots=roots,
      )
    results.append(LogWithSnippet(log=log, snippet=cache[key]))

  return results


def analyze_time_range(
  application_id: str,
  start_ts: float,
  end_ts: float,
  min_level: Optional[str] = None,
  module_name: Optional[Union[str, List[str]]] = None,
  service_name: Optional[Union[str, List[str]]] = None,
  limit: int = 100,
) -> List[LogRecord]:
  """
  Retrieve logs for a time range analysis.

  This function queries logs for a specific application within a time window,
  applying optional filters for level, module, and service.

  Args:
    application_id: Required application identifier
    start_ts: Start of time range (Unix timestamp, inclusive)
    end_ts: End of time range (Unix timestamp, inclusive)
    min_level: Optional minimum log level filter (e.g., "ERROR", "WARN")
    module_name: Optional module name filter (single string or list of strings)
    service_name: Optional service name filter (single string or list of strings)
    limit: Maximum number of records to return (default: 100, max: 1000)

  Returns:
    List of LogRecord objects matching the criteria, ordered by timestamp descending
  """
  backend = storage.get_storage()
  # Storage interface accepts single values or lists, so pass directly
  records = backend.query_time_range(
    start_ts=start_ts,
    end_ts=end_ts,
    application_id=application_id,
    module_name=module_name,
    service_name=service_name,
    limit=limit,
  )

  # Apply additional filters that aren't in the base query
  filtered_records: List[LogRecord] = []
  level_priority = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "CRITICAL": 4}

  for record in records:
    # Filter by minimum level if specified
    if min_level:
      record_level_priority = level_priority.get(record.level.upper(), -1)
      min_level_priority = level_priority.get(min_level.upper(), -1)
      if record_level_priority < min_level_priority:
        continue

    filtered_records.append(record)

  return filtered_records


@dataclass
class LogEntry:
  """A log entry in the AI input format."""

  log_id: str  # Unique identifier for this log (e.g., timestamp-based or index)
  timestamp: float
  level: str
  message: str
  module_name: str
  service_name: Optional[str] = None
  file_path: Optional[str] = None
  line_no: Optional[int] = None
  exception_type: Optional[str] = None
  stacktrace: Optional[str] = None
  context: Dict[str, Any] = None  # type: ignore[assignment]

  def __post_init__(self):
    """Ensure context defaults to empty dict."""
    if self.context is None:
      object.__setattr__(self, "context", {})


@dataclass
class CodeSnippetEntry:
  """A code snippet entry in the AI input format."""

  file_path: str
  line_no: int
  lines: List[Dict[str, Any]]  # List of {line_no, text, is_target}
  snippet_ok: bool
  snippet_error: Optional[str] = None


@dataclass
class LogWithCodeEntry:
  """Combined log and code snippet entry."""

  log: LogEntry
  code_snippet: Optional[CodeSnippetEntry] = None


@dataclass
class AnalysisInput:
  """Structured input format for AI analysis."""

  logs: List[LogWithCodeEntry]
  summary: Dict[str, Any]  # Metadata about the analysis set


def prepare_ai_analysis_input(
  logs: List[LogRecord],
  context_lines: int = 5,
  roots: Optional[List[Path]] = None,
) -> AnalysisInput:
  """
  Combine logs and code snippets into an AI-ready analysis input format.

  This function:
  1. Maps logs to code snippets using existing helpers
  2. Creates a structured format that includes both log details and code context
  3. Handles logs without file_path/line_no gracefully (includes log without snippet)

  Args:
    logs: List of LogRecord objects to analyze
    context_lines: Number of context lines to include around target line (default: 5)
    roots: Optional source roots for file resolution (defaults to configured roots)

  Returns:
    AnalysisInput object containing structured log and code snippet data
  """
  # Map logs to snippets
  log_snippets = map_logs_to_snippets(logs, context_lines=context_lines, roots=roots)

  # Build structured entries
  entries: List[LogWithCodeEntry] = []
  for i, log_snippet in enumerate(log_snippets):
    log = log_snippet.log
    snippet = log_snippet.snippet

    # Create log entry
    log_entry = LogEntry(
      log_id=f"log_{i}_{int(log.ts)}",
      timestamp=log.ts,
      level=log.level,
      message=log.message,
      module_name=log.module_name,
      service_name=log.service_name,
      file_path=log.file_path,
      line_no=log.line_no,
      exception_type=log.exception_type,
      stacktrace=log.stacktrace,
      context=log.context or {},
    )

    # Create code snippet entry if available and successful
    code_entry: Optional[CodeSnippetEntry] = None
    if log.file_path and log.line_no and snippet.ok:
      code_entry = CodeSnippetEntry(
        file_path=log.file_path,
        line_no=log.line_no,
        lines=[
          {"line_no": line.line_no, "text": line.text, "is_target": line.is_target}
          for line in snippet.lines
        ],
        snippet_ok=True,
      )
    elif log.file_path and log.line_no and not snippet.ok:
      # Log has file/line but snippet retrieval failed
      code_entry = CodeSnippetEntry(
        file_path=log.file_path,
        line_no=log.line_no,
        lines=[],
        snippet_ok=False,
        snippet_error=snippet.error,
      )

    entries.append(LogWithCodeEntry(log=log_entry, code_snippet=code_entry))

  # Build summary metadata
  total_logs = len(logs)
  logs_with_code = sum(1 for e in entries if e.code_snippet and e.code_snippet.snippet_ok)
  logs_without_code = total_logs - logs_with_code
  error_logs = sum(1 for log in logs if log.level.upper() in ("ERROR", "CRITICAL"))

  # Component breakdown for cross-module analysis
  services: Dict[str, int] = {}
  modules: Dict[str, int] = {}
  for log in logs:
    if log.service_name:
      services[log.service_name] = services.get(log.service_name, 0) + 1
    if log.module_name:
      modules[log.module_name] = modules.get(log.module_name, 0) + 1

  summary = {
    "total_logs": total_logs,
    "logs_with_code_context": logs_with_code,
    "logs_without_code_context": logs_without_code,
    "error_logs": error_logs,
    "time_range": {
      "start_ts": min(log.ts for log in logs) if logs else None,
      "end_ts": max(log.ts for log in logs) if logs else None,
    },
    "components": {
      "services": services,
      "modules": modules,
    },
  }

  return AnalysisInput(logs=entries, summary=summary)


def analysis_input_to_dict(input_data: AnalysisInput) -> Dict[str, Any]:
  """
  Convert AnalysisInput to a dictionary suitable for JSON serialization.

  This is useful for API responses or logging the AI input payload.
  """
  return {
    "logs": [
      {
        "log": asdict(entry.log),
        "code_snippet": asdict(entry.code_snippet) if entry.code_snippet else None,
      }
      for entry in input_data.logs
    ],
    "summary": input_data.summary,
  }


@dataclass
class EvidenceReference:
  """Reference to a specific log or code snippet that supports the explanation."""

  log_id: str  # Reference to LogEntry.log_id
  reason: str  # Why this evidence is relevant (from key_evidence text or inferred)
  file_path: Optional[str] = None  # Code file path if this evidence includes code
  line_no: Optional[int] = None  # Specific line number if applicable
  line_range: Optional[Dict[str, int]] = None  # {"start": ..., "end": ...} for code snippets


@dataclass
class SuggestedFix:
  """A suggested fix or remediation step with references to logs/code."""

  description: str  # Description of the fix
  file_path: Optional[str] = None  # Code file path if fix applies to specific file
  line_no: Optional[int] = None  # Specific line number if applicable
  line_range: Optional[Dict[str, int]] = None  # {"start": ..., "end": ...} for code ranges
  related_log_ids: List[str] = None  # type: ignore[assignment]
  confidence: str = "medium"  # "low", "medium", "high" - confidence in this fix
  rationale: Optional[str] = None  # Optional explanation of why this fix is suggested

  def __post_init__(self):
    """Ensure list fields default to empty lists."""
    if self.related_log_ids is None:
      object.__setattr__(self, "related_log_ids", [])


@dataclass
class RootCauseExplanation:
  """Structured root-cause explanation from AI analysis."""

  summary: str  # Brief summary of what happened
  root_cause: str  # Explanation of the likely root cause
  error_location: Optional[Dict[str, Any]] = None  # {"file_path": "...", "line_no": ...}
  key_evidence: List[str] = None  # type: ignore[assignment]
  suggested_fixes: List[SuggestedFix] = None  # type: ignore[assignment]
  confidence: str = "medium"  # "low", "medium", "high"
  raw_response: Optional[str] = None  # Original model response for debugging
  evidence_references: List[EvidenceReference] = None  # type: ignore[assignment]
  has_clear_remediation: bool = True  # Whether clear remediation was identified

  def __post_init__(self):
    """Ensure list fields default to empty lists."""
    if self.key_evidence is None:
      object.__setattr__(self, "key_evidence", [])
    if self.suggested_fixes is None:
      object.__setattr__(self, "suggested_fixes", [])
    if self.evidence_references is None:
      object.__setattr__(self, "evidence_references", [])


def build_analysis_prompt(input_data: AnalysisInput) -> str:
  """
  Build an AI prompt from combined logs and code snippets.

  This creates a structured prompt that includes:
  - Summary of the analysis context
  - Log entries with their details
  - Associated code snippets where available
  - Instructions for generating root-cause explanation
  """
  prompt_parts: List[str] = []

  # Header
  prompt_parts.append("You are analyzing application logs to identify root causes of errors.")
  prompt_parts.append("")
  prompt_parts.append("## Analysis Context")
  prompt_parts.append(f"Total logs analyzed: {input_data.summary['total_logs']}")
  prompt_parts.append(
    f"Logs with code context: {input_data.summary['logs_with_code_context']}"
  )
  prompt_parts.append(f"Error logs: {input_data.summary['error_logs']}")
  prompt_parts.append("")

  # Log entries with code snippets
  prompt_parts.append("## Log Entries and Code Context")
  for i, entry in enumerate(input_data.logs, 1):
    prompt_parts.append(f"### Log {i}")
    log = entry.log
    prompt_parts.append(f"Timestamp: {log.timestamp}")
    prompt_parts.append(f"Level: {log.level}")
    prompt_parts.append(f"Message: {log.message}")
    prompt_parts.append(f"Module: {log.module_name}")
    if log.service_name:
      prompt_parts.append(f"Service: {log.service_name}")
    if log.file_path:
      prompt_parts.append(f"File: {log.file_path}")
    if log.line_no:
      prompt_parts.append(f"Line: {log.line_no}")
    if log.exception_type:
      prompt_parts.append(f"Exception: {log.exception_type}")
    if log.stacktrace:
      prompt_parts.append(f"Stacktrace:\n{log.stacktrace}")

    # Code snippet if available
    if entry.code_snippet and entry.code_snippet.snippet_ok:
      prompt_parts.append("Code context:")
      for line in entry.code_snippet.lines:
        marker = ">>> " if line["is_target"] else "    "
        prompt_parts.append(f"{marker}{line['line_no']:4d}: {line['text']}")
    elif entry.code_snippet and not entry.code_snippet.snippet_ok:
      prompt_parts.append(f"Code context unavailable: {entry.code_snippet.snippet_error}")

    prompt_parts.append("")

  # Instructions
  prompt_parts.append("## Instructions")
  prompt_parts.append(
    "Analyze the logs and code context above to identify the root cause of any errors."
  )
  prompt_parts.append(
    "Provide a clear, developer-friendly explanation that includes:"
  )
  prompt_parts.append("1. A brief summary of what happened")
  prompt_parts.append("2. The likely root cause with specific file/line references")
  prompt_parts.append("3. Key evidence from the logs and code that supports your analysis")
  prompt_parts.append("4. Suggested fixes or remediation steps:")
  prompt_parts.append("   - For each fix, provide a clear description")
  prompt_parts.append("   - Include specific file/line references where the fix should be applied")
  prompt_parts.append("   - Reference relevant log entries that support this fix")
  prompt_parts.append("   - If no clear remediation can be identified, state that explicitly")
  prompt_parts.append("5. Your confidence level (low/medium/high)")
  prompt_parts.append("")
  prompt_parts.append("IMPORTANT: Only suggest fixes when you have clear evidence. If the error is ambiguous")
  prompt_parts.append("or requires more investigation, state 'No clear remediation identified' rather than")
  prompt_parts.append("guessing. All suggestions are AI-generated and should be reviewed by a developer.")

  return "\n".join(prompt_parts)


def parse_model_response(response: str, input_data: AnalysisInput) -> RootCauseExplanation:
  """
  Parse AI model response into structured RootCauseExplanation.

  This function extracts structured information from the model's text response,
  handling incomplete or ambiguous outputs gracefully.
  """
  # Extract error location from input data if available
  error_location: Optional[Dict[str, Any]] = None
  for entry in input_data.logs:
    if entry.log.level.upper() in ("ERROR", "CRITICAL") and entry.log.file_path and entry.log.line_no:
      error_location = {
        "file_path": entry.log.file_path,
        "line_no": entry.log.line_no,
      }
      break

  # Try to extract structured fields from response
  # Simple parsing: look for common patterns
  summary = ""
  root_cause = ""
  key_evidence: List[str] = []
  suggested_fixes_raw: List[str] = []  # Raw fix descriptions
  confidence = "medium"
  has_clear_remediation = True

  lines = response.split("\n")
  current_section = None

  # Check entire response for "no clear remediation" indicators first
  response_lower = response.lower()
  no_remediation_phrases = [
    "no clear remediation",
    "no clear fix",
    "cannot identify",
    "requires further investigation",
    "requires investigation",
    "error is ambiguous",
    "ambiguous error",
    "no clear remediation identified",
  ]
  if any(phrase in response_lower for phrase in no_remediation_phrases):
    has_clear_remediation = False

  for line in lines:
    line_stripped = line.strip()
    line_lower = line_stripped.lower()

    # Detect sections (check before processing content)
    # Only match section headers, not content lines that happen to contain keywords
    if ("summary" in line_lower and ":" in line and
        not line_stripped.startswith("-") and not line_stripped[0].isdigit()):
      current_section = "summary"
      summary = line.split(":", 1)[-1].strip()
      continue
    elif ("root cause" in line_lower and ":" in line and
          not line_stripped.startswith("-") and not line_stripped[0].isdigit()):
      current_section = "root_cause"
      root_cause = line.split(":", 1)[-1].strip()
      continue
    elif (("evidence" in line_lower or "key evidence" in line_lower) and ":" in line and
          not line_stripped.startswith("-") and not line_stripped[0].isdigit()):
      current_section = "evidence"
      # Check if there's content after the colon
      if ":" in line:
        after_colon = line.split(":", 1)[-1].strip()
        if after_colon:
          # If there's content, it's not a list, so skip
          pass
      continue
    elif (("suggested fix" in line_lower or "suggested fixes" in line_lower or
           ("fix" in line_lower and ("es:" in line_lower or ":" == line_stripped[-1:])) or
           "remediation" in line_lower) and ":" in line and
          not line_stripped.startswith("-") and not line_stripped[0].isdigit()):
      current_section = "fixes"
      continue
    elif "confidence" in line_lower and ":" in line:
      conf_text = line.split(":", 1)[-1].strip().lower()
      if "high" in conf_text:
        confidence = "high"
      elif "low" in conf_text:
        confidence = "low"
      else:
        confidence = "medium"
      current_section = None  # Reset section after confidence
      continue

    # Process content based on current section
    if not line_stripped or line_stripped.startswith("#"):
      continue

    if current_section == "summary":
      if not summary:
        summary = line_stripped
      else:
        summary += " " + line_stripped
    elif current_section == "root_cause":
      if not root_cause:
        root_cause = line_stripped
      else:
        root_cause += " " + line_stripped
    elif current_section == "evidence":
      # Collect list items (lines starting with -) or numbered items
      if line_stripped.startswith("-"):
        key_evidence.append(line_stripped.lstrip("- ").strip())
      elif line_stripped and not any(keyword in line_lower for keyword in ["summary", "root", "fix", "suggestion", "confidence", "evidence", "remediation"]):
        # If we're in evidence section and it's not a new section, treat as evidence
        if line_stripped[0].isdigit() and "." in line_stripped[:3]:
          # Numbered list item
          key_evidence.append(line_stripped.split(".", 1)[-1].strip())
    elif current_section == "fixes":
      # Check if this line indicates no remediation
      if any(phrase in line_lower for phrase in no_remediation_phrases):
        has_clear_remediation = False
        continue
      # Collect list items (lines starting with -) or numbered items
      if line_stripped.startswith("-"):
        fix_text = line_stripped.lstrip("- ").strip()
        # Skip if it's a "no remediation" message
        if not any(phrase in fix_text.lower() for phrase in no_remediation_phrases):
          suggested_fixes_raw.append(fix_text)
      elif line_stripped and not any(keyword in line_lower for keyword in ["summary", "root", "fix", "suggestion", "confidence", "evidence", "remediation"]):
        # If we're in fixes section and it's not a new section, treat as fix
        if line_stripped[0].isdigit() and "." in line_stripped[:3]:
          # Numbered list item
          fix_text = line_stripped.split(".", 1)[-1].strip()
          if not any(phrase in fix_text.lower() for phrase in no_remediation_phrases):
            suggested_fixes_raw.append(fix_text)
        elif line_stripped and not line_stripped.startswith("#"):
          # Also accept plain text lines in fixes section (for "No clear remediation" messages)
          if any(phrase in line_lower for phrase in no_remediation_phrases):
            has_clear_remediation = False

  # Parse suggested fixes into structured SuggestedFix objects
  suggested_fixes: List[SuggestedFix] = []
  if has_clear_remediation and suggested_fixes_raw:
    for fix_text in suggested_fixes_raw:
      # Try to extract file/line references from fix text
      file_path: Optional[str] = None
      line_no: Optional[int] = None
      line_range: Optional[Dict[str, int]] = None

      # Look for file path patterns (e.g., "src/file.py", "file.py:42", "at line 42")
      import re
      # Pattern: file.py:42 or file.py:42-50
      file_line_match = re.search(r'([a-zA-Z0-9_/\\\-\.]+\.(py|cpp|h|hpp|js|ts|java|go|rs))(?::(\d+)(?:-(\d+))?)?', fix_text)
      if file_line_match:
        file_path = file_line_match.group(1)
        if file_line_match.group(3):
          line_no = int(file_line_match.group(3))
          if file_line_match.group(4):
            line_range = {"start": line_no, "end": int(file_line_match.group(4))}

      # Look for "line X" or "at line X" patterns
      if not line_no:
        line_match = re.search(r'(?:at\s+)?line\s+(\d+)', fix_text, re.IGNORECASE)
        if line_match:
          line_no = int(line_match.group(1))

      # Extract confidence if mentioned in fix text
      fix_confidence = "medium"
      if "high confidence" in fix_text.lower() or "highly confident" in fix_text.lower():
        fix_confidence = "high"
      elif "low confidence" in fix_text.lower() or "uncertain" in fix_text.lower():
        fix_confidence = "low"

      # Find related log IDs by matching file paths or error messages
      related_log_ids: List[str] = []
      for entry in input_data.logs:
        if file_path and entry.log.file_path and file_path in entry.log.file_path:
          related_log_ids.append(entry.log.log_id)
        elif line_no and entry.log.line_no and abs(entry.log.line_no - line_no) <= 5:
          related_log_ids.append(entry.log.log_id)

      suggested_fixes.append(
        SuggestedFix(
          description=fix_text,
          file_path=file_path,
          line_no=line_no,
          line_range=line_range,
          related_log_ids=related_log_ids,
          confidence=fix_confidence,
        )
      )

  # Fallback: if no structured extraction worked, use response as summary
  if not summary and not root_cause:
    summary = response[:500]  # First 500 chars as summary
    root_cause = "Unable to extract structured root cause from model response."

  # Ensure we have at least basic content
  if not summary:
    summary = "Analysis completed, but summary could not be extracted."
  if not root_cause:
    root_cause = "Root cause analysis requires additional context or investigation."

  return RootCauseExplanation(
    summary=summary,
    root_cause=root_cause,
    error_location=error_location,
    key_evidence=key_evidence,
    suggested_fixes=suggested_fixes,
    confidence=confidence,
    raw_response=response,
    has_clear_remediation=has_clear_remediation,
  )


def extract_evidence_references(
  explanation: RootCauseExplanation,
  input_data: AnalysisInput,
) -> List[EvidenceReference]:
  """
  Extract evidence references from explanation and link them to input logs/code.

  This function identifies which logs and code snippets are most relevant based on:
  1. Error logs (ERROR/CRITICAL level)
  2. Logs mentioned in key_evidence text
  3. Code locations referenced in root_cause or key_evidence
  4. Logs with code snippets available

  Args:
    explanation: The parsed root-cause explanation
    input_data: The original analysis input with logs and code snippets

  Returns:
    List of EvidenceReference objects linking explanation to specific logs/code
  """
  references: List[EvidenceReference] = []

  # Strategy: Prioritize error logs, then logs with code context, then others
  # that might be mentioned in the evidence text

  # 1. Always include error logs (ERROR/CRITICAL) as primary evidence
  for entry in input_data.logs:
    if entry.log.level.upper() in ("ERROR", "CRITICAL"):
      # Find matching evidence text if available
      reason = f"Error log: {entry.log.message}"
      if explanation.key_evidence:
        # Try to find evidence text that mentions this log's details
        for evidence_text in explanation.key_evidence:
          if (
            entry.log.message.lower() in evidence_text.lower()
            or (entry.log.file_path and entry.log.file_path in evidence_text)
            or (entry.log.exception_type and entry.log.exception_type in evidence_text)
          ):
            reason = evidence_text
            break

      # Extract code location if available
      file_path = entry.log.file_path
      line_no = entry.log.line_no
      line_range = None

      if entry.code_snippet and entry.code_snippet.snippet_ok and entry.code_snippet.lines:
        # Calculate line range from snippet
        line_numbers = [line["line_no"] for line in entry.code_snippet.lines]
        if line_numbers:
          line_range = {"start": min(line_numbers), "end": max(line_numbers)}

      references.append(
        EvidenceReference(
          log_id=entry.log.log_id,
          reason=reason,
          file_path=file_path,
          line_no=line_no,
          line_range=line_range,
        )
      )

  # 2. Include logs with code snippets that are mentioned in root_cause or key_evidence
  # (avoid duplicates if already added as error logs)
  existing_log_ids = {ref.log_id for ref in references}
  for entry in input_data.logs:
    if entry.log.log_id in existing_log_ids:
      continue

    # Check if this log's details are mentioned in explanation
    mentioned = False
    reason = f"Log: {entry.log.message}"

    # Check root_cause
    if entry.log.file_path and entry.log.file_path in explanation.root_cause:
      mentioned = True
      reason = f"Referenced in root cause analysis: {entry.log.message}"

    # Check key_evidence
    for evidence_text in explanation.key_evidence:
      if (
        entry.log.message.lower() in evidence_text.lower()
        or (entry.log.file_path and entry.log.file_path in evidence_text)
        or (entry.log.module_name and entry.log.module_name in evidence_text)
      ):
        mentioned = True
        reason = evidence_text
        break

    # Include if mentioned and has code context (prioritize logs with code)
    if mentioned and entry.code_snippet and entry.code_snippet.snippet_ok:
      file_path = entry.log.file_path
      line_no = entry.log.line_no
      line_range = None

      if entry.code_snippet.lines:
        line_numbers = [line["line_no"] for line in entry.code_snippet.lines]
        if line_numbers:
          line_range = {"start": min(line_numbers), "end": max(line_numbers)}

      references.append(
        EvidenceReference(
          log_id=entry.log.log_id,
          reason=reason,
          file_path=file_path,
          line_no=line_no,
          line_range=line_range,
        )
      )

  # 3. Limit to top 5 most relevant evidence items
  # (Error logs first, then others with code context)
  if len(references) > 5:
    # Sort: error logs first, then by code availability
    def sort_key(ref: EvidenceReference) -> tuple:
      entry = next((e for e in input_data.logs if e.log.log_id == ref.log_id), None)
      if not entry:
        return (1, 0)  # No code context
      is_error = entry.log.level.upper() in ("ERROR", "CRITICAL")
      has_code = ref.file_path is not None and ref.line_range is not None
      return (0 if is_error else 1, 0 if has_code else 1)

    references = sorted(references, key=sort_key)[:5]

  return references


def generate_root_cause_explanation(
  input_data: AnalysisInput,
  context_lines: int = 5,
  roots: Optional[List[Path]] = None,
) -> RootCauseExplanation:
  """
  Generate a root-cause explanation for errors in the analysis input.

  This function:
  1. Builds a prompt from the analysis input
  2. Calls the AI model to generate an explanation
  3. Parses the response into a structured format
  4. Extracts evidence references linking explanation to logs/code
  5. Handles incomplete/ambiguous responses gracefully

  Args:
    input_data: AnalysisInput containing logs and code snippets
    context_lines: Number of context lines (already applied in input_data)
    roots: Source roots (already applied in input_data)

  Returns:
    RootCauseExplanation with structured analysis results and evidence references
  """
  # Build prompt
  prompt = build_analysis_prompt(input_data)

  # Call AI model
  model = get_ai_model()
  response = model.generate_explanation(prompt)

  # Parse response
  explanation = parse_model_response(response, input_data)

  # Extract evidence references
  evidence_refs = extract_evidence_references(explanation, input_data)
  explanation.evidence_references = evidence_refs

  return explanation


@dataclass
class CrossModuleAnalysisResult:
  """Result of cross-module/service analysis with component context."""

  explanation: RootCauseExplanation
  components: Dict[str, Any]  # Component breakdown: services, modules, counts
  logs_by_component: Dict[str, List[str]]  # Maps component identifiers to log IDs


def analyze_cross_module_incident(
  application_id: str,
  start_ts: float,
  end_ts: float,
  min_level: Optional[str] = None,
  module_names: Optional[List[str]] = None,
  service_names: Optional[List[str]] = None,
  limit: int = 100,
  context_lines: int = 5,
  roots: Optional[List[Path]] = None,
) -> CrossModuleAnalysisResult:
  """
  Analyze an incident across multiple services/modules.

  This function retrieves logs from multiple components, prepares analysis input,
  generates root-cause explanation, and returns component-level context.

  Args:
    application_id: Required application identifier
    start_ts: Start of time range (Unix timestamp, inclusive)
    end_ts: End of time range (Unix timestamp, inclusive)
    min_level: Optional minimum log level filter
    module_names: Optional list of module names to include
    service_names: Optional list of service names to include
    limit: Maximum number of records to return
    context_lines: Number of context lines for code snippets
    roots: Source roots for code context

  Returns:
    CrossModuleAnalysisResult with explanation and component breakdown
  """
  # Query logs across components
  records = analyze_time_range(
    application_id=application_id,
    start_ts=start_ts,
    end_ts=end_ts,
    min_level=min_level,
    module_name=module_names,
    service_name=service_names,
    limit=limit,
  )

  if not records:
    # Return empty result structure
    empty_explanation = RootCauseExplanation(
      summary="No logs found for the specified time range and component filters.",
      root_cause="No data available for analysis.",
    )
    return CrossModuleAnalysisResult(
      explanation=empty_explanation,
      components={"services": {}, "modules": {}},
      logs_by_component={},
    )

  # Prepare analysis input
  input_data = prepare_ai_analysis_input(records, context_lines=context_lines, roots=roots)

  # Generate explanation
  explanation = generate_root_cause_explanation(input_data, context_lines=context_lines, roots=roots)

  # Build component breakdown
  services: Dict[str, int] = {}
  modules: Dict[str, int] = {}
  logs_by_service: Dict[str, List[str]] = {}
  logs_by_module: Dict[str, List[str]] = {}

  for entry in input_data.logs:
    log = entry.log
    if log.service_name:
      services[log.service_name] = services.get(log.service_name, 0) + 1
      if log.service_name not in logs_by_service:
        logs_by_service[log.service_name] = []
      logs_by_service[log.service_name].append(log.log_id)

    if log.module_name:
      modules[log.module_name] = modules.get(log.module_name, 0) + 1
      if log.module_name not in logs_by_module:
        logs_by_module[log.module_name] = []
      logs_by_module[log.module_name].append(log.log_id)

  # Combine logs_by_component
  logs_by_component: Dict[str, List[str]] = {}
  for service, log_ids in logs_by_service.items():
    logs_by_component[f"service:{service}"] = log_ids
  for module, log_ids in logs_by_module.items():
    logs_by_component[f"module:{module}"] = log_ids

  components = {
    "services": services,
    "modules": modules,
    "total_components": len(services) + len(modules),
  }

  return CrossModuleAnalysisResult(
    explanation=explanation,
    components=components,
    logs_by_component=logs_by_component,
  )




