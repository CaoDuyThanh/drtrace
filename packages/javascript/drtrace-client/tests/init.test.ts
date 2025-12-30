/**
 * Tests for DrTrace project initialization CLI
 */

import * as fs from 'fs';
import * as path from 'path';
import { ProjectInitializer, runInitProject } from '../src/init';
import { ConfigSchema } from '../src/config-schema';

// Mock prompts library
jest.mock('prompts', () => {
  const mockPrompts = jest.fn();
  return mockPrompts;
});

// Mock fs operations
jest.mock('fs', () => {
  const actualFs = jest.requireActual('fs');
  return {
    ...actualFs,
    mkdirSync: jest.fn(),
    writeFileSync: jest.fn(),
    existsSync: jest.fn(),
    readFileSync: jest.fn(),
    copyFileSync: jest.fn(),
  };
});

describe('ProjectInitializer', () => {
  let testProjectRoot: string;
  let initializer: ProjectInitializer;

  beforeEach(() => {
    testProjectRoot = path.join(__dirname, 'test-project');
    initializer = new ProjectInitializer(testProjectRoot);
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Clean up mocks
    jest.clearAllMocks();
  });

  describe('constructor', () => {
    it('should set project root to current directory if not provided', () => {
      const defaultInit = new ProjectInitializer();
      expect(defaultInit).toBeInstanceOf(ProjectInitializer);
    });

    it('should set custom project root', () => {
      expect(initializer).toBeInstanceOf(ProjectInitializer);
    });
  });

  describe('runInteractive', () => {
    it('should create _drtrace directory structure', async () => {
      const prompts = require('prompts');
      
      // Mock fs.existsSync to return false (no existing config)
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      
      // Mock prompts to return test values
      prompts.mockResolvedValueOnce({ value: 'test-app' }); // project name
      prompts.mockResolvedValueOnce({ value: 'test-app-id' }); // application ID
      prompts.mockResolvedValueOnce({ value: 'javascript' }); // language
      prompts.mockResolvedValueOnce({ value: 'http://localhost:8001' }); // daemon URL
      prompts.mockResolvedValueOnce({ value: true }); // enabled
      prompts.mockResolvedValueOnce({ value: ['development'] }); // environments
      prompts.mockResolvedValueOnce({ value: false }); // agent enabled

      // Mock directory creation
      (fs.mkdirSync as jest.Mock).mockImplementation(() => {});

      // Mock file writing
      (fs.writeFileSync as jest.Mock).mockImplementation(() => {});

      const result = await initializer.runInteractive();

      // Verify directory was created
      expect(fs.mkdirSync).toHaveBeenCalled();
      expect(fs.writeFileSync).toHaveBeenCalled();
    });

    it('should handle existing config file - user confirms overwrite', async () => {
      const prompts = require('prompts');
      
      // Mock existing config
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      
      // Mock prompts for handleExistingConfig (called first)
      prompts.mockResolvedValueOnce({ value: true }); // overwrite existing config? (Yes)
      prompts.mockResolvedValueOnce({ value: true }); // create backup? (Yes)
      
      // Mock all prompts for successful run (after config check)
      prompts.mockResolvedValueOnce({ value: 'test-app' }); // project name
      prompts.mockResolvedValueOnce({ value: 'test-app-id' }); // application ID
      prompts.mockResolvedValueOnce({ value: 'javascript' }); // language
      prompts.mockResolvedValueOnce({ value: 'http://localhost:8001' }); // daemon URL
      prompts.mockResolvedValueOnce({ value: true }); // enabled
      prompts.mockResolvedValueOnce({ value: ['development'] }); // environments
      prompts.mockResolvedValueOnce({ value: false }); // agent enabled

      (fs.mkdirSync as jest.Mock).mockImplementation(() => {});
      (fs.writeFileSync as jest.Mock).mockImplementation(() => {});
      (fs.copyFileSync as jest.Mock).mockImplementation(() => {}); // For backup

      const result = await initializer.runInteractive();

      // User confirmed overwrite, so initialization continues
      expect(result).toBe(true);
      expect(fs.existsSync).toHaveBeenCalled();
      expect(fs.copyFileSync).toHaveBeenCalled(); // Backup was created
    });

    it('should stop initialization when user declines overwrite', async () => {
      const prompts = require('prompts');
      
      // Mock existing config
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      
      // Mock prompt for handleExistingConfig - user declines overwrite
      prompts.mockResolvedValueOnce({ value: false }); // overwrite existing config? (No)

      const result = await initializer.runInteractive();

      // User declined, so initialization stops
      expect(result).toBe(false);
      expect(fs.existsSync).toHaveBeenCalled();
      // No directory creation or file writing should happen
      expect(fs.mkdirSync).not.toHaveBeenCalled();
      expect(fs.writeFileSync).not.toHaveBeenCalled();
    });
  });

  describe('runInitProject', () => {
    it('should return 0 on success', async () => {
      const prompts = require('prompts');
      
      // Mock fs.existsSync to return false (no existing config)
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      
      // Mock all prompts
      prompts.mockResolvedValueOnce({ value: 'test-app' });
      prompts.mockResolvedValueOnce({ value: 'test-app-id' });
      prompts.mockResolvedValueOnce({ value: 'javascript' });
      prompts.mockResolvedValueOnce({ value: 'http://localhost:8001' });
      prompts.mockResolvedValueOnce({ value: true });
      prompts.mockResolvedValueOnce({ value: ['development'] });
      prompts.mockResolvedValueOnce({ value: false });

      (fs.mkdirSync as jest.Mock).mockImplementation(() => {});
      (fs.writeFileSync as jest.Mock).mockImplementation(() => {});

      const exitCode = await runInitProject(testProjectRoot);
      expect(exitCode).toBe(0);
    });

    it('should return 1 on error', async () => {
      const prompts = require('prompts');
      
      // Mock prompts to throw error
      prompts.mockRejectedValueOnce(new Error('Test error'));

      const exitCode = await runInitProject(testProjectRoot);
      expect(exitCode).toBe(1);
    });

    it('should use current directory if project root not provided', async () => {
      const prompts = require('prompts');
      
      // Mock fs.existsSync to return false (no existing config)
      (fs.existsSync as jest.Mock).mockReturnValue(false);
      
      prompts.mockResolvedValueOnce({ value: 'test-app' });
      prompts.mockResolvedValueOnce({ value: 'test-app-id' });
      prompts.mockResolvedValueOnce({ value: 'javascript' });
      prompts.mockResolvedValueOnce({ value: 'http://localhost:8001' });
      prompts.mockResolvedValueOnce({ value: true });
      prompts.mockResolvedValueOnce({ value: ['development'] });
      prompts.mockResolvedValueOnce({ value: false });

      (fs.mkdirSync as jest.Mock).mockImplementation(() => {});
      (fs.writeFileSync as jest.Mock).mockImplementation(() => {});

      const exitCode = await runInitProject();
      expect(exitCode).toBe(0);
    });
  });
});

