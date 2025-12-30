# log-help Agent Guide

## Overview

The `log-help` agent is the **DrTrace Setup Guide**. It:

- Walks you through DrTrace setup in a **step-by-step** fashion.
- Tracks your progress across languages (Python, C++, JS/TS).
- Provides targeted **troubleshooting** when you get stuck.
- Integrates with the `setup_guide` and `help_agent_interface` components.

Use `log-help` when you want a **guided checklist** and interactive help, rather than raw suggestions.

## Activation

### 1. Bootstrap the agent file

From your project root:

```bash
python -m drtrace_service init-agent --agent log-help
```

This copies the default `log-help` spec into your project (e.g., `_drtrace/agents/log-help.md` or a custom path via `--path`).

### 2. Load the agent

- Point your IDE/agent host to `_drtrace/agents/log-help.md`, or  
- Use `@log-help` if supported.

On activation, the agent:

1. Loads its persona and rules.  
2. Explains that it will use the **setup guide APIs** and your project files to track progress.  
3. Shows a menu of actions such as “Start setup guide”, “What’s my current step?”, etc.

## Step-by-Step Guidance

The `log-help` agent orchestrates the `setup_guide` steps:

- **Start setup guide**
  - Initializes or resets the guide for a specific language (`python`, `cpp`, or `javascript`).
  - Shows **Step 1 of N** with:
    - Title
    - Description
    - Instructions
    - Verification criteria

- **What’s my current step?**
  - Retrieves the current step from the guide.
  - Displays progress as “Step X of Y”, plus what you need to do now.

- **Mark step complete**
  - Verifies (best effort) that you’ve done the work.
  - Marks the step complete and moves to the next one.

- **I’m stuck**
  - Accepts a free‑form issue description.
  - Maps it to common setup problems:
    - Daemon not connecting
    - Import errors
    - Config issues
    - Logs not appearing
  - Returns a structured troubleshooting checklist and verification steps.

- **Show all steps**
  - Prints the full checklist for the current language with completion state.

## Progress Tracking

Progress is tracked via:

- The underlying `setup_guide` component and/or  
- Saved state in your `_drtrace` configuration (depending on implementation).

You can:

- Resume where you left off by asking “What’s my current step?”.  
- See the full picture via “Show all steps”.  
- Reset the guide by starting a new guide for the same language via “Start setup guide”.

## Menu Items

From `log-help.md`:

- **`S` – Start setup guide**
  - Calls `start_setup_guide(language, project_root)`.
  - Good when you’re beginning setup for a given language.

- **`C` – What’s my current step?**
  - Calls `get_current_step(project_root)`.
  - Good when you’re returning to a project or unsure what’s next.

- **`M` – Mark step complete**
  - Calls `complete_step(step_number, project_root)`.
  - Good after you’ve followed a step’s instructions and want to move forward.

- **`T` – I’m stuck**
  - Calls `troubleshoot(issue, project_root)`.
  - Best for diagnosing problems like daemon connectivity, missing dependencies, or config errors.

- **`L` – Show all steps**
  - Displays the full checklist and which steps are done vs. pending.

- **`D` – Dismiss Agent**
  - Ends the guided session.

## Usage Examples

### Python Setup Walkthrough

1. **Start the guide**  
   > “Start Python setup guide for this project.”  
   The agent calls `start_setup_guide(language="python", project_root=Path("."))` and shows **Step 1 of N**, such as:

   ```markdown
   # Setup Guide: Python

   ## Progress: Step 1 of 7

   ### Step 1: Install DrTrace package

   **Instructions:**
   1. Activate your virtualenv
   2. Run: `pip install drtrace-service`

   **Verification:**
   - `python -c "import drtrace_client, drtrace_service"` succeeds
   ```

2. **Mark step complete**  
   After running the commands and verifying imports:

   > “Mark step 1 complete.”  

   The agent calls `complete_step(step_number=1, project_root=...)` and advances to the next step.

3. **Continue through steps**  
   Steps might include:
   - Run `init-project`
   - Add `setup_logging()` to your entry file
   - Test log ingestion and analysis

### C++ Setup Walkthrough

For a C++ project with CMake:

1. Start the C++ setup guide:

   > “Start C++ setup guide for this project.”

2. Follow steps such as:
   - Install the C++ client (via FetchContent).
   - Update `CMakeLists.txt` with the DrTrace block.
   - Add `drtrace_sink.hpp` and spdlog integration to `main.cpp`.
   - Build and run the app to verify logs reach the daemon.

3. Use **“I’m stuck”** when:
   - CMake fails to configure or build.
   - The executable cannot find DrTrace symbols.
   - Logs don’t appear in DrTrace even though the app runs.

### JavaScript/TypeScript Setup Walkthrough

For JS/TS:

1. Start the JS setup guide:

   > “Start JavaScript setup guide for this Node/TS project.”

2. Steps include:
   - Install `drtrace` via npm/yarn/pnpm.
   - Add initialization to `main.ts` or `index.js`.
   - Configure environment variables for the daemon.
   - Run the application and verify logs are captured.

3. Use **“What’s my current step?”** before each session to resume where you left off.

### Multi-Language Troubleshooting

When you have Python + C++ + JS:

1. Use **log-init** to generate a structured suggestions report.  
2. Use **init-project** to apply suggestions where safe.  
3. Use **log-help** to:
   - Walk language‑specific setup guides.
   - Troubleshoot cross‑language issues like:
     - Daemon URL mismatches.
     - Missing environment variables.
     - Incorrect CMake or package.json changes.

## Troubleshooting with log-help

Common prompts:

- **Daemon not connecting**
  - “I’m stuck – daemon not connecting.”
  - Agent suggests:
    - Checking `DRTRACE_DAEMON_URL` / host/port.
    - Running `python -m drtrace_service status`.
    - Verifying Docker / uvicorn is running.

- **Import errors**
  - “I’m stuck – `ModuleNotFoundError: drtrace_client`.”
  - Agent suggests:
    - Installing the proper package (editable install in repo, or `pip install drtrace-service`).
    - Verifying virtualenv activation.

- **Config issues**
  - “I’m stuck – not sure if my config is correct.”
  - Agent suggests:
    - Reviewing `_drtrace/config.json` and env files.
    - Checking for matching `application_id` between app and daemon queries.

- **Logs not appearing**
  - “I’m stuck – logs aren’t appearing in DrTrace.”
  - Agent suggests:
    - Verifying DrTrace is enabled in env/config.
    - Ensuring setup code is executed on startup.
    - Checking daemon logs for ingestion errors.

For each scenario, the agent includes **verification steps** so you can confirm fixes.

## Relationship to log-init and init-project

- **`log-init`**:
  - Focuses on **analysis and suggestion generation**.
  - Produces markdown with integration points, code, and config changes.

- **`init-project`**:
  - Focuses on **bootstrap and automatic application** of many suggestions.
  - Modifies project files with backups.

- **`log-help`**:
  - Focuses on **interactive guidance and troubleshooting**.
  - Helps you execute, verify, and debug the steps suggested by `log-init` and applied by `init-project`.

Together, they provide:

1. Intelligent suggestions (`log-init`).  
2. Automated application (`init-project`).  
3. Guided execution and debugging (`log-help`).  


