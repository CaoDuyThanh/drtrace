import type { LogEvent, LogLevel } from './types';
import { LogQueue } from './queue';

export class DrTraceLogger {
  private queue: LogQueue;
  private applicationId: string;
  private moduleName: string;
  private logLevel: LogLevel;
  private originalConsole?: { log: typeof console.log; error: typeof console.error };

  constructor(opts: { queue: LogQueue; applicationId: string; moduleName?: string; logLevel: LogLevel }) {
    this.queue = opts.queue;
    this.applicationId = opts.applicationId;
    this.moduleName = opts.moduleName || 'default';
    this.logLevel = opts.logLevel || 'info';
  }

  /**
   * Serialize a value to a string suitable for logging.
   * Handles objects, arrays, errors, and primitives correctly.
   */
  private serialize(value: unknown): string {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (value instanceof Error) {
      return value.stack || `${value.name}: ${value.message}`;
    }
    try {
      return JSON.stringify(value);
    } catch {
      // Handle circular references gracefully
      return String(value);
    }
  }

  attachToConsole(): void {
    if (this.originalConsole) return;
    this.originalConsole = { log: console.log, error: console.error };

    console.log = (...args: any[]) => {
      try {
        this.log('info', args.map((arg) => this.serialize(arg)).join(' '));
      } catch {
        // Silently ignore logging errors
      }
      this.originalConsole!.log.apply(console, args);
    };

    console.error = (...args: any[]) => {
      try {
        this.log('error', args.map((arg) => this.serialize(arg)).join(' '));
      } catch {
        // Silently ignore logging errors
      }
      this.originalConsole!.error.apply(console, args);
    };
  }

  detachFromConsole(): void {
    if (!this.originalConsole) return;
    console.log = this.originalConsole.log;
    console.error = this.originalConsole.error;
    this.originalConsole = undefined;
  }

  log(level: LogLevel, message: string, context?: Record<string, unknown>): void {
    const event: LogEvent = {
      ts: Date.now() / 1000,  // Unix timestamp as float (seconds.milliseconds)
      application_id: this.applicationId,
      module_name: this.moduleName,
      level,
      message,
      context,
    };
    this.queue.push(event);
  }
}
