import type { LogEvent, LogBatch } from './types';

const DEFAULT_TIMEOUT_MS = 5000;
const DEFAULT_MAX_RETRIES = 3;
const BACKOFF_MS = [100, 200, 400];
const USER_AGENT = 'drtrace-client-js/0.1.0';

export class Transport {
  private daemonUrl: string;
  private timeoutMs: number;
  private maxRetries: number;

  constructor(opts: { daemonUrl: string; timeoutMs?: number; maxRetries?: number }) {
    this.daemonUrl = opts.daemonUrl.replace(/\/$/, '');
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.maxRetries = Math.max(0, opts.maxRetries ?? DEFAULT_MAX_RETRIES);
  }

  async sendBatch(events: LogEvent[]): Promise<void> {
    if (events.length === 0) return;
    const url = `${this.daemonUrl}/logs/ingest`;
    // Wrap batch with application_id at top level as required by daemon API
    const payload: LogBatch = {
      application_id: events[0].application_id,
      logs: events,
    };

    const fetchImpl: typeof fetch | undefined = (globalThis as any).fetch;
    if (!fetchImpl) return; // Non-blocking skip

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      const controller = new AbortController();
      const to = setTimeout(() => controller.abort(), this.timeoutMs);
      to.unref?.();
      try {
        const res = await fetchImpl(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT,
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });
        // Consume body to free resources
        res.body && (await res.text().catch(() => ''));
        // Treat non-2xx as retryable
        if (res.ok) return;
      } catch (_err) {
        // swallow and retry
      } finally {
        clearTimeout(to);
      }

      if (attempt < this.maxRetries) {
        const delay = BACKOFF_MS[Math.min(attempt, BACKOFF_MS.length - 1)];
        await new Promise((resolve) => {
          const to = setTimeout(resolve, delay);
          to.unref?.();
        });
      }
    }
  }
}
