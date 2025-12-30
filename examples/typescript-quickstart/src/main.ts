import { setup_logging, ClientConfig } from 'drtrace';

// Configure DrTrace client
const config = new ClientConfig({
  application_id: 'typescript-quickstart',
  daemon_host: 'localhost',
  daemon_port: 8000,
  log_level: 'DEBUG',
});

// Initialize logging - intercepts console.log/error
const client = setup_logging(config);

// Helper function to simulate work
async function processRequest(id: number): Promise<string> {
  console.log(`[Request ${id}] Starting...`);

  // Simulate async work
  await new Promise((resolve) => setTimeout(resolve, 100));

  console.log(`[Request ${id}] Processing complete`);
  return `Result for request ${id}`;
}

// Main application
async function main(): Promise<void> {
  console.log('=== DrTrace TypeScript Quickstart ===');
  console.log('✓ Application started');

  try {
    // Process multiple requests
    console.log('');
    console.log('Processing requests...');

    for (let i = 1; i <= 3; i++) {
      const result = await processRequest(i);
      console.log(`[Success] ${result}`);
    }

    // Demonstrate error handling
    console.log('');
    console.log('Demonstrating error handling...');

    try {
      throw new Error('Intentional error for demonstration');
    } catch (error) {
      if (error instanceof Error) {
        console.error(`[Error] ${error.message}`);
      }
    }

    // Demonstrate analysis control
    console.log('');
    console.log('Testing analysis control...');

    console.log('[Analysis] Disabling analysis...');
    client.disable_analysis();
    console.log('[Internal] This log won\'t be analyzed');

    console.log('[Analysis] Re-enabling analysis...');
    client.enable_analysis();
    console.log('[Analysis] This log will be analyzed');

    // Summary
    console.log('');
    console.log('=== Quickstart Complete ===');
    console.log('✓ All operations logged to daemon');
    console.log('');
    console.log('Next steps:');
    console.log('1. Query logs: python -m drtrace_service why for app typescript-quickstart');
    console.log('2. Check daemon: python -m drtrace_service status');
    console.log('3. See config: cat _drtrace/config.json');
  } catch (error) {
    if (error instanceof Error) {
      console.error(`Fatal error: ${error.message}`);
      console.error(error.stack);
    }
    process.exit(1);
  }

  // Give daemon time to receive final logs
  await new Promise((resolve) => setTimeout(resolve, 1000));
}

// Run application
main();
