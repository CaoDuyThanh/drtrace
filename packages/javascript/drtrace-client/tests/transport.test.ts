import { Transport } from '../src/transport';

jest.useFakeTimers();

// Mock fetch globally
const mockFetch = jest.fn(async () => ({ ok: true, body: { pipe: () => {} }, text: async () => '' } as any));
(global as any).fetch = mockFetch as any;

describe('Transport', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterAll(() => {
    jest.useRealTimers();
  });

  it('sends batched logs via fetch', async () => {
    const t = new Transport({ daemonUrl: 'http://daemon' });
    await t.sendBatch([
      { ts: Date.now() / 1000, application_id: 'app', module_name: 'default', level: 'info', message: 'hello' },
    ]);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const url = (mockFetch.mock.calls[0] as any)[0];
    expect(url).toBe('http://daemon/logs/ingest');
  });

  it('retries on failure with backoff', async () => {
    const seq = [
      Promise.reject(new Error('fail1')),
      Promise.resolve({ ok: false, body: null, text: async () => '' } as any),
      Promise.resolve({ ok: true, body: null, text: async () => '' } as any),
    ];
    mockFetch.mockImplementation(() => seq.shift()!);

    const t = new Transport({ daemonUrl: 'http://daemon', maxRetries: 2, timeoutMs: 1000 });
    const sendPromise = t.sendBatch([
      { ts: Date.now() / 1000, application_id: 'app', module_name: 'default', level: 'info', message: 'hello' },
    ]);

    jest.advanceTimersByTime(1000);
    await jest.runAllTimersAsync();
    await sendPromise;
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it('ignores empty batches', async () => {
    const t = new Transport({ daemonUrl: 'http://daemon' });
    await t.sendBatch([]);
    expect(mockFetch).toHaveBeenCalledTimes(0);
  });
});
