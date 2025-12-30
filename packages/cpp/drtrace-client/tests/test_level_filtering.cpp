/**
 * Log Level Filtering Tests for DrTrace C++ Client
 *
 * Tests the client-side log level filtering that reduces network overhead
 * by filtering logs below min_level before they're batched/sent.
 */

#include <gtest/gtest.h>
#include <cstdlib>

#include "drtrace_sink.hpp"

namespace drtrace {
namespace testing {

/**
 * Test: Default min_level is DEBUG (backward compatible)
 *
 * Ensures existing code without min_level continues to work.
 */
TEST(LevelFiltering, DefaultIsDebug) {
  DrtraceConfig config;

  EXPECT_EQ(config.min_level, core::LogLevel::DEBUG);
}

/**
 * Test: Parse log level - valid inputs
 *
 * Tests case-insensitive parsing of log levels.
 */
TEST(LevelFiltering, ParseLogLevelValid) {
  EXPECT_EQ(parse_log_level("debug"), core::LogLevel::DEBUG);
  EXPECT_EQ(parse_log_level("DEBUG"), core::LogLevel::DEBUG);
  EXPECT_EQ(parse_log_level("Debug"), core::LogLevel::DEBUG);

  EXPECT_EQ(parse_log_level("info"), core::LogLevel::INFO);
  EXPECT_EQ(parse_log_level("INFO"), core::LogLevel::INFO);

  EXPECT_EQ(parse_log_level("warn"), core::LogLevel::WARN);
  EXPECT_EQ(parse_log_level("WARN"), core::LogLevel::WARN);
  EXPECT_EQ(parse_log_level("warning"), core::LogLevel::WARN);
  EXPECT_EQ(parse_log_level("WARNING"), core::LogLevel::WARN);

  EXPECT_EQ(parse_log_level("error"), core::LogLevel::ERROR);
  EXPECT_EQ(parse_log_level("ERROR"), core::LogLevel::ERROR);

  EXPECT_EQ(parse_log_level("critical"), core::LogLevel::CRITICAL);
  EXPECT_EQ(parse_log_level("CRITICAL"), core::LogLevel::CRITICAL);
}

/**
 * Test: Parse log level - invalid inputs default to DEBUG
 */
TEST(LevelFiltering, ParseLogLevelInvalid) {
  EXPECT_EQ(parse_log_level("invalid"), core::LogLevel::DEBUG);
  EXPECT_EQ(parse_log_level(""), core::LogLevel::DEBUG);
  EXPECT_EQ(parse_log_level(nullptr), core::LogLevel::DEBUG);
  EXPECT_EQ(parse_log_level("trace"), core::LogLevel::DEBUG);  // Not a valid level
}

/**
 * Test: Environment variable support
 */
TEST(LevelFiltering, EnvironmentVariableSupport) {
  setenv("DRTRACE_MIN_LEVEL", "error", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.min_level, core::LogLevel::ERROR);

  unsetenv("DRTRACE_MIN_LEVEL");
}

/**
 * Test: Environment variable case insensitive
 */
TEST(LevelFiltering, EnvironmentVariableCaseInsensitive) {
  setenv("DRTRACE_MIN_LEVEL", "WARN", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.min_level, core::LogLevel::WARN);

  unsetenv("DRTRACE_MIN_LEVEL");
}

/**
 * Test: Invalid environment variable defaults to DEBUG
 */
TEST(LevelFiltering, EnvironmentVariableInvalidDefaultsToDebug) {
  setenv("DRTRACE_MIN_LEVEL", "not_a_level", 1);
  DrtraceConfig config = DrtraceConfig::from_env();

  EXPECT_EQ(config.min_level, core::LogLevel::DEBUG);

  unsetenv("DRTRACE_MIN_LEVEL");
}

/**
 * Test: Logs below min_level are filtered
 *
 * With min_level=WARN, DEBUG and INFO should be filtered.
 */
TEST(LevelFiltering, LogsBelowMinLevelFiltered) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.min_level = core::LogLevel::WARN;  // Filter DEBUG and INFO
  config.batch_size = 100;  // Large batch to prevent auto-flush
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  // These should be filtered (below WARN)
  client.debug("Debug message");
  client.info("Info message");

  // These should NOT be filtered (>= WARN)
  client.warn("Warn message");
  client.error("Error message");
  client.critical("Critical message");

  // Flush and expect the client to work without crashing
  // (We can't easily verify the exact count without mocking transport)
  client.flush();
}

/**
 * Test: LogLevel comparison works correctly
 */
TEST(LevelFiltering, LogLevelComparison) {
  // DEBUG < INFO < WARN < ERROR < CRITICAL
  EXPECT_LT(core::LogLevel::DEBUG, core::LogLevel::INFO);
  EXPECT_LT(core::LogLevel::INFO, core::LogLevel::WARN);
  EXPECT_LT(core::LogLevel::WARN, core::LogLevel::ERROR);
  EXPECT_LT(core::LogLevel::ERROR, core::LogLevel::CRITICAL);

  // Same level
  EXPECT_FALSE(core::LogLevel::INFO < core::LogLevel::INFO);
  EXPECT_FALSE(core::LogLevel::WARN < core::LogLevel::WARN);
}

/**
 * Test: All levels pass when min_level is DEBUG
 */
TEST(LevelFiltering, AllLevelsPassWhenDebug) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.min_level = core::LogLevel::DEBUG;  // All pass
  config.batch_size = 100;
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  // All should pass
  client.debug("Debug message");
  client.info("Info message");
  client.warn("Warn message");
  client.error("Error message");
  client.critical("Critical message");

  client.flush();
}

/**
 * Test: Only CRITICAL passes when min_level is CRITICAL
 */
TEST(LevelFiltering, OnlyCriticalWhenMinLevelCritical) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.min_level = core::LogLevel::CRITICAL;  // Only CRITICAL passes
  config.batch_size = 100;
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  // These should be filtered
  client.debug("Debug message");
  client.info("Info message");
  client.warn("Warn message");
  client.error("Error message");

  // This should pass
  client.critical("Critical message");

  client.flush();
}

/**
 * Test: Filtering doesn't affect enabled flag
 */
TEST(LevelFiltering, FilteringWithDisabled) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";
  config.application_id = "test-app";
  config.enabled = false;  // Disabled
  config.min_level = core::LogLevel::DEBUG;  // Would allow all

  DrtraceClient client(config, "test-logger");

  // These should all be skipped due to enabled=false
  client.debug("Debug message");
  client.info("Info message");
  client.warn("Warn message");
  client.error("Error message");
  client.critical("Critical message");

  client.flush();
}

/**
 * Test: Concurrent logging with level filtering
 */
TEST(LevelFiltering, ConcurrentLoggingWithFiltering) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.min_level = core::LogLevel::WARN;
  config.batch_size = 100;
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  std::vector<std::thread> threads;

  // 4 threads logging at different levels
  for (int t = 0; t < 4; t++) {
    threads.emplace_back([&client, t]() {
      for (int i = 0; i < 100; i++) {
        switch (i % 5) {
          case 0: client.debug("Debug " + std::to_string(t)); break;
          case 1: client.info("Info " + std::to_string(t)); break;
          case 2: client.warn("Warn " + std::to_string(t)); break;
          case 3: client.error("Error " + std::to_string(t)); break;
          case 4: client.critical("Critical " + std::to_string(t)); break;
        }
      }
    });
  }

  for (auto& thread : threads) {
    thread.join();
  }

  client.flush();
  // No crashes - if we get here, test passes
}

}  // namespace testing
}  // namespace drtrace
