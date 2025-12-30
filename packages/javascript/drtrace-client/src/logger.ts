import type { LogEvent, LogLevel } from './types';
import { LogQueue } from './queue';

export class DrTraceLogger {
  private queue: LogQueue;
  private applicationId: string;
  private logLevel: LogLevel;
  private originalConsole?: { log: typeof console.log; error: typeof console.error };

  constructor(opts: { queue: LogQueue; applicationId: string; logLevel: LogLevel }) {
    this.queue = opts.queue;
    this.applicationId = opts.applicationId;
    this.logLevel = opts.logLevel || 'info';
  }

  attachToConsole(): void {
    if (this.originalConsole) return;
    this.originalConsole = { log: console.log, error: console.error };

    console.log = (...args: any[]) => {
      try {
        this.log('info', args.map(String).join(' '));
      } catch {
        // Silently ignore logging errors
      }
      this.originalConsole!.log.apply(console, args);
    };

    console.error = (...args: any[]) => {
      try {
        this.log('error', args.map(String).join(' '));
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
      timestamp: new Date().toISOString(),
      applicationId: this.applicationId,
      level,
      message,
      context,
    };
    this.queue.push(event);
  }
}
