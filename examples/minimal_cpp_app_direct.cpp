/**
 * Minimal C++ example application using DrTrace direct API (no spdlog required).
 *
 * This demonstrates Pattern 2: Using the direct API (DrtraceClient) without spdlog.
 * For projects using spdlog, see minimal_cpp_app.cpp
 *
 * Header-only build example:
 *   - Ensure drtrace_sink.hpp has been copied to third_party/drtrace/drtrace_sink.hpp
 *     (via the DrTrace init-project command).
 *   - Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)
 *   - Then build with:
 *       g++ -std=c++17 minimal_cpp_app_direct.cpp -I./third_party/drtrace \
 *           -lcurl -pthread -o minimal_cpp_app_direct
 *   - Note: No spdlog dependency required!
 */

#include "third_party/drtrace/drtrace_sink.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
  try {
    // Load configuration from environment variables
    drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

    std::cout << "DrTrace C++ Client Example (direct API, no spdlog)" << std::endl;
    std::cout << "Application ID: " << config.application_id << std::endl;
    std::cout << "Daemon URL: " << config.daemon_url << std::endl;
    std::cout << "Enabled: " << (config.enabled ? "true" : "false") << std::endl;

    // Create a DrTrace client (no spdlog required)
    drtrace::DrtraceClient client(config, "my_cpp_app");

    // Emit logs at various levels using direct API
    client.info("C++ application started");
    client.debug("This is a debug message");
    client.warn("This is a warning message");
    client.error("This is an error message", __FILE__, __LINE__);

    // Log with source location
    client.info("Processing request 12345", __FILE__, __LINE__);
    client.warn("Low memory warning: 512 MB available", __FILE__, __LINE__);

    // Simulate some work
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // Error with file/line information
    client.error("Simulated error in main function", __FILE__, __LINE__);

    // Give the background thread time to flush the batch
    std::cout << "Waiting for logs to be sent..." << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(6));

    // Explicitly flush before exit
    client.flush();

    std::cout << "Example completed. Check the daemon logs to verify ingestion."
              << std::endl;

  } catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << std::endl;
    std::cerr << "Make sure DRTRACE_APPLICATION_ID is set in the environment."
              << std::endl;
    return 1;
  }

  return 0;
}

