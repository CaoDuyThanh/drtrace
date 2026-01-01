export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogEvent {
  ts: number;                    // Unix timestamp (seconds.milliseconds)
  level: LogLevel;
  message: string;
  application_id: string;        // snake_case to match daemon API
  module_name: string;           // Required by daemon
  context?: Record<string, unknown>;
}

export interface LogBatch {
  application_id: string;
  logs: LogEvent[];
}

export interface ClientOptions {
  applicationId: string;
  daemonUrl: string;
  moduleName?: string;           // Optional module name (defaults to 'default')
  enabled?: boolean;
  logLevel?: LogLevel;
  batchSize?: number;
  flushIntervalMs?: number;
  maxRetries?: number;
  maxQueueSize?: number;
}
