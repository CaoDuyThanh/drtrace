/**
 * Minimal C++ example application using DrTrace integration with spdlog.
 *
 * This demonstrates Pattern 1: Using the spdlog adapter (DrtraceSink).
 * For projects without spdlog, see minimal_cpp_app_direct.cpp
 *
 * Header-only build example:
 *   - Ensure drtrace_sink.hpp has been copied to third_party/drtrace/drtrace_sink.hpp
 *     (via the DrTrace init-project command).
 *   - Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)
 *   - Then build with:
 *       g++ -std=c++17 minimal_cpp_app.cpp -I./third_party/drtrace -I/path/to/spdlog/include \
 *           -L/path/to/spdlog/lib -lspdlog -lcurl -pthread -o minimal_cpp_app
 */

#include "third_party/drtrace/drtrace_sink.hpp"
#include <spdlog/spdlog.h>
#include <iostream>
#include <thread>
#include <chrono>

int main() {
  try {
    // Load configuration from environment variables
    drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

    std::cout << "DrTrace C++ Client Example (spdlog adapter)" << std::endl;
    std::cout << "Application ID: " << config.application_id << std::endl;
    std::cout << "Daemon URL: " << config.daemon_url << std::endl;
    std::cout << "Enabled: " << (config.enabled ? "true" : "false") << std::endl;

    // Create a logger with DrTrace integration
    auto logger = drtrace::create_drtrace_logger("my_cpp_app", config);

    // Set log level
    logger->set_level(spdlog::level::info);

    // Emit logs at various levels
    logger->info("C++ application started");
    logger->debug("This is a debug message (may not be sent if level is INFO)");
    logger->warn("This is a warning message");
    logger->error("This is an error message");

    // Log with additional context
    logger->info("Processing request {}", 12345);
    logger->warn("Low memory warning: {} MB available", 512);

    // Simulate some work
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // Error with file/line information (spdlog provides this automatically)
    logger->error("Simulated error in main function");

    // Give the background thread time to flush the batch
    std::cout << "Waiting for logs to be sent..." << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(6));

    // Explicitly flush before exit
    logger->flush();

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

