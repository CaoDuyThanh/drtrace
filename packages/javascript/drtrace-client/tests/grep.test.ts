/**
 * Unit tests for grep command
 */

import { runGrep } from '../src/cli/grep';

// Mock fetch globally
global.fetch = jest.fn();

describe('grep command', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
    
    // Mock console methods
    jest.spyOn(console, 'log').mockImplementation();
    jest.spyOn(console, 'error').mockImplementation();
  });
  
  afterEach(() => {
    jest.restoreAllMocks();
  });
  
  describe('daemon health check', () => {
    it('should check daemon health before querying', async () => {
      // Mock daemon unavailable
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Connection refused'));
      
      const exitCode = await runGrep(['error']);
      
      expect(exitCode).toBe(2);
      expect(console.error).toHaveBeenCalledWith('Error: DrTrace daemon is not running.');
    });
  });
  
  describe('flag parsing', () => {
    it('should parse -E flag and set extendedRegex', async () => {
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [] })
        });
      
      await runGrep(['-E', 'error|warning']);
      
      // Check that the second fetch call (query) used message_regex
      const queryCall = (global.fetch as jest.Mock).mock.calls[1];
      expect(queryCall[0]).toContain('message_regex=error%7Cwarning');
      expect(queryCall[0]).not.toContain('message_contains');
    });
    
    it('should use message_contains without -E flag', async () => {
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [] })
        });
      
      await runGrep(['error']);
      
      // Check that the query used message_contains
      const queryCall = (global.fetch as jest.Mock).mock.calls[1];
      expect(queryCall[0]).toContain('message_contains=error');
      expect(queryCall[0]).not.toContain('message_regex');
    });
    
    it('should parse --since flag', async () => {
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [] })
        });
      
      await runGrep(['--since', '1h', 'error']);
      
      // Check that the query used since=1h
      const queryCall = (global.fetch as jest.Mock).mock.calls[1];
      expect(queryCall[0]).toContain('since=1h');
    });
    
    it('should parse --application-id flag', async () => {
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [] })
        });
      
      await runGrep(['--application-id', 'myapp', 'error']);
      
      // Check that the query used application_id
      const queryCall = (global.fetch as jest.Mock).mock.calls[1];
      expect(queryCall[0]).toContain('application_id=myapp');
    });
  });
  
  describe('mutually exclusive constraint', () => {
    it('should never send both message_contains and message_regex', async () => {
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [] })
        });
      
      // Test with -E flag
      await runGrep(['-E', 'error']);
      const queryWithE = (global.fetch as jest.Mock).mock.calls[1][0];
      
      // Should have message_regex but not message_contains
      expect(queryWithE).toContain('message_regex');
      expect(queryWithE).not.toContain('message_contains');
      
      // Reset mocks
      (global.fetch as jest.Mock).mockClear();
      
      // Mock again for second test
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [] })
        });
      
      // Test without -E flag
      await runGrep(['error']);
      const queryWithoutE = (global.fetch as jest.Mock).mock.calls[1][0];
      
      // Should have message_contains but not message_regex
      expect(queryWithoutE).toContain('message_contains');
      expect(queryWithoutE).not.toContain('message_regex');
    });
  });
  
  describe('output formatting', () => {
    it('should format output matching Python format', async () => {
      const mockResult = {
        id: 1,
        ts: 1704067200, // 2024-01-01 00:00:00
        level: 'ERROR',
        message: 'Test error message',
        application_id: 'testapp',
        service_name: 'api-service',
        module_name: 'main',
        context: {}
      };
      
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [mockResult] })
        });
      
      await runGrep(['error']);
      
      // Check that output was logged
      expect(console.log).toHaveBeenCalled();
      const loggedOutput = (console.log as jest.Mock).mock.calls[0][0];
      
      // Should match format: [TIMESTAMP] [SERVICE] [LEVEL] MESSAGE
      expect(loggedOutput).toContain('[2024-01-01');
      expect(loggedOutput).toContain('[api-service]');
      expect(loggedOutput).toContain('[ERROR]');
      expect(loggedOutput).toContain('Test error message');
    });
    
    it('should output count with -c flag', async () => {
      const mockResults = [
        { id: 1, ts: 1704067200, level: 'ERROR', message: 'Error 1', application_id: 'testapp', context: {} },
        { id: 2, ts: 1704067201, level: 'ERROR', message: 'Error 2', application_id: 'testapp', context: {} }
      ];
      
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: mockResults })
        });
      
      await runGrep(['-c', 'error']);
      
      // Should output count
      expect(console.log).toHaveBeenCalledWith(2);
    });
    
    it('should output JSON with --json flag', async () => {
      const mockResult = {
        id: 1,
        ts: 1704067200,
        level: 'ERROR',
        message: 'Test error',
        application_id: 'testapp',
        context: {}
      };
      
      // Mock successful daemon health check and query
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ results: [mockResult] })
        });
      
      await runGrep(['--json', 'error']);
      
      // Should output JSON
      const loggedOutput = (console.log as jest.Mock).mock.calls[0][0];
      expect(() => JSON.parse(loggedOutput)).not.toThrow();
    });
  });
  
  describe('error handling', () => {
    it('should handle API errors gracefully', async () => {
      // Mock daemon healthy but query fails
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ service_name: 'drtrace_daemon', version: '0.1.0', host: 'localhost', port: 8001 })
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 400,
          json: async () => ({ detail: { message: 'Invalid pattern' } })
        });
      
      const exitCode = await runGrep(['error']);
      
      expect(exitCode).toBe(2);
      expect(console.error).toHaveBeenCalledWith(expect.stringContaining('Invalid pattern'));
    });
  });
});
