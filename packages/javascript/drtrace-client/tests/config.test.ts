/**
 * Tests for DrTrace configuration loader (JavaScript/TypeScript)
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { ConfigLoader, ConfigSchema, loadConfig } from '../src/config';

describe('ConfigSchema', () => {
  describe('getDefault', () => {
    it('should return valid default configuration', () => {
      const defaults = ConfigSchema.getDefault();
      expect(defaults.project.name).toBe('my-app');
      expect(defaults.drtrace.applicationId).toBe('my-app');
      expect(defaults.drtrace.enabled).toBe(true);
    });

    it('should return a deep copy', () => {
      const defaults1 = ConfigSchema.getDefault();
      const defaults2 = ConfigSchema.getDefault();
      defaults1.project.name = 'modified';
      expect(defaults2.project.name).toBe('my-app');
    });
  });

  describe('validate', () => {
    it('should accept valid default config', () => {
      const config = ConfigSchema.getDefault();
      const validated = ConfigSchema.validate(config);
      expect(validated.project.name).toBe('my-app');
    });

    it('should reject missing project section', () => {
      const config = ConfigSchema.getDefault();
      delete (config as any).project;
      expect(() => ConfigSchema.validate(config)).toThrow('Missing required section: project');
    });

    it('should reject missing project name', () => {
      const config = ConfigSchema.getDefault();
      config.project.name = '' as any;
      expect(() => ConfigSchema.validate(config)).toThrow('Missing required field: project.name');
    });

    it('should reject invalid log level', () => {
      const config = ConfigSchema.getDefault();
      config.drtrace.logLevel = 'invalid' as any;
      expect(() => ConfigSchema.validate(config)).toThrow('Invalid logLevel');
    });

    it('should accept valid log levels', () => {
      for (const level of ['debug', 'info', 'warn', 'error']) {
        const config = ConfigSchema.getDefault();
        config.drtrace.logLevel = level as any;
        expect(() => ConfigSchema.validate(config)).not.toThrow();
      }
    });

    it('should reject invalid agent framework', () => {
      const config = ConfigSchema.getDefault();
      config.agent!.framework = 'invalid-framework' as any;
      expect(() => ConfigSchema.validate(config)).toThrow('Invalid agent framework');
    });

    it('should accept valid agent frameworks', () => {
      for (const framework of ['bmad', 'langchain', 'other']) {
        const config = ConfigSchema.getDefault();
        config.agent!.framework = framework as any;
        expect(() => ConfigSchema.validate(config)).not.toThrow();
      }
    });

    it('should reject invalid boolean for enabled', () => {
      const config = ConfigSchema.getDefault();
      config.drtrace.enabled = 'true' as any;
      expect(() => ConfigSchema.validate(config)).toThrow('Invalid type for drtrace.enabled');
    });

    it('should reject invalid type for batchSize', () => {
      const config = ConfigSchema.getDefault();
      config.drtrace.batchSize = 'fifty' as any;
      expect(() => ConfigSchema.validate(config)).toThrow('Invalid type for drtrace.batchSize');
    });
  });
});

describe('ConfigLoader', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'drtrace-config-test-'));
    // Clean up any existing env vars
    delete process.env.NODE_ENV;
    delete process.env.PYTHON_ENV;
    delete process.env.DRTRACE_APPLICATION_ID;
    delete process.env.DRTRACE_DAEMON_URL;
    delete process.env.DRTRACE_ENABLED;
    delete process.env.DRTRACE_LOG_LEVEL;
    delete process.env.DRTRACE_BATCH_SIZE;
  });

  afterEach(() => {
    // Clean up temp directory
    if (fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
    // Clean up env vars
    delete process.env.NODE_ENV;
    delete process.env.PYTHON_ENV;
    delete process.env.DRTRACE_APPLICATION_ID;
    delete process.env.DRTRACE_DAEMON_URL;
    delete process.env.DRTRACE_ENABLED;
    delete process.env.DRTRACE_LOG_LEVEL;
    delete process.env.DRTRACE_BATCH_SIZE;
  });

  describe('load', () => {
    it('should load defaults when no config files exist', () => {
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.project.name).toBe('my-app');
      expect(config.drtrace.applicationId).toBe('my-app');
      expect(config.drtrace.daemonUrl).toBe('http://localhost:8001');
    });

    it('should load from _drtrace/config.json', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-custom-app' },
        drtrace: { applicationId: 'custom-app' },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.project.name).toBe('my-custom-app');
      expect(config.drtrace.applicationId).toBe('custom-app');
    });

    it('should load environment-specific override', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const baseConfig = {
        project: { name: 'my-app' },
        drtrace: {
          applicationId: 'my-app',
          daemonUrl: 'http://localhost:8001',
          enabled: true,
        },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(baseConfig));

      const prodConfig = {
        drtrace: { daemonUrl: 'https://production.example.com' },
      };
      fs.writeFileSync(path.join(configDir, 'config.production.json'), JSON.stringify(prodConfig));

      const config = ConfigLoader.load({ projectRoot: tmpDir, environment: 'production' });
      expect(config.drtrace.daemonUrl).toBe('https://production.example.com');
      expect(config.drtrace.applicationId).toBe('my-app'); // From base
    });

    it('should load environment subsection from base config', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: {
          applicationId: 'my-app',
          daemonUrl: 'http://localhost:8001',
          enabled: true,
        },
        environment: {
          production: {
            daemonUrl: 'https://production.example.com',
            enabled: false,
          },
        },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      const config = ConfigLoader.load({ projectRoot: tmpDir, environment: 'production' });
      expect(config.drtrace.daemonUrl).toBe('https://production.example.com');
      expect(config.drtrace.enabled).toBe(false);
    });

    it('should detect environment from NODE_ENV', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const baseConfig = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app' },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(baseConfig));

      const prodConfig = { drtrace: { enabled: false } };
      fs.writeFileSync(path.join(configDir, 'config.production.json'), JSON.stringify(prodConfig));

      process.env.NODE_ENV = 'production';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.enabled).toBe(false);
    });

    it('should detect environment from PYTHON_ENV', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const baseConfig = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app' },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(baseConfig));

      const devConfig = { drtrace: { logLevel: 'debug' } };
      fs.writeFileSync(path.join(configDir, 'config.development.json'), JSON.stringify(devConfig));

      process.env.PYTHON_ENV = 'development';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.logLevel).toBe('debug');
    });

    it('should throw on invalid JSON', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);
      fs.writeFileSync(path.join(configDir, 'config.json'), '{ invalid json }');

      expect(() => ConfigLoader.load({ projectRoot: tmpDir })).toThrow('Invalid JSON');
    });
  });

  describe('environment variable overrides', () => {
    it('should override applicationId from DRTRACE_APPLICATION_ID', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'from-file' },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_APPLICATION_ID = 'from-env';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.applicationId).toBe('from-env');
    });

    it('should override daemonUrl from DRTRACE_DAEMON_URL', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: {
          applicationId: 'my-app',
          daemonUrl: 'http://localhost:8001',
        },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_DAEMON_URL = 'http://custom:9000';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.daemonUrl).toBe('http://custom:9000');
    });

    it('should override enabled from DRTRACE_ENABLED=true', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app', enabled: false },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_ENABLED = 'true';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.enabled).toBe(true);
    });

    it('should override enabled from DRTRACE_ENABLED=false', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app', enabled: true },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_ENABLED = 'false';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.enabled).toBe(false);
    });

    it('should handle DRTRACE_ENABLED=1 as true', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app', enabled: false },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_ENABLED = '1';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.enabled).toBe(true);
    });

    it('should override batchSize from DRTRACE_BATCH_SIZE', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app', batchSize: 50 },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_BATCH_SIZE = '100';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.drtrace.batchSize).toBe(100);
    });

    it('should throw on invalid DRTRACE_BATCH_SIZE', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app' },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_BATCH_SIZE = 'not-a-number';
      expect(() => ConfigLoader.load({ projectRoot: tmpDir })).toThrow('must be an integer');
    });

    it('should override agent framework from DRTRACE_AGENT_FRAMEWORK', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'my-app' },
        agent: { framework: null },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      process.env.DRTRACE_AGENT_FRAMEWORK = 'langchain';
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.agent?.framework).toBe('langchain');
    });

    it('should apply environment variables with highest priority', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const baseConfig = {
        project: { name: 'my-app' },
        drtrace: {
          applicationId: 'from-file',
          daemonUrl: 'http://file-daemon:8001',
        },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(baseConfig));

      const prodConfig = { drtrace: { applicationId: 'from-prod-file' } };
      fs.writeFileSync(path.join(configDir, 'config.production.json'), JSON.stringify(prodConfig));

      process.env.DRTRACE_APPLICATION_ID = 'from-env';
      process.env.DRTRACE_DAEMON_URL = 'http://env-daemon:9000';

      const config = ConfigLoader.load({ projectRoot: tmpDir, environment: 'production' });
      expect(config.drtrace.applicationId).toBe('from-env');
      expect(config.drtrace.daemonUrl).toBe('http://env-daemon:9000');
    });
  });

  describe('convenience function', () => {
    it('should work with loadConfig function', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = {
        project: { name: 'my-app' },
        drtrace: { applicationId: 'test-app' },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      const config = loadConfig({ projectRoot: tmpDir });
      expect(config.project.name).toBe('my-app');
      expect(config.drtrace.applicationId).toBe('test-app');
    });
  });

  describe('loading priority', () => {
    it('should respect complete loading priority', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const baseConfig = {
        project: { name: 'from-base' },
        drtrace: {
          applicationId: 'from-base',
          daemonUrl: 'http://localhost:8001',
          logLevel: 'info' as const,
        },
      };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(baseConfig));

      const prodConfig = { drtrace: { logLevel: 'debug' as const } };
      fs.writeFileSync(path.join(configDir, 'config.production.json'), JSON.stringify(prodConfig));

      process.env.DRTRACE_DAEMON_URL = 'http://env-daemon:9000';

      const config = ConfigLoader.load({ projectRoot: tmpDir, environment: 'production' });

      // From env var (highest)
      expect(config.drtrace.daemonUrl).toBe('http://env-daemon:9000');

      // From env-specific override
      expect(config.drtrace.logLevel).toBe('debug');

      // From base config
      expect(config.drtrace.applicationId).toBe('from-base');

      // From defaults (for fields not specified anywhere)
      expect(config.drtrace.batchSize).toBe(50);
    });
  });

  describe('missing config files', () => {
    it('should use defaults when config files are missing', () => {
      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.project.name).toBe('my-app');
      expect(config.drtrace.enabled).toBe(true);
    });

    it('should use defaults for missing drtrace section', () => {
      const configDir = path.join(tmpDir, '_drtrace');
      fs.mkdirSync(configDir);

      const configData = { project: { name: 'my-app' } };
      fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify(configData));

      const config = ConfigLoader.load({ projectRoot: tmpDir });
      expect(config.project.name).toBe('my-app');
      expect(config.drtrace.applicationId).toBe('my-app'); // From defaults
    });
  });
});
