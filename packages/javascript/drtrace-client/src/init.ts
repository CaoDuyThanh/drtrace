/**
 * Interactive project initialization for DrTrace (JavaScript/TypeScript)
 * Mirrors Python init_project.py with interactive prompts via prompts library
 */

import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import prompts from "prompts";
import { ConfigSchema, DrTraceConfig } from "./config-schema";

export interface InitOptions {
  projectRoot?: string;
  nonInteractive?: boolean;
  config?: Partial<DrTraceConfig>;
}

export class ProjectInitializer {
  private projectRoot: string;
  private drtraceDir: string;
  private configPath: string;

  constructor(projectRoot: string = process.cwd()) {
    this.projectRoot = projectRoot;
    this.drtraceDir = path.join(projectRoot, "_drtrace");
    this.configPath = path.join(this.drtraceDir, "config.json");
  }

  /**
   * Run the interactive initialization workflow
   */
  async runInteractive(): Promise<boolean> {
    console.log("\n🚀 DrTrace Project Initialization\n");
    console.log("=".repeat(50));

    // Check for existing config FIRST (before collecting project info)
    if (!(await this.handleExistingConfig())) {
      console.log("\n❌ Initialization cancelled.");
      return false;
    }

    // Collect project information
    console.log("\n📋 Project Information:");
    const projectName = await this.promptText(
      "Project name",
      "my-app"
    );
    const applicationId = await this.promptText(
      "Application ID",
      projectName.toLowerCase().replace(/\s+/g, "-")
    );

    // Language selection
    console.log("\n🔧 Technology Stack:");
    const language = await this.promptChoice(
      "Select language/runtime:",
      ["python", "javascript", "cpp", "both"],
      "javascript"
    );

    // Daemon configuration
    console.log("\n📡 DrTrace Daemon Configuration:");
    const daemonUrl = await this.promptText(
      "Daemon URL",
      "http://localhost:8001"
    );
    const enabled = await this.promptYesNo("Enable DrTrace by default?", true);

    // Environment selection
    console.log("\n🌍 Environments:");
    const selectedEnvs = await this.promptMultiSelect(
      "Which environments to configure?",
      ["development", "staging", "production", "ci"]
    );
    const environments = selectedEnvs.length > 0 ? selectedEnvs : ["development"];

    // Agent configuration
    console.log("\n🤖 Agent Integration (Optional):");
    const agentEnabled = await this.promptYesNo(
      "Enable agent interface?",
      false
    );

    let agentFramework = "bmad";
    if (agentEnabled) {
      agentFramework = await this.promptChoice(
        "Select agent framework:",
        ["bmad", "langchain", "other"],
        "bmad"
      );
    }

    // Create directory structure
    this.createDirectoryStructure();

    // Generate and save main config
    const config = ConfigSchema.getDefaultConfig({
      project_name: projectName,
      application_id: applicationId,
      language: language as "python" | "javascript" | "cpp" | "both",
      daemon_url: daemonUrl,
      enabled,
      environments,
      agent_enabled: agentEnabled,
      agent_framework: agentFramework as "bmad" | "langchain" | "other",
    });

    ConfigSchema.save(config, this.configPath);
    console.log(`\n✓ Main config created: ${this.configPath}`);

    // Generate environment-specific configs
    this.generateEnvironmentConfigs(config);

    // Copy default agent spec
    if (agentEnabled) {
      this.copyAgentSpec();
    }

    // Copy framework-specific guides for C++ projects
    if (language === "cpp" || language === "both") {
      this.copyFrameworkGuides();
      // Copy C++ header file for C++ projects
      this.copyCppHeader();
    }

    // Generate .env.example
    this.generateEnvExample(config);

    // Generate README
    this.generateReadme();

    // Summary and next steps
    this.printSummary(config);

    return true;
  }

  /**
   * Prompt for text input
   */
  private async promptText(
    question: string,
    defaultValue?: string
  ): Promise<string> {
    const response = await prompts({
      type: "text",
      name: "value",
      message: question,
      initial: defaultValue,
    });
    return response.value || defaultValue || "";
  }

  /**
   * Prompt for yes/no
   */
  private async promptYesNo(
    question: string,
    defaultValue: boolean = true
  ): Promise<boolean> {
    const response = await prompts({
      type: "confirm",
      name: "value",
      message: question,
      initial: defaultValue,
    });
    return response.value;
  }

  /**
   * Prompt for single choice
   */
  private async promptChoice(
    question: string,
    choices: string[],
    defaultValue?: string
  ): Promise<string> {
    const response = await prompts({
      type: "select",
      name: "value",
      message: question,
      choices: choices.map((c) => ({ title: c, value: c })),
      initial: defaultValue ? choices.indexOf(defaultValue) : 0,
    });
    return response.value;
  }

  /**
   * Prompt for multiple selections
   */
  private async promptMultiSelect(
    question: string,
    choices: string[]
  ): Promise<string[]> {
    const response = await prompts({
      type: "multiselect",
      name: "value",
      message: question,
      choices: choices.map((c) => ({ title: c, value: c })),
      initial: 0, // Development selected by default
    });
    return response.value || [];
  }

  /**
   * Handle existing config - prompt user before overwriting
   * 
   * Returns true if initialization should proceed, false if user declined.
   */
  private async handleExistingConfig(): Promise<boolean> {
    if (!fs.existsSync(this.configPath)) {
      return true; // No existing config, proceed
    }

    console.log(
      `\n⚠️  Configuration already exists at ${this.configPath}`
    );

    // Prompt user if they want to overwrite
    const overwriteResponse = await prompts({
      type: "confirm",
      name: "value",
      message: "Overwrite existing configuration?",
      initial: false, // Default to No (safe)
    });

    if (!overwriteResponse.value) {
      return false; // User declined, stop initialization
    }

    // Optional: Offer backup
    const backupResponse = await prompts({
      type: "confirm",
      name: "value",
      message: "Create backup of existing config?",
      initial: true, // Default to Yes (safe)
    });

    if (backupResponse.value) {
      const backupPath = this.configPath + ".bak";
      fs.copyFileSync(this.configPath, backupPath);
      console.log(`✓ Backup created at ${backupPath}`);
    }

    return true; // User confirmed, proceed with overwrite
  }

  /**
   * Create _drtrace directory structure
   */
  private createDirectoryStructure(): void {
    const agentsDir = path.join(this.drtraceDir, "agents");
    const integrationGuidesDir = path.join(this.drtraceDir, "agents", "integration-guides");
    fs.mkdirSync(agentsDir, { recursive: true });
    fs.mkdirSync(integrationGuidesDir, { recursive: true });
    console.log(`✓ Created directory: ${this.drtraceDir}`);
  }

  /**
   * Generate environment-specific configs
   */
  private generateEnvironmentConfigs(baseConfig: DrTraceConfig): void {
    const environments = baseConfig.environments || ["development"];

    for (const env of environments) {
      const envConfig = { ...baseConfig };
      const envConfigPath = path.join(this.drtraceDir, `config.${env}.json`);
      ConfigSchema.save(envConfig, envConfigPath);
      console.log(`✓ Generated: ${envConfigPath}`);
    }
  }

  /**
   * Copy all agent files from packaged resources to _drtrace/agents/
   * Copies everything from agents/ directory including:
   * - Agent spec files (*.md)
   * - Integration guides (integration-guides/*.md)
   * - Any other files (README.md, CONTRIBUTING.md, etc.)
   */
  private copyAgentSpec(): void {
    try {
      // Try multiple locations for agents directory
      const possibleAgentsDirs = [
        // Installed package location - dist/resources/agents (production)
        path.join(this.projectRoot, "node_modules", "drtrace", "dist", "resources", "agents"),
        // Installed package location - agents (legacy, may be empty)
        path.join(this.projectRoot, "node_modules", "drtrace", "agents"),
        // Development mode (monorepo)
        path.join(process.cwd(), "agents"),
        // Relative to package
        path.resolve(__dirname, "../../agents"),
        // Relative to dist
        path.resolve(__dirname, "../agents"),
      ];

      let agentsDir: string | null = null;
      for (const dir of possibleAgentsDirs) {
        if (fs.existsSync(dir) && fs.statSync(dir).isDirectory()) {
          agentsDir = dir;
          break;
        }
      }

      if (!agentsDir) {
        console.warn("⚠️  Could not find agents directory");
        return;
      }

      // Copy all files recursively
      this.copyAgentsRecursive(agentsDir, path.join(this.drtraceDir, "agents"));
    } catch (error) {
      console.warn(`⚠️  Could not copy agent files: ${error}`);
    }
  }

  /**
   * Recursively copy all files from sourceDir to targetDir
   */
  private copyAgentsRecursive(sourceDir: string, targetDir: string): void {
    if (!fs.existsSync(targetDir)) {
      fs.mkdirSync(targetDir, { recursive: true });
    }

    const entries = fs.readdirSync(sourceDir, { withFileTypes: true });
    let copiedCount = 0;

    for (const entry of entries) {
      const srcPath = path.join(sourceDir, entry.name);
      const destPath = path.join(targetDir, entry.name);

      if (entry.isDirectory()) {
        // Recursively copy directories
        this.copyAgentsRecursive(srcPath, destPath);
      } else {
        // Copy file (no renaming needed - files are already named correctly)
        fs.copyFileSync(srcPath, destPath);
        copiedCount++;
        console.log(`✓ Copied ${entry.name}`);
      }
    }

    if (copiedCount > 0 && !fs.existsSync(path.join(targetDir, "..", ".."))) {
      // Only print summary if we're at the top level
      const relativeSource = path.relative(process.cwd(), sourceDir);
      if (!relativeSource.includes("..")) {
        console.log(`✓ Successfully copied ${copiedCount} file(s) from agents/`);
      }
    }
  }

  /**
   * Copy framework-specific integration guides to _drtrace/agents/integration-guides/
   * Dynamically discovers all .md files in agents/integration-guides/ directory
   * Guides are stored in agents folder so agents can access them on client side
   */
  private copyFrameworkGuides(): void {
    const integrationGuidesDir = path.join(this.drtraceDir, "agents", "integration-guides");
    fs.mkdirSync(integrationGuidesDir, { recursive: true });
    
    // Dynamically discover framework guides from agents/integration-guides/ directory
    const rootGuidesDir = path.join(process.cwd(), "agents", "integration-guides");
    let frameworkGuides: string[] = [];
    
    // Try root agents/integration-guides/ first (development mode)
    if (fs.existsSync(rootGuidesDir)) {
      try {
        const files = fs.readdirSync(rootGuidesDir);
        frameworkGuides = files
          .filter((file) => file.endsWith(".md"))
          .map((file) => file.replace(/\.md$/, ""));
      } catch (error) {
        // If directory exists but can't read it, warn and continue
        console.warn(`⚠️  Could not read integration guides directory: ${error}`);
      }
    }
    
    // If no guides found in development mode, try bundled resources (production mode)
    if (frameworkGuides.length === 0) {
      try {
        // Try to load from bundled resources (production mode)
        // Path: node_modules/drtrace/dist/resources/agents/integration-guides/
        // Note: In production, __dirname points to dist/ directory
        const bundledResourcesPath = path.join(
          __dirname,
          "resources",
          "agents",
          "integration-guides"
        );
        if (fs.existsSync(bundledResourcesPath)) {
          const files = fs.readdirSync(bundledResourcesPath);
          frameworkGuides = files
            .filter((file) => file.endsWith(".md"))
            .map((file) => file.replace(/\.md$/, ""));
        }
      } catch (error) {
        // If bundled resources not available, continue gracefully
        // This is expected in development mode when resources aren't bundled yet
      }
    }

    // Copy each discovered guide
    for (const guideName of frameworkGuides) {
      try {
        const guideFilename = `${guideName}.md`;
        const guidePath = path.join(integrationGuidesDir, guideFilename);
        
        // Try root agents/integration-guides/ first (development mode)
        const rootGuidePath = path.join(rootGuidesDir, guideFilename);
        let content: string;
        
        if (fs.existsSync(rootGuidePath)) {
          content = fs.readFileSync(rootGuidePath, "utf-8");
        } else {
          // Try to load from bundled resources (production mode)
          try {
            const bundledGuidePath = path.join(
              __dirname,
              "resources",
              "agents",
              "integration-guides",
              guideFilename
            );
            if (fs.existsSync(bundledGuidePath)) {
              content = fs.readFileSync(bundledGuidePath, "utf-8");
            } else {
              // Skip if guide not found
              continue;
            }
          } catch (error) {
            // Skip if guide not found
            continue;
          }
        }
        
        fs.writeFileSync(guidePath, content);
        console.log(`✓ Copied framework guide: ${guidePath}`);
      } catch (error) {
        console.warn(`⚠️  Could not copy ${guideName} framework guide: ${error}`);
      }
    }
  }

  /**
   * Copy C++ header file to third_party/drtrace/ for C++ projects.
   * 
   * This enables header-only integration:
   *   - Header is copied to third_party/drtrace/drtrace_sink.hpp
   *   - Users include it via #include "third_party/drtrace/drtrace_sink.hpp"
   *   - Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)
   */
  private copyCppHeader(): void {
    const sourcePath = this.findCppHeaderSource();
    if (!sourcePath || !fs.existsSync(sourcePath)) {
      console.warn(
        "⚠️  Could not find drtrace_sink.hpp - C++ header-only integration " +
        "will not be available."
      );
      return;
    }

    // Destination: third_party/drtrace/drtrace_sink.hpp (committed to git)
    const destDir = path.join(this.projectRoot, "third_party", "drtrace");
    fs.mkdirSync(destDir, { recursive: true });
    const destPath = path.join(destDir, "drtrace_sink.hpp");
    
    try {
      fs.copyFileSync(sourcePath, destPath);
      console.log(`✓ Copied C++ header: ${destPath}`);
      console.log("  Note: third_party/drtrace/ should be committed to git");
    } catch (error) {
      console.warn(
        `⚠️  Failed to copy C++ header from ${sourcePath} to ${destPath}: ${error}`
      );
    }
  }

  /**
   * Find drtrace_sink.hpp source file for header-only C++ integration.
   * 
   * Search order:
   *   1. npm package location: dist/resources/cpp/drtrace_sink.hpp (production mode)
   *   2. Monorepo development layout: packages/cpp/drtrace-client/src/drtrace_sink.hpp
   *   3. pip package location: site-packages/drtrace_service/.../packages/cpp/drtrace-client/src/drtrace_sink.hpp (if Python available)
   * 
   * @returns Path to header file if found, null otherwise
   */
  private findCppHeaderSource(): string | null {
    // 1. Check npm package location (production mode)
    // Path: node_modules/drtrace/dist/resources/cpp/drtrace_sink.hpp
    // In production, __dirname points to dist/ directory
    const npmPackagePath = path.join(
      __dirname,
      "resources",
      "cpp",
      "drtrace_sink.hpp"
    );
    if (fs.existsSync(npmPackagePath)) {
      return npmPackagePath;
    }

    // 2. Check monorepo location (development mode)
    // Search upward from project root (max 6 levels)
    let searchRoot = process.cwd();
    for (let i = 0; i < 6; i++) {
      const monorepoPath = path.join(
        searchRoot,
        "packages",
        "cpp",
        "drtrace-client",
        "src",
        "drtrace_sink.hpp"
      );
      if (fs.existsSync(monorepoPath)) {
        return monorepoPath;
      }
      
      const parent = path.dirname(searchRoot);
      if (parent === searchRoot) {
        break; // Reached filesystem root
      }
      searchRoot = parent;
    }

    // 3. Check pip package location (if Python available)
    // Try to use Python to find the package location
    try {
      const pythonCmd = `python3 -c "import drtrace_service; import os; print(os.path.dirname(drtrace_service.__file__))"`;
      const packageDir = execSync(pythonCmd, { encoding: "utf-8" }).trim();
      const pipPackagePath = path.join(
        packageDir,
        "packages",
        "cpp",
        "drtrace-client",
        "src",
        "drtrace_sink.hpp"
      );
      if (fs.existsSync(pipPackagePath)) {
        return pipPackagePath;
      }
    } catch (error) {
      // Python not available or package not installed - continue
    }

    return null;
  }

  /**
   * Get default agent spec from shared agents/ or bundled resources
   * 
   * Search order:
   *   1. Root repo agents/ directory (development)
   *   2. Bundled default agent from node_modules
   * 
   * @param agentName - Name of the agent: "log-analysis", "log-it", "log-init", or "log-help"
   */
  private getDefaultAgentSpec(agentName: "log-analysis" | "log-it" | "log-init" | "log-help" = "log-analysis"): string {
    // Try multiple possible locations for agents folder
    // Search order optimized: installed package first (most common), then repo root (development)
    const possiblePaths: string[] = [];

    // 1. Try node_modules/drtrace/agents/ directly from project root (most common case)
    const nodeModulesPath = path.join(this.projectRoot, "node_modules", "drtrace", "agents", `${agentName}.md`);
    possiblePaths.push(nodeModulesPath);

    // 2. Try to find from installed package location (if installed via npm)
    try {
      // Try to resolve the main entry point first, then find package.json
      const mainPath = require.resolve("drtrace");
      const packageDir = path.dirname(mainPath);
      // Go up to find package.json (main might be in dist/ or root)
      let currentDir = packageDir;
      for (let i = 0; i < 3; i++) {
        const pkgJsonPath = path.join(currentDir, "package.json");
        if (fs.existsSync(pkgJsonPath)) {
          possiblePaths.push(path.join(currentDir, "agents", `${agentName}.md`));
          break;
        }
        currentDir = path.dirname(currentDir);
      }
    } catch (error) {
      // Package not found, skip this path
    }

    // 3. From project root (when package is in monorepo or installed locally)
    possiblePaths.push(path.join(this.projectRoot, "..", "..", "..", "agents", `${agentName}.md`));
    
    // 4. Try absolute path from known repo structure
    possiblePaths.push(path.resolve(this.projectRoot, "../../../agents", `${agentName}.md`));

    for (const agentPath of possiblePaths) {
      try {
        if (fs.existsSync(agentPath)) {
          return fs.readFileSync(agentPath, "utf-8");
        }
      } catch (error) {
        // Continue to next path
        continue;
      }
    }

    // Fallback to bundled default agent
    return this.getBundledAgentSpec(agentName);
  }

  /**
   * Get bundled agent spec (fallback when root agents/ not available)
   * 
   * @param agentName - Name of the agent: "log-analysis", "log-it", "log-init", or "log-help"
   */
  private getBundledAgentSpec(agentName: "log-analysis" | "log-it" | "log-init" | "log-help" = "log-analysis"): string {
    if (agentName === "log-it") {
      // Return minimal log-it agent spec
      return `---
name: "log-it"
description: "Strategic Logging Assistant"
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified. NEVER break character until given an exit command.

\`\`\`xml
<agent id="log-it.agent.yaml" name="drtrace" title="Strategic Logging Assistant" icon="📝">
<activation critical="MANDATORY">
  <step n="1">Load persona from this current agent file (already in context)</step>
  <step n="2">Remember: You are a Strategic Logging Assistant specializing in efficient, privacy-conscious logging</step>
  <step n="3">NEVER suggest logging code without first seeing actual code context from the user</step>
  <step n="4">When user provides code, detect language automatically and apply appropriate patterns</step>
  <step n="5">Validate EVERY suggested log statement against all 5 criteria:
    1. **Efficiency**: Not in tight loops, uses lazy formatting, appropriate log level
    2. **Necessity**: Provides actionable insight, explains WHY not just THAT, prevents spam
    3. **No Sensitive Data**: Never logs passwords/tokens/PII, flags patterns, suggests masking
    4. **Code Context**: Strategic placement (entry/exit, external calls, errors, decisions)
    5. **Completeness**: Includes debug-worthy context (trace IDs, inputs/outputs, error details)
  </step>
  <step n="6">Always provide line numbers, log level reasoning, and copy-paste ready code</step>
  <step n="7">Show greeting, then display numbered list of ALL menu items from menu section</step>
  <step n="8">STOP and WAIT for user input - do NOT execute menu items automatically</step>
  <step n="9">On user input: Process as natural language query or execute menu item if number/cmd provided</step>
</activation>

<persona>
  <role>Strategic Logging Assistant</role>
  <identity>Expert at adding strategic, efficient, and privacy-conscious logging to codebases</identity>
  <communication_style>Clear and concise. Provides actionable logging suggestions with reasoning.</communication_style>
</persona>
\`\`\`

## Strategic Logging Guide

This agent helps you add effective logging to your codebase.

### How to Use

1. Share your code file or snippet
2. Describe what you want to log or debug
3. Get strategic logging suggestions with reasoning
`;
    }

    if (agentName === "log-init") {
      // Return minimal log-init agent spec
      return `---
name: "log-init"
description: "DrTrace Setup Assistant"
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified. NEVER break character until given an exit command.

\`\`\`xml
<agent id="log-init.agent.yaml" name="drtrace" title="DrTrace Setup Assistant" icon="🔧">
<activation critical="MANDATORY">
  <step n="1">Load persona from this current agent file (already in context)</step>
  <step n="2">Remember: You are a Setup Specialist for DrTrace integration</step>
  <step n="3">NEVER suggest setup without first reading and analyzing actual project files</step>
  <step n="4">Show greeting, then display numbered list of ALL menu items from menu section</step>
  <step n="5">STOP and WAIT for user input - do NOT execute menu items automatically</step>
</activation>

<persona>
  <role>Setup Specialist</role>
  <identity>Expert at analyzing project structures and suggesting intelligent DrTrace integration</identity>
  <communication_style>Clear and educational. Reads and analyzes project files before suggesting setup.</communication_style>
</persona>
\`\`\`

## Setup Guide

This agent helps you set up DrTrace in your project by analyzing your codebase and providing language-specific integration suggestions.
`;
    }

    if (agentName === "log-help") {
      // Return minimal log-help agent spec
      return `---
name: "log-help"
description: "DrTrace Setup Guide"
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified. NEVER break character until given an exit command.

\`\`\`xml
<agent id="log-help.agent.yaml" name="drtrace" title="DrTrace Setup Guide" icon="📘">
<activation critical="MANDATORY">
  <step n="1">Load persona from this current agent file (already in context)</step>
  <step n="2">Remember: You are a Setup Guide Assistant</step>
  <step n="3">Show greeting, then display numbered list of ALL menu items from menu section</step>
  <step n="4">STOP and WAIT for user input - do NOT execute menu items automatically</step>
</activation>

<persona>
  <role>Setup Guide Assistant</role>
  <identity>Expert at providing step-by-step guidance for DrTrace setup</identity>
  <communication_style>Patient and educational. Provides clear, actionable steps.</communication_style>
</persona>
\`\`\`

## Setup Guide

This agent provides step-by-step guidance for setting up DrTrace in your project, tracking your progress and helping when you get stuck.
`;
    }

    // Default log-analysis agent spec
    return `---
name: "log-analysis"
description: "Log Analysis Agent"
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified. NEVER break character until given an exit command.

\`\`\`xml
<agent id="log-analysis.agent.yaml" name="drtrace" title="Log Analysis Agent" icon="📊">
<activation critical="MANDATORY">
  <step n="1">Load persona from this current agent file (already in context)</step>
  <step n="2">Remember: You are a Log Analysis Specialist</step>
  <step n="3">Show greeting, then display numbered list of menu items</step>
  <step n="4">STOP and WAIT for user input</step>
  <step n="5">On user input: Process as natural language query</step>
</activation>

<persona>
  <role>Log Analysis Specialist</role>
  <identity>Expert at analyzing application logs and identifying root causes of errors</identity>
  <communication_style>Clear and concise. Provides structured markdown responses.</communication_style>
</persona>
\`\`\`

## Log Analysis Guide

This agent helps you understand what went wrong in your application by analyzing logs.

### How to Use

1. Describe the error or issue
2. Provide log entries or time window
3. Get root cause analysis with suggested fixes
`;
  }
  private generateEnvExample(config: DrTraceConfig): void {
    const envFile = path.join(this.drtraceDir, ".env.example");
    const content = `# DrTrace Configuration - Copy to .env and customize

# Basic Configuration
DRTRACE_APPLICATION_ID=${config.application_id}
DRTRACE_DAEMON_URL=${config.daemon_url || "http://localhost:8001"}
DRTRACE_ENABLED=${config.enabled !== false ? "true" : "false"}

# Environment-specific overrides
# Uncomment and modify for your environment
# DRTRACE_DAEMON_HOST=localhost
# DRTRACE_DAEMON_PORT=8001
# DRTRACE_RETENTION_DAYS=7

# Agent configuration
# DRTRACE_AGENT_ENABLED=false
# DRTRACE_AGENT_FRAMEWORK=bmad
`;
    fs.writeFileSync(envFile, content);
    console.log(`✓ Generated: ${envFile}`);
  }

  /**
   * Generate README.md
   */
  private generateReadme(): void {
    const readmeFile = path.join(this.drtraceDir, "README.md");
    const content = `# DrTrace Configuration Guide

This directory contains configuration files for the DrTrace (Web Workflow Integration) system.

## Files

- **config.json** - Main project configuration
- **config.{environment}.json** - Environment-specific overrides
- **.env.example** - Environment variable template
- **agents/** - Agent specifications and custom rules

## Configuration

### Basic Setup

1. Review and customize \`config.json\`
2. For environment-specific settings, edit \`config.{environment}.json\`
3. Create \`.env\` from \`.env.example\` and set your environment variables

### Environment Variables

- \`DRTRACE_APPLICATION_ID\` - Unique application identifier
- \`DRTRACE_DAEMON_URL\` - URL of the DrTrace daemon
- \`DRTRACE_ENABLED\` - Enable/disable DrTrace globally (true/false)
- \`DRTRACE_RETENTION_DAYS\` - How long to retain logs (days)

### Environments

Configure separate settings for:
- **development** - Local development setup
- **staging** - Pre-production testing
- **production** - Live environment
- **ci** - Continuous integration/testing

## Usage

Load configuration based on your environment:

\`\`\`javascript
import { ConfigSchema } from 'drtrace';
const config = ConfigSchema.load('./_drtrace/config.json');
\`\`\`

## Starting the DrTrace Daemon

The DrTrace daemon must be running for your application to send logs. You have two options:

### Option A: Docker Compose (Recommended)

The easiest way to start both the database and daemon:

\`\`\`bash
# From the DrTrace repository root
docker-compose up -d

# Verify it's running
curl http://localhost:8001/status
\`\`\`

### Option B: Native Python Daemon

If you have Python and PostgreSQL installed:

\`\`\`bash
# Set database URL (if using PostgreSQL)
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"

# Start the daemon
uvicorn drtrace_service.api:app --host localhost --port 8001

# In another terminal, verify it's running
python -m drtrace_service status
\`\`\`

**Note**: The daemon must be running before your application can send logs. Keep the daemon terminal open while developing.

## Further Reading

- See \`docs/\` for complete documentation
- Check \`agents/\` for agent specifications
- Full quickstart guide: https://github.com/your-repo/docs/quickstart.md
`;
    fs.writeFileSync(readmeFile, content);
    console.log(`✓ Generated: ${readmeFile}`);
  }

  /**
   * Print initialization summary
   */
  private printSummary(config: DrTraceConfig): void {
    console.log("\n" + "=".repeat(50));
    console.log("✅ Project Initialization Complete!\n");

    console.log(`📍 Configuration Location: ${this.drtraceDir}\n`);

    console.log("📋 Generated Files:");
    console.log(`   • ${this.configPath}`);
    for (const env of config.environments || []) {
      console.log(`   • ${path.join(this.drtraceDir, `config.${env}.json`)}`);
    }
    console.log(`   • ${path.join(this.drtraceDir, ".env.example")}`);
    console.log(`   • ${path.join(this.drtraceDir, "README.md")}`);

    if (config.agent?.enabled) {
      console.log(
        `   • ${path.join(this.drtraceDir, "agents", "log-analysis.md")}`
      );
      console.log(
        `   • ${path.join(this.drtraceDir, "agents", "log-it.md")}`
      );
      console.log(
        `   • ${path.join(this.drtraceDir, "agents", "log-init.md")}`
      );
      console.log(
        `   • ${path.join(this.drtraceDir, "agents", "log-help.md")}`
      );
    }

    console.log("\n📖 Next Steps:");
    console.log(`   1. Review ${this.configPath}`);
    console.log(`   2. Create .env: cp ${path.join(this.drtraceDir, ".env.example")} .env`);
    console.log(`   3. Start the daemon:`);
    console.log(`      Option A (Docker - Recommended): docker-compose up -d`);
    console.log(`      Option B (Native): uvicorn drtrace_service.api:app --host localhost --port 8001`);
    console.log(`   4. Verify daemon: python -m drtrace_service status`);
    console.log(
      `   5. Read ${path.join(this.drtraceDir, "README.md")} for more details`
    );

    console.log("\n" + "=".repeat(50) + "\n");
  }
}

/**
 * Entry point for init command
 */
export async function runInitProject(
  projectRoot?: string
): Promise<number> {
  try {
    const initializer = new ProjectInitializer(projectRoot);
    const success = await initializer.runInteractive();
    return success ? 0 : 1;
  } catch (error) {
    console.error(`\n❌ Error during initialization:`, error);
    return 1;
  }
}
