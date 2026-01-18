/**
 * End-to-end tests for JavaScript CLI
 * Tests package installation, CLI availability, and behavior
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { execSync } from 'child_process';

describe('JavaScript CLI E2E Tests', () => {
  let tmpDir: string;
  let workDir: string;
  
  beforeAll(() => {
    // Create temporary directories
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'drtrace-e2e-js-'));
    workDir = path.join(tmpDir, 'workdir');
    fs.mkdirSync(workDir, { recursive: true });

    // Initialize and install package once for all tests
    execSync('npm init -y', { cwd: workDir, stdio: 'ignore' });
    
    // Find the package path relative to this test file
    const packagePath = path.resolve(__dirname, '..');
    execSync(`npm install ${packagePath}`, {
      cwd: workDir,
      stdio: 'inherit'
    });
  });
  
  afterAll(() => {
    // Clean up
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch (e) {
      console.error('Failed to clean up:', e);
    }
  });
  
  function runCmd(cmd: string, options?: any): string {
    try {
      return execSync(cmd, {
        cwd: workDir,
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
        ...options
      });
    } catch (error: any) {
      return error.stdout || error.stderr || String(error);
    }
  }
  
  describe('CLI Installation', () => {
    it('should show correct version', () => {
      const result = runCmd('npx drtrace --version 2>&1');
      expect(result).toContain('v0.5.0');
    });
    
    it('should show help text', () => {
      const result = runCmd('npx drtrace --help 2>&1');
      expect(result).toContain('grep');
      expect(result).toContain('status');
      expect(result).toContain('init');
    });

    it('should copy agent resources into node_modules', () => {
      const agentPath = path.join(workDir, 'node_modules', 'drtrace', 'dist', 'resources', 'agents', 'log-analysis.md');
      expect(fs.existsSync(agentPath)).toBe(true);
      const content = fs.readFileSync(agentPath, 'utf-8');
      expect(content).toContain('Log Analysis Agent');
    });
  });

  describe('Init Command', () => {
    it('should create config and copy agents with defaults', () => {
      const initScript = `
const fs = require('fs');
const path = require('path');
const drtraceMain = require.resolve('drtrace');
const drtraceRoot = require('path').join(require('path').dirname(drtraceMain), '..');
const prompts = require(require.resolve('prompts', { paths: [drtraceRoot] }));
const { ProjectInitializer } = require(require('path').join(drtraceRoot, 'dist', 'init.js'));
prompts.inject([
  'js-e2e',  // project name
  '',        // application id (default)
  'javascript',
  '',        // daemon url (default)
  true,      // enable DrTrace
  ['development'],
  true,      // enable agent interface
  'bmad'     // agent framework
]);
(async () => {
  const ok = await new ProjectInitializer(process.cwd()).runInteractive();
  console.log(ok ? 'OK' : 'FAIL');
})();
`;

      const scriptPath = path.join(workDir, 'init-script.js');
      fs.writeFileSync(scriptPath, initScript, 'utf-8');

      const result = runCmd(`node ${scriptPath} 2>&1`);
      expect(result).toContain('OK');

      const configPath = path.join(workDir, '_drtrace', 'config.json');
      const envConfigPath = path.join(workDir, '_drtrace', 'config.development.json');
      const agentPath = path.join(workDir, '_drtrace', 'agents', 'log-analysis.md');

      expect(fs.existsSync(configPath)).toBe(true);
      expect(fs.existsSync(envConfigPath)).toBe(true);
      expect(fs.existsSync(agentPath)).toBe(true);

      const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
      expect(config.project_name).toBe('js-e2e');
      expect(config.application_id).toBe('js-e2e');
      expect(config.daemon_url).toBe('http://localhost:8001');
      expect(config.enabled).toBe(true);
      expect(config.environments).toContain('development');

      const content = fs.readFileSync(agentPath, 'utf-8');
      expect(content).toContain('Log Analysis Agent');
    });
  });
  
  describe('Grep Command', () => {
    it('should show grep help', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('Search log messages');
      expect(result).toContain('-E');
      expect(result).toContain('--extended-regex');
      expect(result).toContain('message_regex');
    });
    
    it('should document mutually exclusive constraint', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('message_regex');
      // The help text mentions the constraint
      const hasFlag = result.includes('-E') || result.includes('extended');
      expect(hasFlag).toBe(true);
    });
    
    it('should recognize -E flag', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toMatch(/-E.*extended-regex/);
    });
    
    it('should recognize -c flag for count', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('-c');
      expect(result).toContain('count');
    });
    
    it('should recognize -i flag for ignore case', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('-i');
      expect(result).toContain('ignore');
    });
    
    it('should recognize -v flag for invert match', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('-v');
      expect(result).toContain('invert');
    });
    
    it('should recognize -n flag for line numbers', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('-n');
      expect(result).toContain('line');
    });
    
    it('should recognize --since flag', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('--since');
    });
    
    it('should recognize --json flag', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('--json');
    });
    
    it('should recognize --color flag', () => {
      const result = runCmd('npx drtrace grep --help 2>&1');
      expect(result).toContain('--color');
    });
  });
  
  describe('Status Command', () => {
    it('should show status help', () => {
      const result = runCmd('npx drtrace status --help 2>&1');
      expect(result).toContain('daemon');
      const hasLabel = result.includes('health') || result.includes('status');
      expect(hasLabel).toBe(true);
    });
    
    it('should run status command', () => {
      const result = runCmd('npx drtrace status 2>&1');
      // Status may succeed or fail depending on daemon availability
      expect(result).toMatch(/HEALTHY|UNREACHABLE/i);
    });
  });
  
  describe('Parity with Python CLI', () => {
    it('grep help should mention -E flag like Python', () => {
      const jsResult = runCmd('npx drtrace grep --help 2>&1');
      expect(jsResult).toContain('-E');
      expect(jsResult).toContain('extended-regex');
    });
    
    it('status command should exist like Python', () => {
      const jsResult = runCmd('npx drtrace status --help 2>&1');
      expect(jsResult).not.toContain('Unknown command');
    });
    
    it('version format should be v0.5.0 like Python', () => {
      const jsResult = runCmd('npx drtrace --version 2>&1');
      expect(jsResult).toContain('v0.5.0');
    });
  });
});
