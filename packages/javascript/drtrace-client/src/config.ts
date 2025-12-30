/**
 * Configuration loading and management for DrTrace JavaScript client.
 *
 * Implements hierarchical config loading with the following priority:
 * 1. Environment variables (highest)
 * 2. _drtrace/config.json (per-project)
 * 3. _drtrace/config.{NODE_ENV}.json (environment-specific overrides)
 * 4. Default values (lowest)
 *
 * Usage:
 * ```typescript
 * import { ConfigLoader } from './config';
 * const config = ConfigLoader.load({ projectRoot: '.', environment: 'production' });
 * console.log(config.drtrace.applicationId);
 * ```
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * DrTrace Configuration interface
 */
export interface DrTraceConfig {
  project: {
    name: string;
    language?: string;
    description?: string;
  };
  drtrace: {
    applicationId: string;
    daemonUrl?: string;
    enabled?: boolean;
    logLevel?: 'debug' | 'info' | 'warn' | 'error';
    batchSize?: number;
    flushIntervalMs?: number;
    retentionDays?: number;
  };
  agent?: {
    enabled?: boolean;
    agentFile?: string | null;
    framework?: 'bmad' | 'langchain' | 'other' | null;
  };
  environment?: {
    [key: string]: Partial<DrTraceConfig>;
  };
}

/**
 * Schema validation and defaults for DrTrace configuration.
 */
export class ConfigSchema {
  /**
   * Default configuration values
   */
  static readonly DEFAULTS: DrTraceConfig = {
    project: {
      name: 'my-app',
      language: 'javascript',
      description: 'My application',
    },
    drtrace: {
      applicationId: 'my-app',
      daemonUrl: 'http://localhost:8001',
      enabled: true,
      logLevel: 'info',
      batchSize: 50,
      flushIntervalMs: 1000,
      retentionDays: 7,
    },
    agent: {
      enabled: false,
      agentFile: null,
      framework: null,
    },
    environment: {},
  };

  /**
   * Validate configuration against schema.
   *
   * @param config - Configuration to validate
   * @returns Validated configuration
   * @throws Error if validation fails
   */
  static validate(config: any): DrTraceConfig {
    const errors: string[] = [];

    // Check for required sections
    if (!config.project) {
      errors.push('Missing required section: project');
    } else {
      if (!config.project.name) {
        errors.push('Missing required field: project.name');
      }
      if (typeof config.project.name !== 'string' && config.project.name !== undefined) {
        errors.push(`Invalid type for project.name: expected string, got ${typeof config.project.name}`);
      }
    }

    if (!config.drtrace) {
      errors.push('Missing required section: drtrace');
    } else {
      if (!config.drtrace.applicationId) {
        errors.push('Missing required field: drtrace.applicationId');
      }
      if (typeof config.drtrace.applicationId !== 'string' && config.drtrace.applicationId !== undefined) {
        errors.push(
          `Invalid type for drtrace.applicationId: expected string, got ${typeof config.drtrace.applicationId}`
        );
      }
    }

    // Validate enums
    if (config.drtrace?.logLevel) {
      const validLevels = ['debug', 'info', 'warn', 'error'];
      if (!validLevels.includes(config.drtrace.logLevel)) {
        errors.push(
          `Invalid logLevel: ${config.drtrace.logLevel}. Must be one of: ${validLevels.join(', ')}`
        );
      }
    }

    if (config.agent?.framework) {
      const validFrameworks = ['bmad', 'langchain', 'other'];
      if (!validFrameworks.includes(config.agent.framework)) {
        errors.push(
          `Invalid agent framework: ${config.agent.framework}. Must be one of: ${validFrameworks.join(', ')}`
        );
      }
    }

    // Validate types
    if (config.drtrace?.enabled !== undefined && typeof config.drtrace.enabled !== 'boolean') {
      errors.push(`Invalid type for drtrace.enabled: expected boolean, got ${typeof config.drtrace.enabled}`);
    }

    if (config.drtrace?.batchSize !== undefined && typeof config.drtrace.batchSize !== 'number') {
      errors.push(`Invalid type for drtrace.batchSize: expected number, got ${typeof config.drtrace.batchSize}`);
    }

    if (config.drtrace?.flushIntervalMs !== undefined && typeof config.drtrace.flushIntervalMs !== 'number') {
      errors.push(
        `Invalid type for drtrace.flushIntervalMs: expected number, got ${typeof config.drtrace.flushIntervalMs}`
      );
    }

    if (config.drtrace?.retentionDays !== undefined && typeof config.drtrace.retentionDays !== 'number') {
      errors.push(`Invalid type for drtrace.retentionDays: expected number, got ${typeof config.drtrace.retentionDays}`);
    }

    if (errors.length > 0) {
      throw new Error(`Configuration validation failed:\n${errors.join('\n')}`);
    }

    return config as DrTraceConfig;
  }

  /**
   * Get default configuration
   */
  static getDefault(): DrTraceConfig {
    return JSON.parse(JSON.stringify(ConfigSchema.DEFAULTS));
  }
}

/**
 * Configuration loading and merging utility
 */
export class ConfigLoader {
  /**
   * Load configuration with hierarchical merging.
   *
   * Priority (highest to lowest):
   * 1. Environment variables (process.env with DRTRACE_* prefix)
   * 2. _drtrace/config.json
   * 3. _drtrace/config.{environment}.json
   * 4. Default values
   *
   * @param options - Loading options
   * @returns Loaded and validated configuration
   */
  static load(options: { projectRoot?: string; environment?: string } = {}): DrTraceConfig {
    const projectRoot = options.projectRoot || '.';
    const configDir = path.join(projectRoot, '_drtrace');

    // Start with defaults
    let config = ConfigSchema.getDefault();

    // Determine environment
    let environment = options.environment;
    if (!environment) {
      environment = process.env.NODE_ENV || process.env.PYTHON_ENV || undefined;
    }

    // Load base config from _drtrace/config.json
    const baseConfigPath = path.join(configDir, 'config.json');
    if (fs.existsSync(baseConfigPath)) {
      const baseConfig = ConfigLoader.loadJsonFile(baseConfigPath);
      config = ConfigLoader.mergeConfigs(config, baseConfig);
    }

    // Load environment-specific overrides
    if (environment) {
      // First, check for environment-specific subsection in base config
      if (config.environment && environment in config.environment) {
        config = ConfigLoader.mergeConfigs(config, {
          drtrace: config.environment[environment],
        } as any);
      }

      // Then, load environment-specific config file (takes precedence)
      const envConfigPath = path.join(configDir, `config.${environment}.json`);
      if (fs.existsSync(envConfigPath)) {
        const envConfig = ConfigLoader.loadJsonFile(envConfigPath);
        config = ConfigLoader.mergeConfigs(config, envConfig);
      }
    }

    // Apply environment variable overrides (highest priority)
    config = ConfigLoader.applyEnvVarOverrides(config);

    // Validate final configuration
    config = ConfigSchema.validate(config);

    return config;
  }

  /**
   * Load and parse JSON file
   */
  private static loadJsonFile(filepath: string): any {
    try {
      const content = fs.readFileSync(filepath, 'utf-8');
      return JSON.parse(content);
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        throw new Error(`Invalid JSON in ${filepath}: ${error.message}`);
      }
      throw new Error(`Error reading ${filepath}: ${error.message}`);
    }
  }

  /**
   * Deep merge override config into base config
   */
  private static mergeConfigs(base: any, overrides: any): any {
    const result = JSON.parse(JSON.stringify(base)); // Deep copy

    for (const key in overrides) {
      if (Object.prototype.hasOwnProperty.call(overrides, key)) {
        const value = overrides[key];
        if (
          result[key] &&
          typeof result[key] === 'object' &&
          !Array.isArray(result[key]) &&
          typeof value === 'object' &&
          !Array.isArray(value)
        ) {
          result[key] = ConfigLoader.mergeConfigs(result[key], value);
        } else {
          result[key] = value;
        }
      }
    }

    return result;
  }

  /**
   * Apply environment variable overrides to config.
   *
   * Environment variables use DRTRACE_* prefix with UPPER_SNAKE_CASE.
   * Examples:
  *   - DRTRACE_APPLICATION_ID -> config.drtrace.applicationId
  *   - DRTRACE_DAEMON_URL -> config.drtrace.daemonUrl
  *   - DRTRACE_ENABLED -> config.drtrace.enabled
   */
  private static applyEnvVarOverrides(config: any): any {
    const result = JSON.parse(JSON.stringify(config)); // Deep copy

    const envVarMappings: Record<string, [string, string]> = {
      DRTRACE_APPLICATION_ID: ['drtrace', 'applicationId'],
      DRTRACE_DAEMON_URL: ['drtrace', 'daemonUrl'],
      DRTRACE_ENABLED: ['drtrace', 'enabled'],
      DRTRACE_LOG_LEVEL: ['drtrace', 'logLevel'],
      DRTRACE_BATCH_SIZE: ['drtrace', 'batchSize'],
      DRTRACE_FLUSH_INTERVAL_MS: ['drtrace', 'flushIntervalMs'],
      DRTRACE_RETENTION_DAYS: ['drtrace', 'retentionDays'],
      DRTRACE_AGENT_ENABLED: ['agent', 'enabled'],
      DRTRACE_AGENT_FILE: ['agent', 'agentFile'],
      DRTRACE_AGENT_FRAMEWORK: ['agent', 'framework'],
    };

    for (const [envVar, [section, field]] of Object.entries(envVarMappings)) {
      if (process.env[envVar]) {
        let value: any = process.env[envVar];

        // Type conversions
        if (field === 'enabled') {
          value = ['true', '1', 'yes'].includes(value.toLowerCase());
        } else if (['batchSize', 'flushIntervalMs', 'retentionDays'].includes(field)) {
          const parsed = parseInt(value, 10);
          if (isNaN(parsed)) {
            throw new Error(`Invalid value for ${envVar}: must be an integer`);
          }
          value = parsed;
        }

        if (!result[section]) {
          result[section] = {};
        }
        result[section][field] = value;
      }
    }

    return result;
  }
}

/**
 * Convenience function to load configuration
 */
export function loadConfig(options?: { projectRoot?: string; environment?: string }): DrTraceConfig {
  return ConfigLoader.load(options);
}
