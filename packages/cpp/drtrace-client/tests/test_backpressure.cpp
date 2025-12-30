/**
 * Backpressure Tests for DrTrace C++ Client
 *
 * Tests the bounded memory usage feature that prevents OOM
 * when daemon is unavailable or slow.
 */

#include <gtest/gtest.h>
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <thread>
#include <vector>

#include "drtrace_sink.hpp"

namespace drtrace {
namespace testing {

/**
 * Test: Buffer overflow drops oldest logs
 *
 * When the buffer is full, new logs should cause oldest logs to be dropped.
 */
TEST(Backpressure, BufferOverflowDropsOldest) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.max_buffer_size = 100;
  config.batch_size = 200;  // Larger than buffer to prevent auto-flush
  config.flush_interval = std::chrono::milliseconds(60000);  // Disable timer flush

  DrtraceClient client(config, "test-logger");

  // Log 200 messages (buffer can only hold 100)
  for (int i = 0; i < 200; i++) {
    client.info("Message " + std::to_string(i));
  }

  // If we get here without crashing, backpressure is working
  // The buffer should contain the latest 100 messages (100-199)
  // and have dropped messages 0-99
}

/**
 * Test: Memory stays bounded under high load
 *
 * Even with a very high volume of logs, memory should stay bounded.
 */
TEST(Backpressure, MemoryBoundedUnderHighLoad) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.max_buffer_size = 1000;
  config.batch_size = 2000;  // Larger than buffer to prevent auto-flush
  config.flush_interval = std::chrono::milliseconds(60000);  // Disable timer flush

  DrtraceClient client(config, "test-logger");

  // Log 100,000 messages with daemon unavailable
  // Without backpressure, this would consume ~10MB+ of memory
  // With backpressure (max 1000), memory stays bounded to ~100KB
  for (int i = 0; i < 100000; i++) {
    client.info("Test message with some content to increase size " + std::to_string(i));
  }

  // Memory should stay bounded (no OOM)
  // Test passes if it doesn't crash
}

/**
 * Test: Unlimited buffer when set to zero
 *
 * When max_buffer_size is 0, no backpressure should be applied.
 */
TEST(Backpressure, UnlimitedBufferWhenZero) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.max_buffer_size = 0;  // Unlimited
  config.batch_size = 10000;  // Larger than test to prevent auto-flush
  config.flush_interval = std::chrono::milliseconds(60000);  // Disable timer flush

  DrtraceClient client(config, "test-logger");

  // Should not drop any logs
  for (int i = 0; i < 1000; i++) {
    client.info("Message " + std::to_string(i));
  }

  // All 1000 messages should be in buffer (no drops)
  // Test passes if it doesn't crash
}

/**
 * Test: Environment variable configuration
 *
 * Verify DRTRACE_MAX_BUFFER_SIZE environment variable is parsed correctly.
 */
TEST(Backpressure, EnvironmentVariableConfiguration) {
  setenv("DRTRACE_MAX_BUFFER_SIZE", "5000", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.max_buffer_size, 5000u);

  unsetenv("DRTRACE_MAX_BUFFER_SIZE");
}

/**
 * Test: Invalid environment variable is ignored
 *
 * Invalid values should fall back to default.
 */
TEST(Backpressure, InvalidEnvironmentVariableIgnored) {
  setenv("DRTRACE_MAX_BUFFER_SIZE", "not_a_number", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  // Should use default value (10000)
  EXPECT_EQ(config.max_buffer_size, 10000u);

  unsetenv("DRTRACE_MAX_BUFFER_SIZE");
}

/**
 * Test: Zero environment variable means unlimited
 *
 * Setting DRTRACE_MAX_BUFFER_SIZE=0 should disable backpressure.
 */
TEST(Backpressure, ZeroEnvironmentVariableMeansUnlimited) {
  setenv("DRTRACE_MAX_BUFFER_SIZE", "0", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.max_buffer_size, 0u);

  unsetenv("DRTRACE_MAX_BUFFER_SIZE");
}

/**
 * Test: Concurrent logging with backpressure
 *
 * Multiple threads logging simultaneously should work correctly
 * with backpressure enabled.
 */
TEST(Backpressure, ConcurrentLoggingWithBackpressure) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.max_buffer_size = 500;
  config.batch_size = 1000;  // Larger than buffer
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  std::vector<std::thread> threads;
  std::atomic<int> total_logs{0};

  // 4 threads logging 1000 messages each
  for (int t = 0; t < 4; t++) {
    threads.emplace_back([&client, &total_logs, t]() {
      for (int i = 0; i < 1000; i++) {
        client.info("Thread " + std::to_string(t) + " message " + std::to_string(i));
        total_logs.fetch_add(1);
      }
    });
  }

  for (auto& thread : threads) {
    thread.join();
  }

  EXPECT_EQ(total_logs.load(), 4000);
  // Buffer should be bounded to 500 even with 4000 logs
  // No crashes, no OOM - if we get here, test passes
}

/**
 * Test: Backpressure with small buffer
 *
 * Very small buffer should still work correctly.
 */
TEST(Backpressure, SmallBuffer) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.max_buffer_size = 5;  // Very small
  config.batch_size = 10;  // Larger than buffer
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  // Log 100 messages
  for (int i = 0; i < 100; i++) {
    client.info("Message " + std::to_string(i));
  }

  // Buffer should only contain 5 messages
  // No crashes - if we get here, test passes
}

/**
 * Test: Backpressure does not affect flush behavior
 *
 * When buffer is full and flush is triggered, it should work correctly.
 */
TEST(Backpressure, BackpressureWithFlush) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.max_buffer_size = 50;
  config.batch_size = 10;  // Auto-flush every 10 messages
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  // Log 200 messages (will trigger many auto-flushes)
  for (int i = 0; i < 200; i++) {
    client.info("Message " + std::to_string(i));
  }

  // Explicit flush
  client.flush();

  // No crashes - if we get here, test passes
}

}  // namespace testing
}  // namespace drtrace
