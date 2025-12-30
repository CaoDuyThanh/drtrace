/**
 * Circuit Breaker Tests for DrTrace C++ Client
 *
 * Tests the circuit breaker pattern implementation that provides fast-fail
 * behavior when the daemon is unavailable.
 */

#include <gtest/gtest.h>
#include <chrono>
#include <thread>

#include "drtrace_sink.hpp"

namespace drtrace {
namespace testing {

/**
 * Test: Fast-fail when daemon is unavailable
 *
 * When daemon is DOWN, the circuit should open after the first failed batch,
 * and subsequent batches should fast-fail (< 10ms for 100 logs).
 */
TEST(CircuitBreaker, FastFailWhenDaemonDown) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent port
  config.application_id = "test-app";
  config.circuit_reset_interval = std::chrono::milliseconds(30000);  // 30 seconds

  DrtraceClient client(config, "test-logger");

  // First batch will fail and open the circuit (takes ~3.3s for retries)
  client.info("Initial message to open circuit");
  client.flush();

  // Now measure subsequent messages - these should fast-fail
  auto start = std::chrono::steady_clock::now();
  for (int i = 0; i < 100; i++) {
    client.info("Test message " + std::to_string(i));
  }
  client.flush();
  auto elapsed = std::chrono::steady_clock::now() - start;

  // 100 messages should complete in < 100ms (fast-fail, no network calls)
  // This is much faster than the ~33 seconds it would take without circuit breaker
  auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();
  EXPECT_LT(elapsed_ms, 100) << "100 messages should fast-fail in < 100ms, took " << elapsed_ms << "ms";
}

/**
 * Test: Circuit opens after failed connection
 *
 * Verify that the circuit breaker transitions to OPEN state after connection failure.
 */
TEST(CircuitBreaker, CircuitOpensOnFailure) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent port
  config.application_id = "test-app";
  config.circuit_reset_interval = std::chrono::milliseconds(5000);

  // Create transport directly to check circuit state
  HttpTransport transport(config);

  // Initially circuit should be closed
  EXPECT_FALSE(transport.is_circuit_open_for_test()) << "Circuit should start closed";

  // Send a batch that will fail
  std::vector<std::string> batch = {R"({"ts":1234567890,"level":"info","message":"test"})"};
  bool result = transport.send_batch(batch);

  // Send should fail
  EXPECT_FALSE(result) << "Send should fail with non-existent daemon";

  // Circuit should now be open
  EXPECT_TRUE(transport.is_circuit_open_for_test()) << "Circuit should be open after failure";
}

/**
 * Test: Circuit allows probe after cooldown
 *
 * After the circuit reset interval expires, the circuit should allow one probe request.
 */
TEST(CircuitBreaker, CircuitAllowsProbeAfterCooldown) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent port
  config.application_id = "test-app";
  config.circuit_reset_interval = std::chrono::milliseconds(100);  // 100ms for fast test

  HttpTransport transport(config);

  // Open the circuit by failing a request
  std::vector<std::string> batch = {R"({"ts":1234567890,"level":"info","message":"test"})"};
  transport.send_batch(batch);

  // Circuit should be open
  EXPECT_TRUE(transport.is_circuit_open_for_test()) << "Circuit should be open after failure";

  // Wait for cooldown to expire
  std::this_thread::sleep_for(std::chrono::milliseconds(150));

  // Circuit should now allow probe (is_circuit_open returns false)
  EXPECT_FALSE(transport.is_circuit_open_for_test()) << "Circuit should allow probe after cooldown";
}

/**
 * Test: Environment variable configuration
 *
 * Verify that DRTRACE_CIRCUIT_RESET_MS environment variable is parsed correctly.
 */
TEST(CircuitBreaker, EnvironmentVariableConfiguration) {
  // Set environment variable
  setenv("DRTRACE_CIRCUIT_RESET_MS", "5000", 1);

  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.circuit_reset_interval.count(), 5000)
      << "circuit_reset_interval should be 5000ms from env var";

  // Clean up
  unsetenv("DRTRACE_CIRCUIT_RESET_MS");
}

/**
 * Test: Invalid environment variable is ignored
 *
 * Verify that invalid DRTRACE_CIRCUIT_RESET_MS values fall back to default.
 */
TEST(CircuitBreaker, InvalidEnvironmentVariableIgnored) {
  // Set invalid environment variable
  setenv("DRTRACE_CIRCUIT_RESET_MS", "not-a-number", 1);

  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.circuit_reset_interval.count(), 30000)
      << "circuit_reset_interval should be default 30000ms for invalid env var";

  // Clean up
  unsetenv("DRTRACE_CIRCUIT_RESET_MS");
}

/**
 * Test: Performance parity - daemon OFF should not be slower than daemon ON
 *
 * After circuit opens, logging should be as fast (or faster) than when daemon is ON.
 */
TEST(CircuitBreaker, PerformanceParityDaemonOnVsOff) {
  // This test verifies that after circuit opens, logging is fast
  // We can't easily test daemon ON in unit tests, but we can verify
  // that circuit-open logging is very fast (< 1ms per log)

  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.circuit_reset_interval = std::chrono::milliseconds(60000);  // Long cooldown

  DrtraceClient client(config, "test-logger");

  // Open the circuit
  client.info("Open circuit");
  client.flush();

  // Measure logging rate with circuit open
  const int num_logs = 1000;
  auto start = std::chrono::steady_clock::now();
  for (int i = 0; i < num_logs; i++) {
    client.info("Performance test message " + std::to_string(i));
  }
  auto elapsed = std::chrono::steady_clock::now() - start;

  auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count();
  double us_per_log = static_cast<double>(elapsed_us) / num_logs;

  // Each log should take < 100 microseconds on average (fast-fail + serialization)
  EXPECT_LT(us_per_log, 100.0)
      << "With circuit open, each log should take < 100µs, took " << us_per_log << "µs";
}

/**
 * Test: Thread safety of circuit breaker
 *
 * Multiple threads should be able to log concurrently without issues.
 */
TEST(CircuitBreaker, ThreadSafety) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.circuit_reset_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  // Open the circuit first
  client.info("Open circuit");
  client.flush();

  const int num_threads = 4;
  const int logs_per_thread = 100;
  std::vector<std::thread> threads;

  auto start = std::chrono::steady_clock::now();

  for (int t = 0; t < num_threads; t++) {
    threads.emplace_back([&client, t, logs_per_thread]() {
      for (int i = 0; i < logs_per_thread; i++) {
        client.info("Thread " + std::to_string(t) + " message " + std::to_string(i));
      }
    });
  }

  for (auto& thread : threads) {
    thread.join();
  }

  client.flush();
  auto elapsed = std::chrono::steady_clock::now() - start;

  auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

  // 400 logs from 4 threads should complete in < 500ms with circuit open
  EXPECT_LT(elapsed_ms, 500)
      << "Multi-threaded logging with circuit open should complete in < 500ms, took "
      << elapsed_ms << "ms";
}

}  // namespace testing
}  // namespace drtrace
