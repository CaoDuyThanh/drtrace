import type { LogEvent } from './types';
import { Transport } from './transport';

export class LogQueue {
  private buffer: LogEvent[] = [];
  private transport: Transport;
  private batchSize: number;
  private flushIntervalMs: number;
  private timer: NodeJS.Timeout | null = null;
  private running = false;
  private maxQueueSize: number;
  private exitHandlerBound = false;
  private exitHandler?: () => Promise<void>;

  constructor(opts: { transport: Transport; batchSize: number; flushIntervalMs: number; maxQueueSize?: number }) {
    this.transport = opts.transport;
    this.batchSize = Math.max(1, opts.batchSize);
    this.flushIntervalMs = Math.max(100, opts.flushIntervalMs);
    this.maxQueueSize = Math.max(1, opts.maxQueueSize ?? 10000);
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    this.scheduleFlush();
    this.registerExitHandlers();
  }

  stop(): void {
    this.running = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.unregisterExitHandlers();
  }

  push(event: LogEvent): void {
    this.buffer.push(event);
    if (this.buffer.length > this.maxQueueSize) {
      // Drop oldest to enforce limit
      const dropCount = this.buffer.length - this.maxQueueSize;
      this.buffer.splice(0, dropCount);
      console.warn?.(`DrTrace: maxQueueSize exceeded, dropped ${dropCount} log(s)`);
    }
    if (this.buffer.length >= this.batchSize) {
      this.flush();
    }
  }

  async flush(): Promise<void> {
    if (this.buffer.length === 0) {
      this.scheduleFlush();
      return;
    }
    const toSend = this.buffer.splice(0, this.buffer.length);
    try {
      await this.transport.sendBatch(toSend);
    } finally {
      this.scheduleFlush();
    }
  }

  private scheduleFlush(): void {
    if (!this.running) return;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.timer = setTimeout(() => {
      this.flush();
    }, this.flushIntervalMs);
    this.timer.unref?.();
  }

  private registerExitHandlers(): void {
    if (this.exitHandlerBound) return;
    const handler = async () => {
      try {
        const flushPromise = this.flush();
        const timeout = new Promise((resolve) => {
          const to = setTimeout(resolve, 2000);
          (to as any).unref?.();
        });
        await Promise.race([flushPromise, timeout]);
      } catch {
        // ignore
      }
    };
    this.exitHandler = handler;
    process.on('SIGINT', handler);
    process.on('SIGTERM', handler);
    this.exitHandlerBound = true;
  }

  private unregisterExitHandlers(): void {
    if (!this.exitHandlerBound) return;
    if (this.exitHandler) {
      process.removeListener('SIGINT', this.exitHandler);
      process.removeListener('SIGTERM', this.exitHandler);
      this.exitHandler = undefined;
    }
    this.exitHandlerBound = false;
  }
}
