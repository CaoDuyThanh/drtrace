/**
 * Test program to verify timestamp fix.
 * 
 * Generates multiple logs with small delays to test if timestamps are unique.
 */

#include <iostream>
#include <thread>
#include <chrono>
#include "../src/drtrace_sink.hpp"

using namespace drtrace;

int main() {
  // Configure DrTrace
  DrtraceConfig config;
  config.application_id = "timestamp-test";
  config.daemon_url = "http://localhost:8001/logs/ingest";
  config.enabled = true;
  
  // Create client
  DrtraceClient client(config);
  
  std::cout << "Generating 10 test logs with 100ms delays..." << std::endl;
  
  // Generate 10 logs with small delays
  for (int i = 0; i < 10; ++i) {
    client.info("Test log message " + std::to_string(i));
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  
  // Flush to ensure logs are sent
  std::cout << "Flushing logs..." << std::endl;
  std::this_thread::sleep_for(std::chrono::seconds(2));
  
  std::cout << "Test logs generated. Check daemon logs for timestamp values." << std::endl;
  std::cout << "Query logs: curl \"http://localhost:8001/logs/query?start_ts=0&end_ts=9999999999&application_id=timestamp-test&limit=10\"" << std::endl;
  
  return 0;
}

