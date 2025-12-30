import { setup_logging, ClientConfig } from 'drtrace';

// Configure DrTrace for this client
const config = new ClientConfig({
  application_id: 'cross-language-example-ts',
  daemon_host: 'localhost',
  daemon_port: 8000,
  log_level: 'DEBUG',
});

// Initialize logging
setup_logging(config);

// Helper function to make API calls
async function apiCall(
  method: string,
  endpoint: string,
  body?: Record<string, any>
): Promise<any> {
  const url = `http://localhost:8001${endpoint}`;
  console.log(`[API] ${method} ${endpoint}`);

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      console.error(
        `[API Error] ${method} ${endpoint} returned ${response.status}`
      );
      const error = await response.json();
      return { error };
    }

    const data = await response.json();
    console.log(`[API Success] ${method} ${endpoint}: ${JSON.stringify(data)}`);
    return data;
  } catch (error) {
    if (error instanceof Error) {
      console.error(`[API Error] ${method} ${endpoint}: ${error.message}`);
    }
    throw error;
  }
}

// Main client flow
async function main(): Promise<void> {
  console.log('=== Cross-Language Example (TypeScript Client) ===');
  console.log('');

  try {
    // Check API is healthy
    console.log('Checking API health...');
    await apiCall('GET', '/health');

    // Create users
    console.log('');
    console.log('Creating users...');
    const user1 = await apiCall('POST', '/api/users?name=Alice');
    const user2 = await apiCall('POST', '/api/users?name=Bob');

    // List users
    console.log('');
    console.log('Listing users...');
    await apiCall('GET', '/api/users');

    // Get specific user
    console.log('');
    console.log('Fetching user by ID...');
    await apiCall('GET', `/api/users/${user1.id}`);

    // Update user
    console.log('');
    console.log('Updating user...');
    await apiCall('PUT', `/api/users/${user1.id}?name=Alice_Updated`);

    // Delete user
    console.log('');
    console.log('Deleting user...');
    await apiCall('DELETE', `/api/users/${user2.id}`);

    // Final list
    console.log('');
    console.log('Final user list...');
    await apiCall('GET', '/api/users');

    console.log('');
    console.log('=== Example Complete ===');
    console.log('All operations logged to daemon');
    console.log('');
    console.log('Query logs:');
    console.log('  python -m drtrace_service why for app cross-language-example');
    console.log('  python -m drtrace_service why for app cross-language-example since "last 5 minutes"');
  } catch (error) {
    if (error instanceof Error) {
      console.error(`Fatal error: ${error.message}`);
    }
    process.exit(1);
  }

  // Give daemon time to receive logs
  await new Promise((resolve) => setTimeout(resolve, 1000));
}

// Run the client
main();
