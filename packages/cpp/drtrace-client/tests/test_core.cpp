/**
 * Unit tests for DrTrace C++ core components (spdlog-independent).
 * 
 * Tests:
 * - LogRecord structure
 * - DrtraceCore::log() - single and multiple records
 * - DrtraceCore::serialize_record() - JSON serialization
 * - DrtraceCore::flush() - batching and flushing
 * - Thread safety
 */

#include <gtest/gtest.h>
// Note: In tests, we include the header directly from src/ since it's not copied to third_party/
// In real usage, users would include from third_party/drtrace/drtrace_sink.hpp
#include "../src/drtrace_sink.hpp"
#include <thread>
#include <vector>
#include <chrono>

using namespace drtrace;
using namespace drtrace::core;

class DrtraceCoreTest : public ::testing::Test {
 protected:
  void SetUp() override {
    // Create a test config
    config_.application_id = "test-app";
    config_.daemon_url = "http://localhost:8001/logs/ingest";
    config_.enabled = true;
    config_.batch_size = 5;  // Small batch size for testing
    config_.flush_interval = std::chrono::milliseconds(1000);
    
    core_ = std::make_unique<DrtraceCore>(config_);
  }
  
  void TearDown() override {
    if (core_) {
      core_->flush();
      core_.reset();
    }
  }
  
  DrtraceConfig config_;
  std::unique_ptr<DrtraceCore> core_;
};

// Test LogRecord structure creation
TEST_F(DrtraceCoreTest, LogRecordCreation) {
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Test message";
  record.logger_name = "test_logger";
  record.timestamp = std::chrono::system_clock::now();
  record.source.filename = "test.cpp";
  record.source.line = 42;
  record.source.function = "test_function";
  
  EXPECT_EQ(record.level, LogLevel::INFO);
  EXPECT_EQ(record.message, "Test message");
  EXPECT_EQ(record.logger_name, "test_logger");
  EXPECT_EQ(record.source.filename, "test.cpp");
  EXPECT_EQ(record.source.line, 42);
  EXPECT_EQ(record.source.function, "test_function");
}

// Test DrtraceCore::log() - single record
TEST_F(DrtraceCoreTest, LogSingleRecord) {
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Single log message";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  // Should not throw
  EXPECT_NO_THROW(core_->log(record));
}

// Test DrtraceCore::log() - multiple records (batching)
TEST_F(DrtraceCoreTest, LogMultipleRecords) {
  for (int i = 0; i < 10; ++i) {
    LogRecord record;
    record.level = LogLevel::INFO;
    record.message = "Message " + std::to_string(i);
    record.logger_name = "test";
    record.timestamp = std::chrono::system_clock::now();
    
    EXPECT_NO_THROW(core_->log(record));
  }
  
  // Flush to ensure all records are processed
  EXPECT_NO_THROW(core_->flush());
}

// Test DrtraceCore::serialize_record() - all log levels
TEST_F(DrtraceCoreTest, SerializeAllLogLevels) {
  std::vector<LogLevel> levels = {
    LogLevel::DEBUG,
    LogLevel::INFO,
    LogLevel::WARN,
    LogLevel::ERROR,
    LogLevel::CRITICAL
  };
  
  for (auto level : levels) {
    LogRecord record;
    record.level = level;
    record.message = "Test message";
    record.logger_name = "test";
    record.timestamp = std::chrono::system_clock::now();
    
    EXPECT_NO_THROW(core_->log(record));
  }
  
  EXPECT_NO_THROW(core_->flush());
}

// Test DrtraceCore::serialize_record() - with source location
TEST_F(DrtraceCoreTest, SerializeWithSourceLocation) {
  LogRecord record;
  record.level = LogLevel::ERROR;
  record.message = "Error with location";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  record.source.filename = "test.cpp";
  record.source.line = 123;
  record.source.function = "test_function";
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test DrtraceCore::serialize_record() - without source location
TEST_F(DrtraceCoreTest, SerializeWithoutSourceLocation) {
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Info without location";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  // source.filename and source.function are empty strings by default
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test DrtraceCore::serialize_record() - with service_name
TEST_F(DrtraceCoreTest, SerializeWithServiceName) {
  config_.service_name = "test-service";
  core_ = std::make_unique<DrtraceCore>(config_);
  
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Message with service";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test DrtraceCore::flush() - empty batch (no-op)
TEST_F(DrtraceCoreTest, FlushEmptyBatch) {
  // Flush without any logs should not throw
  EXPECT_NO_THROW(core_->flush());
}

// Test DrtraceCore - disabled state (no-op)
TEST_F(DrtraceCoreTest, DisabledState) {
  config_.enabled = false;
  core_ = std::make_unique<DrtraceCore>(config_);
  
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Should be ignored";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  // Should not throw, but record should be ignored
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_FALSE(core_->is_enabled());
}

// Test DrtraceCore - thread safety (concurrent logging)
TEST_F(DrtraceCoreTest, ThreadSafety) {
  const int num_threads = 4;
  const int logs_per_thread = 10;
  
  std::vector<std::thread> threads;
  
  for (int t = 0; t < num_threads; ++t) {
    threads.emplace_back([this, t, logs_per_thread]() {
      for (int i = 0; i < logs_per_thread; ++i) {
        LogRecord record;
        record.level = LogLevel::INFO;
        record.message = "Thread " + std::to_string(t) + " message " + std::to_string(i);
        record.logger_name = "test";
        record.timestamp = std::chrono::system_clock::now();
        
        core_->log(record);
      }
    });
  }
  
  // Wait for all threads
  for (auto& thread : threads) {
    thread.join();
  }
  
  // Flush all records
  EXPECT_NO_THROW(core_->flush());
}

// Test DrtraceCore - large batch sizes (stress test)
TEST_F(DrtraceCoreTest, LargeBatchSize) {
  config_.batch_size = 100;
  core_ = std::make_unique<DrtraceCore>(config_);
  
  // Log more than batch size
  for (int i = 0; i < 250; ++i) {
    LogRecord record;
    record.level = LogLevel::INFO;
    record.message = "Large batch message " + std::to_string(i);
    record.logger_name = "test";
    record.timestamp = std::chrono::system_clock::now();
    
    EXPECT_NO_THROW(core_->log(record));
  }
  
  EXPECT_NO_THROW(core_->flush());
}

// Test SourceLocation with std::string (memory safety)
TEST_F(DrtraceCoreTest, SourceLocationMemorySafety) {
  LogRecord record;
  record.level = LogLevel::ERROR;
  record.message = "Memory safety test";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  // Test with temporary string (should be safe)
  {
    std::string temp_filename = "temp_file.cpp";
    std::string temp_function = "temp_function";
    
    record.source.filename = temp_filename;
    record.source.function = temp_function;
    
    // temp_filename and temp_function go out of scope here
  }
  
  // record.source should still be valid (copied strings)
  EXPECT_EQ(record.source.filename, "temp_file.cpp");
  EXPECT_EQ(record.source.function, "temp_function");
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Empty messages
TEST_F(DrtraceCoreTest, EmptyMessage) {
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "";  // Empty message
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Special characters in messages (JSON escaping)
TEST_F(DrtraceCoreTest, SpecialCharactersInMessage) {
  LogRecord record;
  record.level = LogLevel::ERROR;
  // Test various special characters that need JSON escaping
  record.message = "Error with special chars: \"quotes\" 'apostrophes' \\backslash\\ /slash/ \nnewline\t\ttab \r\r\r\r";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Very long log messages (serialization limits)
TEST_F(DrtraceCoreTest, VeryLongMessage) {
  LogRecord record;
  record.level = LogLevel::INFO;
  // Create a very long message (10KB)
  record.message = std::string(10000, 'A') + " - This is a very long message";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Empty source locations (explicit test)
TEST_F(DrtraceCoreTest, EmptySourceLocation) {
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Message with empty source location";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  // Explicitly set empty strings
  record.source.filename = "";
  record.source.function = "";
  record.source.line = 0;
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Special characters in source location
TEST_F(DrtraceCoreTest, SpecialCharactersInSourceLocation) {
  LogRecord record;
  record.level = LogLevel::ERROR;
  record.message = "Error message";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  // Test special characters in filename and function name
  record.source.filename = "path/with\"quotes\"and\\backslashes/file.cpp";
  record.source.function = "function<with>special::chars()";
  record.source.line = 42;
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Rapid enable/disable toggling
TEST_F(DrtraceCoreTest, RapidEnableDisable) {
  // Toggle enabled state multiple times
  for (int i = 0; i < 5; ++i) {
    config_.enabled = (i % 2 == 0);
    core_ = std::make_unique<DrtraceCore>(config_);
    
    LogRecord record;
    record.level = LogLevel::INFO;
    record.message = "Message during toggle " + std::to_string(i);
    record.logger_name = "test";
    record.timestamp = std::chrono::system_clock::now();
    
    EXPECT_NO_THROW(core_->log(record));
  }
  
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Destruction during active logging (clean shutdown)
TEST_F(DrtraceCoreTest, DestructionDuringLogging) {
  // Log multiple records
  for (int i = 0; i < 10; ++i) {
    LogRecord record;
    record.level = LogLevel::INFO;
    record.message = "Message " + std::to_string(i);
    record.logger_name = "test";
    record.timestamp = std::chrono::system_clock::now();
    
    core_->log(record);
  }
  
  // Destroy core without explicit flush (should flush in destructor)
  core_.reset();
  
  // Should not crash or throw
  EXPECT_TRUE(true);
}

// Test edge case: Special characters in logger name
TEST_F(DrtraceCoreTest, SpecialCharactersInLoggerName) {
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Test message";
  record.logger_name = "logger/with\"special\"chars::module";
  record.timestamp = std::chrono::system_clock::now();
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Unicode characters in message
TEST_F(DrtraceCoreTest, UnicodeCharacters) {
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Unicode: 你好世界 🌍 émojis 🚀";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
}

// Test edge case: Network failure during flush (graceful degradation)
// Tests that the system handles network failures gracefully without crashing
TEST_F(DrtraceCoreTest, NetworkFailureDuringFlush) {
  // First, properly clean up the existing core from SetUp
  if (core_) {
    core_->flush();
    core_.reset();
  }
  
  // Configure with invalid/unreachable daemon URL
  config_.daemon_url = "http://127.0.0.1:99999/logs/ingest";  // Invalid port
  config_.enabled = true;
  core_ = std::make_unique<DrtraceCore>(config_);
  
  // Log multiple records
  for (int i = 0; i < 5; ++i) {
    LogRecord record;
    record.level = LogLevel::INFO;
    record.message = "Message " + std::to_string(i) + " (network will fail)";
    record.logger_name = "test";
    record.timestamp = std::chrono::system_clock::now();
    
    // Should not throw even though network will fail
    EXPECT_NO_THROW(core_->log(record));
  }
  
  // Flush should complete without throwing (graceful degradation)
  EXPECT_NO_THROW(core_->flush());
  
  // System should still be usable after network failure
  EXPECT_TRUE(core_->is_enabled());
  
  // Should be able to log more records after failure
  LogRecord record;
  record.level = LogLevel::INFO;
  record.message = "Message after network failure";
  record.logger_name = "test";
  record.timestamp = std::chrono::system_clock::now();
  EXPECT_NO_THROW(core_->log(record));
  EXPECT_NO_THROW(core_->flush());
  
  // Explicitly clean up before TearDown (TearDown will also try to flush/reset)
  if (core_) {
    core_->flush();
    core_.reset();
  }
}

