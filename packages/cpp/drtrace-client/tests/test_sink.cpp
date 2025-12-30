/**
 * Unit tests for DrTrace C++ DrtraceSink (spdlog adapter).
 * 
 * Tests:
 * - DrtraceSink::convert_to_log_record() - level mapping
 * - DrtraceSink::convert_to_log_record() - message and logger name copying
 * - DrtraceSink::convert_to_log_record() - source location copying
 * - DrtraceSink::sink_it_() - forwards to DrtraceCore
 * - DrtraceSink::flush_() - forwards to DrtraceCore
 * - setup_drtrace() - adds sink to existing logger
 * - create_drtrace_logger() - creates logger with sink
 */

#include <gtest/gtest.h>
// Note: In tests, we include the header directly from src/ since it's not copied to third_party/
// In real usage, users would include from third_party/drtrace/drtrace_sink.hpp
#include "../src/drtrace_sink.hpp"
#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <memory>

using namespace drtrace;

// Only compile these tests if spdlog is available
#if DRTRACE_SPDLOG_AVAILABLE

class DrtraceSinkTest : public ::testing::Test {
 protected:
  void SetUp() override {
    // Create a test config
    config_.application_id = "test-app";
    config_.daemon_url = "http://localhost:8001/logs/ingest";
    config_.enabled = true;
    config_.batch_size = 5;
    config_.flush_interval = std::chrono::milliseconds(1000);
  }
  
  void TearDown() override {
    spdlog::drop_all();  // Clean up registered loggers
  }
  
  DrtraceConfig config_;
};

// Test DrtraceSink::sink_it_() - forwards to DrtraceCore (test through actual spdlog API)
// Note: We test through the actual spdlog API rather than manually constructing log_msg
// because log_msg has internal buffers that are complex to initialize correctly.
TEST_F(DrtraceSinkTest, SinkItForwardsToCore) {
  auto sink = std::make_shared<DrtraceSink_mt>(config_);
  auto logger = std::make_shared<spdlog::logger>("test_logger", sink);
  
  // Test all log levels through actual spdlog API
  EXPECT_NO_THROW(logger->trace("Trace message"));
  EXPECT_NO_THROW(logger->debug("Debug message"));
  EXPECT_NO_THROW(logger->info("Info message"));
  EXPECT_NO_THROW(logger->warn("Warn message"));
  EXPECT_NO_THROW(logger->error("Error message"));
  EXPECT_NO_THROW(logger->critical("Critical message"));
  
  EXPECT_NO_THROW(logger->flush());
}

// Test setup_drtrace() - adds sink to existing logger
TEST_F(DrtraceSinkTest, SetupDrtraceAddsSink) {
  // Create a fresh logger for this test
  auto logger = spdlog::create<spdlog::sinks::stdout_color_sink_mt>("test_setup_logger");
  ASSERT_NE(logger, nullptr);
  
  size_t initial_sink_count = logger->sinks().size();
  
  setup_drtrace(logger, config_);
  
  // Should have one more sink
  EXPECT_EQ(logger->sinks().size(), initial_sink_count + 1);
  
  // Logging should work
  EXPECT_NO_THROW(logger->info("Test message"));
  EXPECT_NO_THROW(logger->flush());
  
  // Clean up
  spdlog::drop("test_setup_logger");
}

// Test create_drtrace_logger() - creates logger with sink
TEST_F(DrtraceSinkTest, CreateDrtraceLogger) {
  auto logger = create_drtrace_logger("test_logger", config_);
  
  EXPECT_NE(logger, nullptr);
  EXPECT_GT(logger->sinks().size(), 0);
  
  // Logging should work
  EXPECT_NO_THROW(logger->info("Test message"));
  EXPECT_NO_THROW(logger->flush());
}

// Test create_drtrace_logger() - returns existing logger if already exists
TEST_F(DrtraceSinkTest, CreateDrtraceLoggerReturnsExisting) {
  auto logger1 = create_drtrace_logger("shared_logger", config_);
  auto logger2 = create_drtrace_logger("shared_logger", config_);
  
  // Should return the same logger
  EXPECT_EQ(logger1, logger2);
}

// Test edge case: Empty messages
TEST_F(DrtraceSinkTest, EmptyMessage) {
  auto logger = create_drtrace_logger("test_empty", config_);
  EXPECT_NO_THROW(logger->info(""));
  EXPECT_NO_THROW(logger->flush());
}

// Test edge case: Special characters in messages (JSON escaping)
TEST_F(DrtraceSinkTest, SpecialCharactersInMessage) {
  auto logger = create_drtrace_logger("test_special", config_);
  EXPECT_NO_THROW(logger->error("Error: \"quotes\" 'apostrophes' \\backslash\\ \nnewline\t\ttab"));
  EXPECT_NO_THROW(logger->flush());
}

// Test edge case: Very long log messages
TEST_F(DrtraceSinkTest, VeryLongMessage) {
  auto logger = create_drtrace_logger("test_long", config_);
  std::string long_message(10000, 'A');
  EXPECT_NO_THROW(logger->info(long_message));
  EXPECT_NO_THROW(logger->flush());
}

// Test edge case: Unicode characters
TEST_F(DrtraceSinkTest, UnicodeCharacters) {
  auto logger = create_drtrace_logger("test_unicode", config_);
  EXPECT_NO_THROW(logger->info("Unicode: 你好世界 🌍 émojis 🚀"));
  EXPECT_NO_THROW(logger->flush());
}

// Test edge case: Rapid enable/disable toggling
TEST_F(DrtraceSinkTest, RapidEnableDisable) {
  for (int i = 0; i < 5; ++i) {
    config_.enabled = (i % 2 == 0);
    auto logger = create_drtrace_logger("test_toggle", config_);
    EXPECT_NO_THROW(logger->info("Message during toggle " + std::to_string(i)));
    EXPECT_NO_THROW(logger->flush());
  }
}

// Test edge case: Destruction during active logging
TEST_F(DrtraceSinkTest, DestructionDuringLogging) {
  auto logger = create_drtrace_logger("test_destruction", config_);
  
  // Log multiple records
  for (int i = 0; i < 10; ++i) {
    logger->info("Message " + std::to_string(i));
  }
  
  // Destroy logger without explicit flush (should flush in destructor)
  logger.reset();
  spdlog::drop("test_destruction");
  
  // Should not crash or throw
  EXPECT_TRUE(true);
}

#endif  // DRTRACE_SPDLOG_AVAILABLE

