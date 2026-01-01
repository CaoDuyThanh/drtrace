import { DrTrace } from '../src/node';
import { loadConfig } from '../src/config';

jest.mock('../src/config', () => {
  return {
    loadConfig: jest.fn(() => ({
      project: { name: 'my-app' },
      drtrace: {
        applicationId: 'app',
        daemonUrl: 'http://localhost:8001',
        enabled: true,
        logLevel: 'info',
        batchSize: 2,
        flushIntervalMs: 1000,
      },
    })),
  };
});

// Mock fetch for transport
const mockFetch = jest.fn(async () => ({ body: { pipe: () => {} }, text: async () => '' } as any));
(global as any).fetch = mockFetch as any;

describe('DrTrace client', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    (loadConfig as jest.Mock).mockClear();
  });

  it('initializes from loadConfig and attaches console', async () => {
    const client = DrTrace.init();
    client.attachToConsole();

    console.log('hello');
    console.error('oops');

    // Because batchSize=2, the two logs will trigger flush
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const url = (mockFetch.mock.calls[0] as any)[0];
    expect(url).toBe('http://localhost:8001/logs/ingest');

    await client.shutdown();
  });

  it('respects enabled=false', async () => {
    (loadConfig as jest.Mock).mockReturnValueOnce({
      project: { name: 'my-app' },
      drtrace: {
        applicationId: 'app',
        daemonUrl: 'http://localhost:8001',
        enabled: false,
        logLevel: 'info',
        batchSize: 2,
        flushIntervalMs: 1000,
      },
    });

    const client = DrTrace.init();
    client.attachToConsole();

    console.log('hello');
    expect(mockFetch).toHaveBeenCalledTimes(0);

    await client.shutdown();
  });
});
