/**
 * Configuration schema and validation for DrTrace projects.
 * Mirrors the Python config_schema.py implementation.
 */

import * as fs from "fs";
import * as path from "path";

export interface DrTraceConfig {
  project_name: string;
  application_id: string;
  language?: "python" | "javascript" | "cpp" | "both";
  daemon_url?: string;
  enabled?: boolean;
  environments?: string[];
  agent?: {
    enabled?: boolean;
    framework?: "bmad" | "langchain" | "other";
  };
  created_at?: string;
}

export class ConfigSchema {
  private static VALID_ENVIRONMENTS = [
    "development",
    "staging",
    "production",
    "ci",
  ];

  /**
   * Get default configuration with provided values
   */
  static getDefaultConfig(options: {
    project_name: string;
    application_id: string;
    language?: "python" | "javascript" | "cpp" | "both";
    daemon_url?: string;
    enabled?: boolean;
    environments?: string[];
    agent_enabled?: boolean;
    agent_framework?: "bmad" | "langchain" | "other";
  }): DrTraceConfig {
    return {
      project_name: options.project_name,
      application_id: options.application_id,
      language: options.language || "javascript",
      daemon_url: options.daemon_url || "http://localhost:8001",
      enabled: options.enabled !== false,
      environments: options.environments || ["development"],
      agent: {
        enabled: options.agent_enabled || false,
        framework: options.agent_framework || "bmad",
      },
      created_at: new Date().toISOString(),
    };
  }

  /**
   * Validate configuration against schema
   */
  static validate(config: DrTraceConfig): boolean {
    // Required fields
    if (!config.project_name || typeof config.project_name !== "string") {
      throw new Error("Missing required field: project_name");
    }
    if (!config.application_id || typeof config.application_id !== "string") {
      throw new Error("Missing required field: application_id");
    }

    // Type validation
    if (config.enabled !== undefined && typeof config.enabled !== "boolean") {
      throw new Error("Field 'enabled' must be boolean");
    }

    // Environment validation
    if (config.environments) {
      if (!Array.isArray(config.environments)) {
        throw new Error("Field 'environments' must be an array");
      }
      for (const env of config.environments) {
        if (!this.VALID_ENVIRONMENTS.includes(env)) {
          throw new Error(`Invalid environment: ${env}`);
        }
      }
    }

    return true;
  }

  /**
   * Save configuration to file
   */
  static save(config: DrTraceConfig, filePath: string): void {
    this.validate(config);
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(filePath, JSON.stringify(config, null, 2));
  }

  /**
   * Load configuration from file
   */
  static load(filePath: string): DrTraceConfig {
    if (!fs.existsSync(filePath)) {
      throw new Error(`Config file not found: ${filePath}`);
    }
    const content = fs.readFileSync(filePath, "utf-8");
    const config = JSON.parse(content);
    this.validate(config);
    return config;
  }
}
