import { Transport } from './transport';
import { LogQueue } from './queue';
import { DrTraceLogger } from './logger';
import type { ClientOptions, LogLevel } from './types';

/**
 * DrTrace client for browser environments.
 *
 * Unlike the Node.js client, this does NOT load configuration from files.
 * All options must be passed explicitly to init().
 */
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
    this.logger = new DrTraceLogger({
      queue: this.queue,
      applicationId: opts.applicationId,
      moduleName: opts.moduleName,
      logLevel: (opts.logLevel ?? 'info') as LogLevel,
    });
  }

  /**
   * Initialize DrTrace for browser environments.
   * Unlike Node.js, browser does not load config from files.
   * All options must be passed explicitly.
   *
   * @param opts - Client options (applicationId and daemonUrl are required)
   * @throws Error if applicationId or daemonUrl are not provided
   */
  static init(opts: ClientOptions): DrTrace {
    if (!opts.applicationId) {
      throw new Error('applicationId is required for browser usage');
    }
    if (!opts.daemonUrl) {
      throw new Error('daemonUrl is required for browser usage');
    }
    return new DrTrace(opts);
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

export * from './types';
