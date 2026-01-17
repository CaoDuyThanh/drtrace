#!/usr/bin/env node

/**
 * CLI entry point for drtrace commands
 * This wrapper is copied to dist/bin/cli.js and imports from compiled TypeScript
 */

const path = require('path');

// Resolve paths relative to the dist directory
// When copied to dist/bin/cli.js, we need to go up one level to access dist/cli/*
const { runGrep } = require(path.join(__dirname, '..', 'cli', 'grep'));
const { runStatus } = require(path.join(__dirname, '..', 'cli', 'status'));
const { runInitProject } = require(path.join(__dirname, '..', 'init'));

const COMMANDS = ['grep', 'status', 'init'];

function printMainHelp() {
  console.log(`Usage: drtrace <command> [options]

Commands:
  grep      Search log messages with pattern matching
  status    Check daemon health and configuration
  init      Initialize DrTrace project configuration

Options:
  -h, --help     Show this help message
  -v, --version  Show version number

Examples:
  drtrace status
  drtrace grep "error"
  drtrace grep -E "error|warning" --since 30m
  drtrace init

For command-specific help:
  drtrace <command> --help
`);
}

function printVersion() {
  const packageJson = require(path.join(__dirname, '..', '..', 'package.json'));
  console.log(`drtrace v${packageJson.version}`);
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    printMainHelp();
    return 0;
  }
  
  const firstArg = args[0];
  
  // Handle global flags
  if (firstArg === '-h' || firstArg === '--help') {
    printMainHelp();
    return 0;
  }
  
  if (firstArg === '-v' || firstArg === '--version') {
    printVersion();
    return 0;
  }
  
  // Route to command
  const command = firstArg;
  const commandArgs = args.slice(1);
  
  switch (command) {
    case 'grep':
      return await runGrep(commandArgs);
    
    case 'status':
      return await runStatus(commandArgs);
    
    case 'init':
      const projectRoot = commandArgs.find((arg, i) => 
        (args[i - 1] === '--project-root' || args[i - 1] === '-p')
      );
      return await runInitProject(projectRoot);
    
    default:
      console.error(`Error: Unknown command '${command}'`);
      console.error('');
      printMainHelp();
      return 2;
  }
}

// Run CLI
main().then((exitCode) => {
  process.exit(exitCode);
}).catch((error) => {
  console.error(`Fatal error: ${error.message}`);
  process.exit(1);
});
