/**
 * Grep command implementation for searching logs with POSIX regex.
 * Matches Python implementation in packages/python/src/drtrace_service/cli/grep.py
 */

import * as fs from 'fs';
import * as path from 'path';

interface GrepOptions {
  pattern: string;
  ignoreCase?: boolean;
  count?: boolean;
  invertMatch?: boolean;
  lineNumber?: boolean;
  extendedRegex?: boolean;
  since?: string;
  applicationId?: string;
  daemonHost?: string;
  daemonPort?: number;
  json?: boolean;
  color?: 'auto' | 'always' | 'never';
}

interface LogRecord {
  id: number;
  ts: number;
  level: string;
  message: string;
  application_id: string;
  service_name?: string;
  module_name?: string;
  file_path?: string;
  line_no?: number;
  exception_type?: string | null;
  stacktrace?: string | null;
  context: Record<string, any>;
}

/**
 * Check if daemon is available with timeout
 */
async function checkDaemonAlive(host: string, port: number, timeoutMs: number = 500): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const response = await fetch(`http://${host}:${port}/status`, {
      signal: controller.signal,
    });
    clearTimeout(timeout);
    return response.ok;
  } catch (error) {
    clearTimeout(timeout);
    return false;
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(ts: number): string {
  const date = new Date(ts * 1000);
  return date.toISOString().replace('T', ' ').substring(0, 19);
}

/**
 * Apply color to text based on log level
 */
function colorize(text: string, level: string, colorMode: 'auto' | 'always' | 'never'): string {
  const shouldColor = colorMode === 'always' || (colorMode === 'auto' && process.stdout.isTTY);
  
  if (!shouldColor) {
    return text;
  }
  
  const colors: Record<string, string> = {
    ERROR: '\x1b[31m',    // Red
    CRITICAL: '\x1b[31m', // Red
    WARNING: '\x1b[33m',  // Yellow
    WARN: '\x1b[33m',     // Yellow
    INFO: '\x1b[0m',      // Default
    DEBUG: '\x1b[90m',    // Gray
  };
  
  const reset = '\x1b[0m';
  const color = colors[level] || colors.INFO;
  
  return `${color}${text}${reset}`;
}

/**
 * Main grep implementation
 */
export async function grep(options: GrepOptions): Promise<number> {
  const {
    pattern,
    ignoreCase = false,
    count = false,
    invertMatch = false,
    lineNumber = false,
    extendedRegex = false,
    since = '5m',
    applicationId,
    daemonHost = process.env.DRTRACE_DAEMON_HOST || 'localhost',
    daemonPort = parseInt(process.env.DRTRACE_DAEMON_PORT || '8001'),
    json = false,
    color = 'auto',
  } = options;
  
  // Check if daemon is available
  const daemonAvailable = await checkDaemonAlive(daemonHost, daemonPort, 500);
  
  if (!daemonAvailable) {
    console.error('Error: DrTrace daemon is not running.');
    console.error('');
    console.error('Start the daemon with:');
    console.error('  drtrace daemon start');
    return 2;
  }
  
  // Build query parameters (Story 11-2: wire -E flag to message_regex)
  const params = new URLSearchParams({
    since: since,
  });
  
  // Use message_regex if -E flag provided, else message_contains (Epic 11.1, 11.2)
  if (extendedRegex) {
    params.append('message_regex', pattern);
  } else {
    params.append('message_contains', pattern);
  }
  
  if (applicationId) {
    params.append('application_id', applicationId);
  }
  
  // Query daemon using fetch
  try {
    const daemonUrl = `http://${daemonHost}:${daemonPort}/logs/query`;
    const response = await fetch(`${daemonUrl}?${params.toString()}`);
    
    if (!response.ok) {
      const error = await response.json() as { detail?: { message?: string } | string };
      const errorMsg = typeof error.detail === 'object' ? error.detail?.message : error.detail;
      console.error(`Error: ${errorMsg || 'Query failed'}`);
      return 2;
    }
    
    const data = await response.json() as { results?: LogRecord[] };
    const results: LogRecord[] = data.results || [];
    
    // Apply additional filters that weren't sent to API (invert_match)
    let filteredResults = results;
    
    if (invertMatch) {
      if (extendedRegex) {
        const flags = ignoreCase ? 'i' : '';
        const regex = new RegExp(pattern, flags);
        filteredResults = results.filter(record => !regex.test(record.message));
      } else {
        const searchPattern = ignoreCase ? pattern.toLowerCase() : pattern;
        filteredResults = results.filter(record => {
          const message = ignoreCase ? record.message.toLowerCase() : record.message;
          return !message.includes(searchPattern);
        });
      }
    }
    
    // Output results
    if (count) {
      console.log(filteredResults.length);
      return 0;
    }
    
    if (json) {
      console.log(JSON.stringify(filteredResults, null, 2));
      return 0;
    }
    
    if (filteredResults.length === 0) {
      return 1;
    }
    
    // Format and print results
    for (const record of filteredResults) {
      const tsStr = formatTimestamp(record.ts);
      const serviceStr = record.service_name ? `[${record.service_name}]` : '';
      let msg = `[${tsStr}] ${serviceStr} [${record.level}] ${record.message}`;
      
      msg = colorize(msg, record.level, color);
      
      if (lineNumber) {
        // Use timestamp as pseudo line number for daemon results
        msg = `${Math.floor(record.ts)}:${msg}`;
      }
      
      console.log(msg);
    }
    
    return 0;
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`Error: Failed to query daemon: ${errorMessage}`);
    return 2;
  }
}

/**
 * Parse CLI arguments and run grep command
 */
export async function runGrep(args: string[]): Promise<number> {
  // Simple argument parser matching Python argparse behavior
  const options: GrepOptions = {
    pattern: '',
    ignoreCase: false,
    count: false,
    invertMatch: false,
    lineNumber: false,
    extendedRegex: false,
    since: '5m',
    color: 'auto',
  };
  
  let i = 0;
  while (i < args.length) {
    const arg = args[i];
    
    if (arg === '-i' || arg === '--ignore-case') {
      options.ignoreCase = true;
    } else if (arg === '-c' || arg === '--count') {
      options.count = true;
    } else if (arg === '-v' || arg === '--invert-match') {
      options.invertMatch = true;
    } else if (arg === '-n' || arg === '--line-number') {
      options.lineNumber = true;
    } else if (arg === '-E' || arg === '--extended-regex') {
      options.extendedRegex = true;
    } else if (arg === '--since') {
      options.since = args[++i];
    } else if (arg === '--application-id') {
      options.applicationId = args[++i];
    } else if (arg === '--daemon-host') {
      options.daemonHost = args[++i];
    } else if (arg === '--daemon-port') {
      options.daemonPort = parseInt(args[++i]);
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--color') {
      const colorValue = args[++i];
      if (colorValue !== 'auto' && colorValue !== 'always' && colorValue !== 'never') {
        console.error(`Error: Invalid color value '${colorValue}'. Use: auto, always, never`);
        return 2;
      }
      options.color = colorValue;
    } else if (arg === '-h' || arg === '--help') {
      printHelp();
      return 0;
    } else if (!arg.startsWith('-')) {
      // Positional argument - pattern
      options.pattern = arg;
    } else {
      console.error(`Error: Unknown option '${arg}'`);
      return 2;
    }
    
    i++;
  }
  
  if (!options.pattern) {
    console.error('Error: Pattern is required');
    printHelp();
    return 2;
  }
  
  return grep(options);
}

function printHelp(): void {
  console.log(`Usage: drtrace grep [OPTIONS] PATTERN

Search log messages with pattern matching.

Options:
  -i, --ignore-case       Ignore case in pattern matching
  -c, --count             Output count of matches instead of matches
  -v, --invert-match      Invert match (show non-matching lines)
  -n, --line-number       Output line numbers with matches
  -E, --extended-regex    Use POSIX extended regex (sends message_regex to API)
  --since <time>          Time range: 30m/1h/2d/7d (default: 5m)
  --application-id <id>   Filter by application ID
  --daemon-host <host>    Daemon host (default: localhost)
  --daemon-port <port>    Daemon port (default: 8001)
  --json                  Output in JSON format
  --color <mode>          Color control: auto, always, never (default: auto)
  -h, --help              Show this help message

Examples:
  # Simple substring search
  drtrace grep "timeout"

  # Regex search with -E flag
  drtrace grep -E "error|warning"

  # Search with application filter
  drtrace grep --application-id myapp "error"

  # Count matches
  drtrace grep -c "error"
`);
}
