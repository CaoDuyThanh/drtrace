from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from importlib import resources
from typing import NoReturn, Optional, Tuple
from urllib import error, parse, request


def main(argv: list[str] | None = None) -> NoReturn:
  argv = list(sys.argv[1:] if argv is None else argv)

  if not argv or argv[0] not in {"status", "why", "query", "init-agent", "init"}:
    print("Usage: python -m drtrace {status|why|query|init-agent|init}", file=sys.stderr)
    print("  status        - Check daemon status", file=sys.stderr)
    print("  why           - Analyze why an error happened", file=sys.stderr)
    print("  query         - Manage saved analysis queries", file=sys.stderr)
    print("  init-agent    - Bootstrap default agent file (use --agent log-it for logging assistant, log-init for setup assistant)", file=sys.stderr)
    print("  init          - Interactive project initialization with config and templates", file=sys.stderr)
    sys.exit(1)

  if argv[0] == "status":
    _run_status()
  elif argv[0] == "why":
    _run_why(argv[1:])
  elif argv[0] == "query":
    _run_query(argv[1:])
  elif argv[0] == "init-agent":
    _run_init_agent(argv[1:])
  elif argv[0] == "init":
    _run_init_project(argv[1:])


def _run_status() -> None:
  host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
  port = int(os.getenv("DRTRACE_DAEMON_PORT", "8001"))
  url = f"http://{host}:{port}/status"

  try:
    with request.urlopen(url, timeout=1.0) as resp:  # nosec B310
      data = json.loads(resp.read().decode("utf-8"))
  except (error.URLError, error.HTTPError, TimeoutError, OSError):
    print(f"DrTrace daemon status: UNREACHABLE at {url}", file=sys.stderr)
    print("Hint: ensure the daemon is running and listening on this host/port.", file=sys.stderr)
    sys.exit(2)

  print("DrTrace daemon status: HEALTHY")
  print(f"Service: {data.get('service_name')} v{data.get('version')}")
  print(f"Listening on: {data.get('host')}:{data.get('port')}")
  sys.exit(0)


def _load_agent_spec(agent_name: str, skip_local: bool = False) -> str:
  """
  Load agent spec from root agents/ directory or fallback to packaged resources.

  Search order:
    1. Root repo directory: <repo>/agents/<agent-name>.md (development) - skipped if skip_local=True
    2. Packaged resources: drtrace_service.resources.agents.<agent-name>.md (installed)

  Args:
    agent_name: Name of the agent (e.g., 'log-analysis', 'log-it', 'log-init')
    skip_local: If True, skip local agents/ directory and use packaged resources only.
                Used when --force is specified to ensure we get the default spec.

  Returns:
    Agent spec content as string

  Raises:
    FileNotFoundError: If agent not found in either location
  """
  agent_filename = f"{agent_name}.md"

  # Try root agents/ first (development mode) - unless skip_local is True
  if not skip_local:
    root_agent_path = os.path.join(os.getcwd(), "agents", agent_filename)
    if os.path.isfile(root_agent_path):
      with open(root_agent_path, "r", encoding="utf-8") as f:
        return f.read()

  # Fallback to packaged resources (installed mode)
  try:
    with resources.open_text(
      "drtrace_service.resources.agents", agent_filename, encoding="utf-8"
    ) as f:
      return f.read()
  except FileNotFoundError as e:
    raise FileNotFoundError(
      f"Agent '{agent_name}' not found in agents/ or installed packages. "
      f"Ensure {agent_filename} is available."
    ) from e


def _run_init_agent(args: list[str]) -> None:
  """
  Bootstrap a default agent spec into the current project.

  By default this writes to ./agents/<agent-name>.md in the current working
  directory. Existing files are never overwritten unless --force is provided.

  Supported agents: log-analysis (default), log-it, log-init, log-help
  """
  parser = argparse.ArgumentParser(
    prog="drtrace init-agent",
    description="Bootstrap default agent spec into this project",
  )
  parser.add_argument(
    "--agent",
    default="log-analysis",
    choices=["log-analysis", "log-it", "log-init", "log-help"],
    help="Agent type to bootstrap (default: log-analysis)",
  )
  parser.add_argument(
    "--path",
    default=None,
    help="Target path for the agent file (default: agents/<agent-name>.md)",
  )
  parser.add_argument(
    "--force",
    action="store_true",
    help="Overwrite existing agent file without prompting",
  )
  parser.add_argument(
    "--backup",
    action="store_true",
    help="Create timestamped backup if the agent file already exists",
  )

  parsed = parser.parse_args(args)

  # Determine target path based on agent type if not explicitly provided
  if parsed.path is None:
    target_path = os.path.abspath(f"agents/{parsed.agent}.md")
  else:
    target_path = os.path.abspath(parsed.path)

  target_dir = os.path.dirname(target_path)

  # Ensure target directory exists
  os.makedirs(target_dir, exist_ok=True)

  # Load agent spec from root agents/ or packaged resources
  # When --force is specified, skip local agents/ to ensure we get the default spec
  try:
    default_contents = _load_agent_spec(parsed.agent, skip_local=parsed.force)
  except FileNotFoundError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

  # Handle existing file
  if os.path.exists(target_path):
    if not parsed.force and not parsed.backup:
      print(
        f"Agent file already exists at {target_path}.",
        file=sys.stderr,
      )
      print(
        "Use --force to overwrite or --backup to create a timestamped backup before overwriting.",
        file=sys.stderr,
      )
      sys.exit(1)

    if parsed.backup:
      timestamp = time.strftime("%Y%m%d-%H%M%S")
      backup_path = f"{target_path}.bak-{timestamp}"
      os.rename(target_path, backup_path)
      print(f"Existing agent file backed up to {backup_path}")

  # Write default contents
  with open(target_path, "w", encoding="utf-8") as f:
    f.write(default_contents)

  print(f"Default {parsed.agent} agent spec written to {target_path}")
  sys.exit(0)


def _parse_time_window(since: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None) -> Tuple[float, float]:
  """
  Parse time window from CLI arguments.

  Supports:
  - Relative: --since "5m" (last 5 minutes), "1h" (last hour), "30s" (last 30 seconds)
  - Explicit: --start <timestamp> --end <timestamp> (Unix timestamps)

  Returns:
    Tuple of (start_ts, end_ts) as Unix timestamps
  """
  now = time.time()

  if since:
    # Parse relative time (e.g., "5m", "1h", "30s")
    since_lower = since.lower().strip()
    try:
      if since_lower.endswith("s"):
        seconds = int(since_lower[:-1])
      elif since_lower.endswith("m"):
        seconds = int(since_lower[:-1]) * 60
      elif since_lower.endswith("h"):
        seconds = int(since_lower[:-1]) * 3600
      elif since_lower.endswith("d"):
        seconds = int(since_lower[:-1]) * 86400
      else:
        # Try to parse as integer seconds
        seconds = int(since_lower)
    except ValueError:
      raise ValueError(f"Invalid time format: {since}. Use format like '5m', '1h', '30s', or Unix timestamp")

    start_ts = now - seconds
    end_ts = now
  elif start and end:
    # Explicit timestamps
    try:
      start_ts = float(start)
      end_ts = float(end)
    except ValueError:
      raise ValueError("--start and --end must be Unix timestamps (floats)")
  else:
    raise ValueError("Must specify either --since or both --start and --end")

  if start_ts >= end_ts:
    raise ValueError("Start time must be before end time")

  return (start_ts, end_ts)


def _run_why(args: list[str]) -> None:
  """Run the 'why' command to analyze root causes."""
  parser = argparse.ArgumentParser(
    prog="drtrace why",
    description="Analyze why an error happened in a time window",
  )
  parser.add_argument(
    "--application-id",
    required=True,
    help="Application identifier",
  )
  parser.add_argument(
    "--since",
    help="Relative time window (e.g., '5m' for last 5 minutes, '1h' for last hour, '30s' for last 30 seconds)",
  )
  parser.add_argument(
    "--start",
    help="Start time (Unix timestamp)",
  )
  parser.add_argument(
    "--end",
    help="End time (Unix timestamp)",
  )
  parser.add_argument(
    "--min-level",
    choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
    help="Minimum log level to include",
  )
  parser.add_argument(
    "--module-name",
    help="Filter by module name",
  )
  parser.add_argument(
    "--service-name",
    help="Filter by service name",
  )
  parser.add_argument(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of logs to analyze (default: 100)",
  )

  parsed = parser.parse_args(args)

  # Parse time window
  try:
    start_ts, end_ts = _parse_time_window(
      since=parsed.since,
      start=parsed.start,
      end=parsed.end,
    )
  except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

  # Build URL
  host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
  port = int(os.getenv("DRTRACE_DAEMON_PORT", "8001"))
  base_url = f"http://{host}:{port}/analysis/why"

  params = {
    "application_id": parsed.application_id,
    "start_ts": start_ts,
    "end_ts": end_ts,
    "limit": parsed.limit,
  }
  if parsed.min_level:
    params["min_level"] = parsed.min_level
  if parsed.module_name:
    params["module_name"] = parsed.module_name
  if parsed.service_name:
    params["service_name"] = parsed.service_name

  url = f"{base_url}?{parse.urlencode(params)}"

  # Make request
  try:
    with request.urlopen(url, timeout=30.0) as resp:  # nosec B310
      data = json.loads(resp.read().decode("utf-8"))
  except error.HTTPError as e:
    if e.code == 400:
      error_data = json.loads(e.read().decode("utf-8"))
      detail = error_data.get("detail", {})
      if isinstance(detail, dict):
        print(f"Error: {detail.get('message', 'Bad request')}", file=sys.stderr)
        if detail.get("code") == "INVALID_TIME_RANGE":
          print("Hint: Ensure start time is before end time.", file=sys.stderr)
        elif detail.get("code") == "INVALID_LEVEL":
          print("Hint: Use one of: DEBUG, INFO, WARN, ERROR, CRITICAL", file=sys.stderr)
      else:
        print(f"Error: {detail}", file=sys.stderr)
    else:
      print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
    sys.exit(1)
  except (error.URLError, TimeoutError, OSError) as e:
    print(f"Error: Cannot connect to daemon at {base_url}", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    print("Hint: Ensure the daemon is running and listening on this host/port.", file=sys.stderr)
    sys.exit(2)

  # Check for no data
  if data.get("meta", {}).get("no_data"):
    print("No logs found for the specified time range and filters.")
    print(f"  Application: {parsed.application_id}")
    print(f"  Time range: {datetime.fromtimestamp(start_ts)} to {datetime.fromtimestamp(end_ts)}")
    sys.exit(0)

  # Format and print explanation
  explanation = data.get("data", {}).get("explanation")
  if not explanation:
    print("No explanation available.")
    sys.exit(0)

  print("=" * 70)
  print("ROOT CAUSE ANALYSIS")
  print("=" * 70)
  print()

  # Summary
  if explanation.get("summary"):
    print("Summary:")
    print(f"  {explanation['summary']}")
    print()

  # Root cause
  if explanation.get("root_cause"):
    print("Root Cause:")
    print(f"  {explanation['root_cause']}")
    print()

  # Error location
  if explanation.get("error_location"):
    loc = explanation["error_location"]
    print("Error Location:")
    if loc.get("file_path"):
      print(f"  File: {loc['file_path']}")
    if loc.get("line_no"):
      print(f"  Line: {loc['line_no']}")
    print()

  # Key evidence
  if explanation.get("key_evidence"):
    print("Key Evidence:")
    for evidence in explanation["key_evidence"]:
      print(f"  • {evidence}")
    print()

  # Evidence references
  if explanation.get("evidence_references"):
    print("Evidence References:")
    for ref in explanation["evidence_references"]:
      print(f"  • Log ID: {ref['log_id']}")
      print(f"    Reason: {ref['reason']}")
      if ref.get("file_path"):
        print(f"    Code: {ref['file_path']}", end="")
        if ref.get("line_no"):
          print(f":{ref['line_no']}", end="")
        if ref.get("line_range"):
          r = ref["line_range"]
          print(f" (lines {r['start']}-{r['end']})", end="")
        print()
      print()
    print()

  # Suggested fixes
  if explanation.get("suggested_fixes"):
    print("Suggested Fixes:")
    for fix in explanation["suggested_fixes"]:
      if isinstance(fix, dict):
        # Structured fix
        print(f"  • {fix.get('description', 'Fix')}")
        if fix.get("file_path"):
          print(f"    Location: {fix['file_path']}", end="")
          if fix.get("line_no"):
            print(f":{fix['line_no']}", end="")
          if fix.get("line_range"):
            r = fix["line_range"]
            print(f" (lines {r['start']}-{r['end']})", end="")
          print()
        if fix.get("related_log_ids"):
          print(f"    Related logs: {', '.join(fix['related_log_ids'][:3])}")
        if fix.get("confidence"):
          print(f"    Confidence: {fix['confidence'].upper()}")
      else:
        # Legacy string format (fallback)
        print(f"  • {fix}")
    print()
  elif not explanation.get("has_clear_remediation", True):
    print("Suggested Fixes:")
    print("  No clear remediation identified. Further investigation required.")
    print()

  # Confidence
  if explanation.get("confidence"):
    print(f"Confidence: {explanation['confidence'].upper()}")
    print()

  # Metadata
  meta = data.get("meta", {})
  print("-" * 70)
  print(f"Analyzed {meta.get('count', 0)} log(s) from {datetime.fromtimestamp(start_ts)} to {datetime.fromtimestamp(end_ts)}")
  sys.exit(0)


def _run_query(args: list[str]) -> None:
  """Run the 'query' command to manage saved queries."""
  parser = argparse.ArgumentParser(
    prog="drtrace query",
    description="Manage saved analysis queries",
  )
  subparsers = parser.add_subparsers(dest="command", help="Command to execute")

  # List command
  subparsers.add_parser("list", help="List all saved queries")

  # Create command
  create_parser = subparsers.add_parser("create", help="Create a new saved query")
  create_parser.add_argument("--name", required=True, help="Query name")
  create_parser.add_argument("--description", help="Query description")
  create_parser.add_argument("--application-id", required=True, help="Default application_id")
  create_parser.add_argument("--default-window", type=int, default=5, help="Default time window in minutes (default: 5)")
  create_parser.add_argument("--min-level", choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"], help="Default minimum log level")
  create_parser.add_argument("--module-names", nargs="+", help="Default module names")
  create_parser.add_argument("--service-names", nargs="+", help="Default service names")
  create_parser.add_argument("--limit", type=int, default=100, help="Default limit (default: 100)")
  create_parser.add_argument("--type", choices=["why", "cross-module"], default="why", help="Query type (default: why)")

  # Delete command
  delete_parser = subparsers.add_parser("delete", help="Delete a saved query")
  delete_parser.add_argument("--name", required=True, help="Query name to delete")

  # Run command
  run_parser = subparsers.add_parser("run", help="Run a saved query")
  run_parser.add_argument("--name", required=True, help="Query name to run")
  run_parser.add_argument("--since", help="Override time window (e.g., '5m', '1h')")
  run_parser.add_argument("--start", help="Override start time (Unix timestamp)")
  run_parser.add_argument("--end", help="Override end time (Unix timestamp)")
  run_parser.add_argument("--application-id", help="Override application_id")
  run_parser.add_argument("--min-level", choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"], help="Override min_level")
  run_parser.add_argument("--module-names", nargs="+", help="Override module names")
  run_parser.add_argument("--service-names", nargs="+", help="Override service names")
  run_parser.add_argument("--limit", type=int, help="Override limit")

  parsed = parser.parse_args(args)

  if not parsed.command:
    parser.print_help()
    sys.exit(1)

  from drtrace_service import saved_queries

  if parsed.command == "list":
    queries = saved_queries.list_queries()
    if not queries:
      print("No saved queries found.")
      sys.exit(0)

    print("Saved Queries:")
    print()
    for query in queries:
      print(f"  Name: {query.name}")
      if query.description:
        print(f"    Description: {query.description}")
      print(f"    Application ID: {query.application_id}")
      print(f"    Default window: {query.default_time_window_minutes} minutes")
      print(f"    Type: {query.query_type}")
      if query.min_level:
        print(f"    Min level: {query.min_level}")
      if query.module_names:
        print(f"    Module names: {', '.join(query.module_names)}")
      if query.service_names:
        print(f"    Service names: {', '.join(query.service_names)}")
      print()

  elif parsed.command == "create":
    query = saved_queries.SavedQuery(
      name=parsed.name,
      description=parsed.description,
      application_id=parsed.application_id,
      default_time_window_minutes=parsed.default_window,
      min_level=parsed.min_level,
      module_names=parsed.module_names or [],
      service_names=parsed.service_names or [],
      limit=parsed.limit,
      query_type=parsed.type,
    )
    saved_queries.save_query(query)
    print(f"Saved query '{parsed.name}' created successfully.")
    sys.exit(0)

  elif parsed.command == "delete":
    if saved_queries.delete_query(parsed.name):
      print(f"Query '{parsed.name}' deleted successfully.")
      sys.exit(0)
    else:
      print(f"Query '{parsed.name}' not found.", file=sys.stderr)
      sys.exit(1)

  elif parsed.command == "run":
    try:
      # Parse time window overrides
      start_ts_override = None
      end_ts_override = None
      if parsed.since:
        start_ts, end_ts = _parse_time_window(since=parsed.since)
        start_ts_override = start_ts
        end_ts_override = end_ts
      elif parsed.start and parsed.end:
        start_ts, end_ts = _parse_time_window(start=parsed.start, end=parsed.end)
        start_ts_override = start_ts
        end_ts_override = end_ts

      # Resolve query parameters
      params = saved_queries.resolve_query_params(
        query_name=parsed.name,
        start_ts=start_ts_override,
        end_ts=end_ts_override,
        application_id=parsed.application_id,
        min_level=parsed.min_level,
        module_names=parsed.module_names,
        service_names=parsed.service_names,
        limit=parsed.limit,
      )

      # Determine which endpoint to call
      query_type = params.pop("query_type", "why")
      endpoint = "/analysis/cross-module" if query_type == "cross-module" else "/analysis/why"

      # Build URL
      host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
      port = int(os.getenv("DRTRACE_DAEMON_PORT", "8001"))
      base_url = f"http://{host}:{port}{endpoint}"

      url_params = {
        "application_id": params["application_id"],
        "start_ts": params["start_ts"],
        "end_ts": params["end_ts"],
        "limit": params["limit"],
      }
      if params.get("min_level"):
        url_params["min_level"] = params["min_level"]
      if params.get("module_names"):
        for name in params["module_names"]:
          url_params.setdefault("module_names", []).append(name)
      if params.get("service_names"):
        for name in params["service_names"]:
          url_params.setdefault("service_names", []).append(name)

      url = f"{base_url}?{parse.urlencode(url_params, doseq=True)}"

      # Make request (reuse logic from _run_why)
      try:
        with request.urlopen(url, timeout=30.0) as resp:  # nosec B310
          data = json.loads(resp.read().decode("utf-8"))
      except error.HTTPError as e:
        if e.code == 400:
          error_data = json.loads(e.read().decode("utf-8"))
          detail = error_data.get("detail", {})
          if isinstance(detail, dict):
            print(f"Error: {detail.get('message', 'Bad request')}", file=sys.stderr)
          else:
            print(f"Error: {detail}", file=sys.stderr)
        else:
          print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        sys.exit(1)
      except (error.URLError, TimeoutError, OSError) as e:
        print(f"Error: Cannot connect to daemon at {base_url}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        print("Hint: Ensure the daemon is running and listening on this host/port.", file=sys.stderr)
        sys.exit(2)

      # Format and print explanation (reuse logic from _run_why)
      explanation = data.get("data", {}).get("explanation")
      if not explanation:
        if data.get("meta", {}).get("no_data"):
          print("No logs found for the specified time range and filters.")
        else:
          print("No explanation available.")
        sys.exit(0)

      print("=" * 70)
      print("ROOT CAUSE ANALYSIS")
      print("=" * 70)
      print()

      if explanation.get("summary"):
        print("Summary:")
        print(f"  {explanation['summary']}")
        print()

      if explanation.get("root_cause"):
        print("Root Cause:")
        print(f"  {explanation['root_cause']}")
        print()

      if explanation.get("error_location"):
        loc = explanation["error_location"]
        print("Error Location:")
        if loc.get("file_path"):
          print(f"  File: {loc['file_path']}")
        if loc.get("line_no"):
          print(f"  Line: {loc['line_no']}")
        print()

      if explanation.get("key_evidence"):
        print("Key Evidence:")
        for evidence in explanation["key_evidence"]:
          print(f"  • {evidence}")
        print()

      if explanation.get("suggested_fixes"):
        print("Suggested Fixes:")
        for fix in explanation["suggested_fixes"]:
          if isinstance(fix, dict):
            print(f"  • {fix.get('description', 'Fix')}")
            if fix.get("file_path"):
              print(f"    Location: {fix['file_path']}", end="")
              if fix.get("line_no"):
                print(f":{fix['line_no']}", end="")
              if fix.get("line_range"):
                r = fix["line_range"]
                print(f" (lines {r['start']}-{r['end']})", end="")
              print()
            if fix.get("related_log_ids"):
              print(f"    Related logs: {', '.join(fix['related_log_ids'][:3])}")
            if fix.get("confidence"):
              print(f"    Confidence: {fix['confidence'].upper()}")
          else:
            print(f"  • {fix}")
        print()
      elif not explanation.get("has_clear_remediation", True):
        print("Suggested Fixes:")
        print("  No clear remediation identified. Further investigation required.")
        print()

      if explanation.get("confidence"):
        print(f"Confidence: {explanation['confidence'].upper()}")
        print()

      meta = data.get("meta", {})
      print("-" * 70)
      print(f"Query: {parsed.name}")
      print(f"Analyzed {meta.get('count', 0)} log(s) from {datetime.fromtimestamp(params['start_ts'])} to {datetime.fromtimestamp(params['end_ts'])}")
      sys.exit(0)

    except ValueError as e:
      print(f"Error: {e}", file=sys.stderr)
      sys.exit(1)


def _run_init_project(args: list[str]) -> None:
  """Run the 'init-project' command for interactive project initialization."""
  from pathlib import Path

  from drtrace_service.cli.init_project import run_init_project

  parser = argparse.ArgumentParser(
    prog="drtrace init-project",
    description="Interactive project initialization with config and templates",
  )
  parser.add_argument(
    "--project-root",
    default=".",
    help="Project root directory (default: current directory)",
  )

  parsed = parser.parse_args(args)

  try:
    exit_code = run_init_project(Path(parsed.project_root))
    sys.exit(exit_code)
  except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
  main()


