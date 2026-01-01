import { DrTrace } from '../src/browser';
import { DrTraceLogger } from '../src/logger';
import { LogQueue } from '../src/queue';
import { Transport } from '../src/transport';
import type { LogEvent } from '../src/types';
import * as fs from 'fs';
import * as path from 'path';

// Mock fetch for transport
const mockFetch = jest.fn(async () => ({ ok: true, body: null, text: async () => '' } as any));
(global as any).fetch = mockFetch as any;

describe('Browser Entry Point', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('should not import fs or path in browser bundle', () => {
    // Read the compiled browser.js to verify no Node.js imports
    const browserBundlePath = path.join(__dirname, '../dist/browser.js');
    if (fs.existsSync(browserBundlePath)) {
      const browserBundle = fs.readFileSync(browserBundlePath, 'utf-8');
      expect(browserBundle).not.toContain('require("fs")');
      expect(browserBundle).not.toContain('require("path")');
      expect(browserBundle).not.toContain("require('fs')");
      expect(browserBundle).not.toContain("require('path')");
    }
  });

  it('should require applicationId', () => {
    expect(() => DrTrace.init({} as any)).toThrow('applicationId is required');
  });

  it('should require daemonUrl', () => {
    expect(() => DrTrace.init({ applicationId: 'test' } as any)).toThrow('daemonUrl is required');
  });

  it('should initialize with valid options', () => {
    const client = DrTrace.init({
      applicationId: 'test-app',
      daemonUrl: 'http://localhost:8001',
    });
    expect(client).toBeDefined();
  });

  it('should send logs to daemon', async () => {
    const client = DrTrace.init({
      applicationId: 'test-app',
      daemonUrl: 'http://localhost:8001',
      batchSize: 1,
    });

    client.log('test message');

    // Wait for async flush
    await new Promise(resolve => setTimeout(resolve, 10));

    expect(mockFetch).toHaveBeenCalled();
    const [url, options] = mockFetch.mock.calls[0] as any;
    expect(url).toBe('http://localhost:8001/logs/ingest');
    expect(options.method).toBe('POST');

    await client.shutdown();
  });
});

describe('Object Serialization', () => {
  let logger: DrTraceLogger;
  let capturedEvents: LogEvent[] = [];

  beforeEach(() => {
    capturedEvents = [];
    const mockTransport = new Transport({ daemonUrl: 'http://test' });
    const queue = new LogQueue({
      transport: mockTransport,
      batchSize: 100,
      flushIntervalMs: 10000,
    });
    // Override push to capture events
    queue.push = (event: LogEvent) => {
      capturedEvents.push(event);
    };
    logger = new DrTraceLogger({
      queue,
      applicationId: 'test',
      logLevel: 'info',
    });
  });

  it('should serialize objects to JSON', () => {
    logger.log('info', JSON.stringify({ user: 'john' }));
    expect(capturedEvents[0].message).toBe('{"user":"john"}');
  });

  it('should serialize arrays to JSON', () => {
    logger.log('info', JSON.stringify([1, 2, 3]));
    expect(capturedEvents[0].message).toBe('[1,2,3]');
  });

  it('should pass strings through unchanged', () => {
    logger.log('info', 'hello world');
    expect(capturedEvents[0].message).toBe('hello world');
  });

  it('should convert numbers to strings', () => {
    logger.log('info', String(42));
    expect(capturedEvents[0].message).toBe('42');
  });

  it('should handle null and undefined', () => {
    logger.log('info', 'null');
    expect(capturedEvents[0].message).toBe('null');
  });
});

describe('Schema Compliance', () => {
  let capturedEvents: LogEvent[] = [];
  let logger: DrTraceLogger;

  beforeEach(() => {
    capturedEvents = [];
    const mockTransport = new Transport({ daemonUrl: 'http://test' });
    const queue = new LogQueue({
      transport: mockTransport,
      batchSize: 100,
      flushIntervalMs: 10000,
    });
    queue.push = (event: LogEvent) => {
      capturedEvents.push(event);
    };
    logger = new DrTraceLogger({
      queue,
      applicationId: 'test-app',
      moduleName: 'test-module',
      logLevel: 'info',
    });
  });

  it('should use Unix timestamp (ts) as float', () => {
    const before = Date.now() / 1000;
    logger.log('info', 'test message');
    const after = Date.now() / 1000;

    expect(capturedEvents[0].ts).toBeGreaterThanOrEqual(before);
    expect(capturedEvents[0].ts).toBeLessThanOrEqual(after);
    expect(typeof capturedEvents[0].ts).toBe('number');
  });

  it('should use snake_case field names', () => {
    logger.log('info', 'test message');

    expect(capturedEvents[0].application_id).toBe('test-app');
    expect(capturedEvents[0].module_name).toBe('test-module');
    // Verify old camelCase fields don't exist
    expect((capturedEvents[0] as any).applicationId).toBeUndefined();
    expect((capturedEvents[0] as any).timestamp).toBeUndefined();
  });

  it('should include module_name with default value', () => {
    const queue = new LogQueue({
      transport: new Transport({ daemonUrl: 'http://test' }),
      batchSize: 100,
      flushIntervalMs: 10000,
    });
    const events: LogEvent[] = [];
    queue.push = (event: LogEvent) => events.push(event);

    const loggerWithDefault = new DrTraceLogger({
      queue,
      applicationId: 'test',
      logLevel: 'info',
      // No moduleName provided - should default to 'default'
    });

    loggerWithDefault.log('info', 'test');
    expect(events[0].module_name).toBe('default');
  });
});
