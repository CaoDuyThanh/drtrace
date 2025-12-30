export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogEvent {
  timestamp: string;
  applicationId: string;
  level: LogLevel;
  message: string;
  context?: Record<string, unknown>;
}

export interface ClientOptions {
  applicationId: string;
  daemonUrl: string;
  enabled?: boolean;
  logLevel?: LogLevel;
  batchSize?: number;
  flushIntervalMs?: number;
  maxRetries?: number;
  maxQueueSize?: number;
}
