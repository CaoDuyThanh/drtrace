import { loadConfig } from './config';
import { Transport } from './transport';
import { LogQueue } from './queue';
import { DrTraceLogger } from './logger';
import type { ClientOptions, LogLevel } from './types';

export class DrTrace {
  private queue: LogQueue;
  private logger: DrTraceLogger;
  private enabled: boolean;

  private constructor(opts: ClientOptions) {
    const transport = new Transport({
      daemonUrl: opts.daemonUrl,
      maxRetries: opts.maxRetries ?? 3,
      timeoutMs: 5000,
    });
    this.queue = new LogQueue({
      transport,
      batchSize: opts.batchSize ?? 50,
      flushIntervalMs: opts.flushIntervalMs ?? 1000,
      maxQueueSize: opts.maxQueueSize ?? 10000,
    });
    this.queue.start();

    this.enabled = opts.enabled ?? true;
    this.logger = new DrTraceLogger({ queue: this.queue, applicationId: opts.applicationId, logLevel: (opts.logLevel ?? 'info') as LogLevel });
  }

  static init(opts?: Partial<ClientOptions>): DrTrace {
    const cfg = loadConfig({ projectRoot: '.', environment: process.env.NODE_ENV });
    const merged: ClientOptions = {
      applicationId: cfg.drtrace.applicationId,
      daemonUrl: cfg.drtrace.daemonUrl || 'http://localhost:8001',
      enabled: cfg.drtrace.enabled ?? true,
      logLevel: (cfg.drtrace.logLevel ?? 'info') as LogLevel,
      batchSize: cfg.drtrace.batchSize ?? 50,
      flushIntervalMs: cfg.drtrace.flushIntervalMs ?? 1000,
      ...opts,
    };
    return new DrTrace(merged);
  }

  attachToConsole(): void {
    if (!this.enabled) return;
    this.logger.attachToConsole();
  }

  detachFromConsole(): void {
    this.logger.detachFromConsole();
  }

  log(message: string, level: LogLevel = 'info', context?: Record<string, unknown>): void {
    if (!this.enabled) return;
    this.logger.log(level, message, context);
  }

  error(message: string, context?: Record<string, unknown>): void {
    if (!this.enabled) return;
    this.logger.log('error', message, context);
  }

  async shutdown(): Promise<void> {
    await this.queue.flush();
    this.queue.stop();
    this.detachFromConsole();
  }
}
