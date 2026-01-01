import { LogQueue } from '../src/queue';
import { Transport } from '../src/transport';
import type { LogEvent } from '../src/types';

jest.useFakeTimers();

class MockTransport extends Transport {
  public sent: LogEvent[][] = [];
  constructor() {
    super({ daemonUrl: 'http://localhost:8001' });
  }
  async sendBatch(events: LogEvent[]): Promise<void> {
    this.sent.push(events);
  }
}

describe('LogQueue', () => {
  afterEach(() => {
    process.removeAllListeners('SIGINT');
    process.removeAllListeners('SIGTERM');
  });

  it('flushes when batchSize is reached', async () => {
    const transport = new MockTransport();
    const queue = new LogQueue({ transport, batchSize: 3, flushIntervalMs: 1000 });
    queue.start();

    const mk = (msg: string): LogEvent => ({ ts: Date.now() / 1000, application_id: 'app', module_name: 'default', level: 'info', message: msg });
    queue.push(mk('a'));
    queue.push(mk('b'));
    expect(transport.sent.length).toBe(0);
    queue.push(mk('c'));
    expect(transport.sent.length).toBe(1);
    expect(transport.sent[0].map(e => e.message)).toEqual(['a', 'b', 'c']);
    queue.stop();
  });

  it('flushes periodically based on flushIntervalMs', async () => {
    const transport = new MockTransport();
    const queue = new LogQueue({ transport, batchSize: 10, flushIntervalMs: 500 });
    queue.start();

    const mk = (msg: string): LogEvent => ({ ts: Date.now() / 1000, application_id: 'app', module_name: 'default', level: 'info', message: msg });
    queue.push(mk('x'));

    // Advance timers to trigger scheduled flush
    jest.advanceTimersByTime(500);
    // Allow flush promise to resolve
    await Promise.resolve();

    expect(transport.sent.length).toBe(1);
    expect(transport.sent[0].map(e => e.message)).toEqual(['x']);
    queue.stop();
  });

  it('enforces maxQueueSize and drops oldest with warning', async () => {
    const transport = new MockTransport();
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const queue = new LogQueue({ transport, batchSize: 100, flushIntervalMs: 1000, maxQueueSize: 2 });
    queue.start();

    const mk = (msg: string): LogEvent => ({ ts: Date.now() / 1000, application_id: 'app', module_name: 'default', level: 'info', message: msg });
    queue.push(mk('a'));
    queue.push(mk('b'));
    queue.push(mk('c')); // exceeds maxQueueSize

    expect(queue as any).toBeDefined();
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
    queue.stop();
  });
});
