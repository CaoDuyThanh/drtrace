/**
 * Status command implementation - check daemon health
 */

/**
 * Check daemon status and display information
 */
export async function status(
  daemonHost: string = process.env.DRTRACE_DAEMON_HOST || 'localhost',
  daemonPort: number = parseInt(process.env.DRTRACE_DAEMON_PORT || '8001')
): Promise<number> {
  try {
    const response = await fetch(`http://${daemonHost}:${daemonPort}/status`, {
      signal: AbortSignal.timeout(5000),
    });
    
    if (!response.ok) {
      console.error(`DrTrace daemon status: UNHEALTHY (HTTP ${response.status})`);
      console.error(`URL: http://${daemonHost}:${daemonPort}/status`);
      return 2;
    }
    
    const data = await response.json() as {
      service_name: string;
      version: string;
      host: string;
      port: number;
      retention_days?: number;
    };
    
    console.log('DrTrace daemon status: HEALTHY');
    console.log(`Service: ${data.service_name} v${data.version}`);
    console.log(`Listening on: ${data.host}:${data.port}`);
    
    if (data.retention_days) {
      console.log(`Retention: ${data.retention_days} days`);
    }
    
    return 0;
  } catch (error) {
    console.error(`DrTrace daemon status: UNREACHABLE`);
    console.error(`URL: http://${daemonHost}:${daemonPort}/status`);
    console.error('');
    console.error('Make sure the daemon is running:');
    console.error('  python -m drtrace_service daemon start');
    return 2;
  }
}

/**
 * Parse CLI arguments and run status command
 */
export async function runStatus(args: string[]): Promise<number> {
  let daemonHost = process.env.DRTRACE_DAEMON_HOST || 'localhost';
  let daemonPort = parseInt(process.env.DRTRACE_DAEMON_PORT || '8001');
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--daemon-host') {
      daemonHost = args[++i];
    } else if (arg === '--daemon-port') {
      daemonPort = parseInt(args[++i]);
    } else if (arg === '-h' || arg === '--help') {
      printHelp();
      return 0;
    } else {
      console.error(`Error: Unknown option '${arg}'`);
      return 2;
    }
  }
  
  return status(daemonHost, daemonPort);
}

function printHelp(): void {
  console.log(`Usage: drtrace status [OPTIONS]

Check daemon health and configuration.

Options:
  --daemon-host <host>    Daemon host (default: localhost)
  --daemon-port <port>    Daemon port (default: 8001)
  -h, --help              Show this help message

Environment Variables:
  DRTRACE_DAEMON_HOST     Daemon host (default: localhost)
  DRTRACE_DAEMON_PORT     Daemon port (default: 8001)
`);
}
