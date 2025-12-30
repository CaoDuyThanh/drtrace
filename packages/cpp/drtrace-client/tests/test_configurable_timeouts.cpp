/**
 * Configurable Timeouts Tests for DrTrace C++ Client
 *
 * Tests the configurable HTTP timeout, retry backoff, and max retries
 * for tuning the client for different network environments.
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
 * Test: Default values are correct
 */
TEST(ConfigurableTimeouts, DefaultValues) {
  DrtraceConfig config;

  EXPECT_EQ(config.http_timeout, std::chrono::milliseconds(1000));
  EXPECT_EQ(config.retry_backoff, std::chrono::milliseconds(100));
  EXPECT_EQ(config.max_retries, 3);
}

/**
 * Test: Custom values can be set
 */
TEST(ConfigurableTimeouts, CustomValues) {
  DrtraceConfig config;
  config.http_timeout = std::chrono::milliseconds(5000);
  config.retry_backoff = std::chrono::milliseconds(500);
  config.max_retries = 5;

  EXPECT_EQ(config.http_timeout, std::chrono::milliseconds(5000));
  EXPECT_EQ(config.retry_backoff, std::chrono::milliseconds(500));
  EXPECT_EQ(config.max_retries, 5);
}

/**
 * Test: Environment variable DRTRACE_HTTP_TIMEOUT_MS
 */
TEST(ConfigurableTimeouts, EnvironmentVariableHttpTimeout) {
  setenv("DRTRACE_HTTP_TIMEOUT_MS", "3000", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.http_timeout, std::chrono::milliseconds(3000));

  unsetenv("DRTRACE_HTTP_TIMEOUT_MS");
}

/**
 * Test: Environment variable DRTRACE_RETRY_BACKOFF_MS
 */
TEST(ConfigurableTimeouts, EnvironmentVariableRetryBackoff) {
  setenv("DRTRACE_RETRY_BACKOFF_MS", "200", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.retry_backoff, std::chrono::milliseconds(200));

  unsetenv("DRTRACE_RETRY_BACKOFF_MS");
}

/**
 * Test: Environment variable DRTRACE_MAX_RETRIES
 */
TEST(ConfigurableTimeouts, EnvironmentVariableMaxRetries) {
  setenv("DRTRACE_MAX_RETRIES", "5", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.max_retries, 5);

  unsetenv("DRTRACE_MAX_RETRIES");
}

/**
 * Test: All environment variables together
 */
TEST(ConfigurableTimeouts, AllEnvironmentVariables) {
  setenv("DRTRACE_HTTP_TIMEOUT_MS", "2500", 1);
  setenv("DRTRACE_RETRY_BACKOFF_MS", "150", 1);
  setenv("DRTRACE_MAX_RETRIES", "4", 1);

  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.http_timeout, std::chrono::milliseconds(2500));
  EXPECT_EQ(config.retry_backoff, std::chrono::milliseconds(150));
  EXPECT_EQ(config.max_retries, 4);

  unsetenv("DRTRACE_HTTP_TIMEOUT_MS");
  unsetenv("DRTRACE_RETRY_BACKOFF_MS");
  unsetenv("DRTRACE_MAX_RETRIES");
}

/**
 * Test: Invalid environment variables use defaults
 */
TEST(ConfigurableTimeouts, InvalidEnvironmentVariablesUseDefaults) {
  setenv("DRTRACE_HTTP_TIMEOUT_MS", "not_a_number", 1);
  setenv("DRTRACE_RETRY_BACKOFF_MS", "invalid", 1);
  setenv("DRTRACE_MAX_RETRIES", "abc", 1);

  DrtraceConfig config = DrtraceConfig::from_env();

  // Should use default values
  EXPECT_EQ(config.http_timeout, std::chrono::milliseconds(1000));
  EXPECT_EQ(config.retry_backoff, std::chrono::milliseconds(100));
  EXPECT_EQ(config.max_retries, 3);

  unsetenv("DRTRACE_HTTP_TIMEOUT_MS");
  unsetenv("DRTRACE_RETRY_BACKOFF_MS");
  unsetenv("DRTRACE_MAX_RETRIES");
}

/**
 * Test: Zero retries is allowed (no retries on failure)
 */
TEST(ConfigurableTimeouts, ZeroRetriesAllowed) {
  setenv("DRTRACE_MAX_RETRIES", "0", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.max_retries, 0);

  unsetenv("DRTRACE_MAX_RETRIES");
}

/**
 * Test: Negative values use defaults
 */
TEST(ConfigurableTimeouts, NegativeValuesUseDefaults) {
  setenv("DRTRACE_HTTP_TIMEOUT_MS", "-1000", 1);
  setenv("DRTRACE_RETRY_BACKOFF_MS", "-100", 1);
  setenv("DRTRACE_MAX_RETRIES", "-5", 1);

  DrtraceConfig config = DrtraceConfig::from_env();

  // Negative values should be ignored, use defaults
  EXPECT_EQ(config.http_timeout, std::chrono::milliseconds(1000));
  EXPECT_EQ(config.retry_backoff, std::chrono::milliseconds(100));
  EXPECT_EQ(config.max_retries, 3);

  unsetenv("DRTRACE_HTTP_TIMEOUT_MS");
  unsetenv("DRTRACE_RETRY_BACKOFF_MS");
  unsetenv("DRTRACE_MAX_RETRIES");
}

/**
 * Test: Short timeout results in quick failure
 *
 * This tests that a very short timeout actually affects curl behavior.
 * We use a non-routable IP (10.255.255.1) to ensure the connection times out.
 */
TEST(ConfigurableTimeouts, ShortTimeoutQuickFailure) {
  DrtraceConfig config;
  config.http_timeout = std::chrono::milliseconds(100);  // Very short
  config.retry_backoff = std::chrono::milliseconds(10);
  config.max_retries = 1;  // Only one attempt
  config.daemon_url = "http://10.255.255.1:8001/logs/ingest";  // Non-routable
  config.application_id = "test-app";

  DrtraceClient client(config, "test-logger");

  auto start = std::chrono::steady_clock::now();
  client.info("Test message");
  client.flush();
  auto elapsed = std::chrono::steady_clock::now() - start;

  // Should fail quickly (< 1 second)
  // With 100ms timeout and 1 retry, total should be ~100-300ms
  EXPECT_LT(elapsed, std::chrono::seconds(1));
}

/**
 * Test: Multiple retries with backoff
 *
 * This tests that the retry mechanism with backoff works correctly.
 */
TEST(ConfigurableTimeouts, MultipleRetriesWithBackoff) {
  DrtraceConfig config;
  config.http_timeout = std::chrono::milliseconds(50);  // Very short
  config.retry_backoff = std::chrono::milliseconds(50);  // 50ms base backoff
  config.max_retries = 3;  // 3 attempts
  config.daemon_url = "http://10.255.255.1:8001/logs/ingest";  // Non-routable
  config.application_id = "test-app";

  DrtraceClient client(config, "test-logger");

  auto start = std::chrono::steady_clock::now();
  client.info("Test message");
  client.flush();
  auto elapsed = std::chrono::steady_clock::now() - start;

  // With 3 retries and 50ms backoff:
  // Attempt 1: timeout ~50ms
  // Sleep: 50ms * 1 = 50ms
  // Attempt 2: timeout ~50ms
  // Sleep: 50ms * 2 = 100ms
  // Attempt 3: timeout ~50ms
  // Total: ~300-500ms
  // Should complete within 2 seconds (with generous margin for slow CI)
  EXPECT_LT(elapsed, std::chrono::seconds(2));
}

/**
 * Test: Zero retries means single attempt
 */
TEST(ConfigurableTimeouts, ZeroRetriesSingleAttempt) {
  DrtraceConfig config;
  config.http_timeout = std::chrono::milliseconds(50);
  config.retry_backoff = std::chrono::milliseconds(1000);  // Long backoff (shouldn't be used)
  config.max_retries = 0;  // No retries
  config.daemon_url = "http://10.255.255.1:8001/logs/ingest";  // Non-routable
  config.application_id = "test-app";

  DrtraceClient client(config, "test-logger");

  auto start = std::chrono::steady_clock::now();
  client.info("Test message");
  client.flush();
  auto elapsed = std::chrono::steady_clock::now() - start;

  // With 0 retries, should fail after single timeout (~50ms)
  // No backoff sleep should occur
  EXPECT_LT(elapsed, std::chrono::milliseconds(500));
}

/**
 * Test: Client creation with custom config
 */
TEST(ConfigurableTimeouts, ClientCreationWithCustomConfig) {
  DrtraceConfig config;
  config.http_timeout = std::chrono::milliseconds(2000);
  config.retry_backoff = std::chrono::milliseconds(250);
  config.max_retries = 5;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";

  // Client should be created successfully with custom config
  DrtraceClient client(config, "test-logger");

  // Verify client is enabled
  EXPECT_TRUE(client.is_enabled());
}

/**
 * Test: Large timeout values work correctly
 */
TEST(ConfigurableTimeouts, LargeTimeoutValues) {
  DrtraceConfig config;
  config.http_timeout = std::chrono::milliseconds(60000);  // 60 seconds
  config.retry_backoff = std::chrono::milliseconds(5000);  // 5 seconds
  config.max_retries = 10;

  EXPECT_EQ(config.http_timeout, std::chrono::milliseconds(60000));
  EXPECT_EQ(config.retry_backoff, std::chrono::milliseconds(5000));
  EXPECT_EQ(config.max_retries, 10);
}

}  // namespace testing
}  // namespace drtrace
