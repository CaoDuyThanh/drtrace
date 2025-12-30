/**
 * Unit tests for DrTrace C++ DrtraceClient (direct API, no spdlog required).
 * 
 * Tests:
 * - DrtraceClient constructor
 * - DrtraceClient::log() - all log levels
 * - DrtraceClient convenience methods (debug, info, warn, error, critical)
 * - Source location handling
 * - Flush functionality
 * - Disabled state
 * - Thread safety
 */

#include <gtest/gtest.h>
// Note: In tests, we include the header directly from src/ since it's not copied to third_party/
// In real usage, users would include from third_party/drtrace/drtrace_sink.hpp
#include "../src/drtrace_sink.hpp"
#include <thread>
#include <vector>

using namespace drtrace;

class DrtraceClientTest : public ::testing::Test {
 protected:
  void SetUp() override {
    // Create a test config
    config_.application_id = "test-app";
    config_.daemon_url = "http://localhost:8001/logs/ingest";
    config_.enabled = true;
    config_.batch_size = 5;
    config_.flush_interval = std::chrono::milliseconds(1000);
    
    client_ = std::make_unique<DrtraceClient>(config_, "test_logger");
  }
  
  void TearDown() override {
    if (client_) {
      client_->flush();
      client_.reset();
    }
  }
  
  DrtraceConfig config_;
  std::unique_ptr<DrtraceClient> client_;
};

// Test DrtraceClient constructor
TEST_F(DrtraceClientTest, Constructor) {
  DrtraceClient client(config_, "my_logger");
  EXPECT_TRUE(client.is_enabled());
}

// Test DrtraceClient::log() - all log levels
TEST_F(DrtraceClientTest, LogAllLevels) {
  EXPECT_NO_THROW(client_->log(core::LogLevel::DEBUG, "Debug message"));
  EXPECT_NO_THROW(client_->log(core::LogLevel::INFO, "Info message"));
  EXPECT_NO_THROW(client_->log(core::LogLevel::WARN, "Warn message"));
  EXPECT_NO_THROW(client_->log(core::LogLevel::ERROR, "Error message"));
  EXPECT_NO_THROW(client_->log(core::LogLevel::CRITICAL, "Critical message"));
  
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::debug() - convenience method
TEST_F(DrtraceClientTest, DebugMethod) {
  EXPECT_NO_THROW(client_->debug("Debug message"));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::info() - convenience method
TEST_F(DrtraceClientTest, InfoMethod) {
  EXPECT_NO_THROW(client_->info("Info message"));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::warn() - convenience method
TEST_F(DrtraceClientTest, WarnMethod) {
  EXPECT_NO_THROW(client_->warn("Warn message"));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::error() - convenience method
TEST_F(DrtraceClientTest, ErrorMethod) {
  EXPECT_NO_THROW(client_->error("Error message"));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::critical() - convenience method
TEST_F(DrtraceClientTest, CriticalMethod) {
  EXPECT_NO_THROW(client_->critical("Critical message"));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::log() - with source location
TEST_F(DrtraceClientTest, LogWithSourceLocation) {
  EXPECT_NO_THROW(client_->error("Error with location", __FILE__, __LINE__));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::log() - without source location
TEST_F(DrtraceClientTest, LogWithoutSourceLocation) {
  EXPECT_NO_THROW(client_->info("Info without location"));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::log() - with temporary strings (memory safety)
TEST_F(DrtraceClientTest, LogWithTemporaryStrings) {
  // Test that temporary strings are safely copied
  auto get_filename = []() { return std::string("temp.cpp"); };
  auto get_function = []() { return std::string("temp_func"); };
  
  EXPECT_NO_THROW(client_->error("Error", get_filename().c_str(), 42, get_function().c_str()));
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::flush() - flushes pending records
TEST_F(DrtraceClientTest, FlushPendingRecords) {
  // Log multiple records
  for (int i = 0; i < 10; ++i) {
    client_->info("Message " + std::to_string(i));
  }
  
  // Flush should not throw
  EXPECT_NO_THROW(client_->flush());
}

// Test DrtraceClient::is_enabled() - returns correct state
TEST_F(DrtraceClientTest, IsEnabled) {
  EXPECT_TRUE(client_->is_enabled());
  
  // Create disabled client
  config_.enabled = false;
  DrtraceClient disabled_client(config_, "test");
  EXPECT_FALSE(disabled_client.is_enabled());
}

// Test DrtraceClient - disabled state (no-op)
TEST_F(DrtraceClientTest, DisabledState) {
  config_.enabled = false;
  DrtraceClient disabled_client(config_, "test");
  
  // Logging should not throw, but should be ignored
  EXPECT_NO_THROW(disabled_client.info("Should be ignored"));
  EXPECT_NO_THROW(disabled_client.flush());
}

// Test DrtraceClient - thread safety (concurrent logging)
TEST_F(DrtraceClientTest, ThreadSafety) {
  const int num_threads = 4;
  const int logs_per_thread = 10;
  
  std::vector<std::thread> threads;
  
  for (int t = 0; t < num_threads; ++t) {
    threads.emplace_back([this, t, logs_per_thread]() {
      for (int i = 0; i < logs_per_thread; ++i) {
        client_->info("Thread " + std::to_string(t) + " message " + std::to_string(i));
      }
    });
  }
  
  // Wait for all threads
  for (auto& thread : threads) {
    thread.join();
  }
  
  // Flush all records
  EXPECT_NO_THROW(client_->flush());
}

// Test edge case: Empty messages
TEST_F(DrtraceClientTest, EmptyMessage) {
  EXPECT_NO_THROW(client_->info(""));
  EXPECT_NO_THROW(client_->flush());
}

// Test edge case: Special characters in messages (JSON escaping)
TEST_F(DrtraceClientTest, SpecialCharactersInMessage) {
  EXPECT_NO_THROW(client_->error("Error: \"quotes\" 'apostrophes' \\backslash\\ \nnewline\t\ttab"));
  EXPECT_NO_THROW(client_->flush());
}

// Test edge case: Very long log messages
TEST_F(DrtraceClientTest, VeryLongMessage) {
  std::string long_message(10000, 'A');
  EXPECT_NO_THROW(client_->info(long_message));
  EXPECT_NO_THROW(client_->flush());
}

// Test edge case: Unicode characters
TEST_F(DrtraceClientTest, UnicodeCharacters) {
  EXPECT_NO_THROW(client_->info("Unicode: 你好世界 🌍 émojis 🚀"));
  EXPECT_NO_THROW(client_->flush());
}

// Test edge case: Rapid enable/disable toggling
TEST_F(DrtraceClientTest, RapidEnableDisable) {
  for (int i = 0; i < 5; ++i) {
    config_.enabled = (i % 2 == 0);
    client_ = std::make_unique<DrtraceClient>(config_, "test");
    
    EXPECT_NO_THROW(client_->info("Message during toggle " + std::to_string(i)));
  }
  
  EXPECT_NO_THROW(client_->flush());
}

// Test edge case: Destruction during active logging
TEST_F(DrtraceClientTest, DestructionDuringLogging) {
  // Log multiple records
  for (int i = 0; i < 10; ++i) {
    client_->info("Message " + std::to_string(i));
  }
  
  // Destroy client without explicit flush (should flush in destructor)
  client_.reset();
  
  // Should not crash or throw
  EXPECT_TRUE(true);
}

// Test edge case: Network failure during flush (graceful degradation)
TEST_F(DrtraceClientTest, NetworkFailureDuringFlush) {
  // Configure with invalid/unreachable daemon URL
  config_.daemon_url = "http://127.0.0.1:99999/logs/ingest";  // Invalid port
  config_.enabled = true;
  client_ = std::make_unique<DrtraceClient>(config_, "test");
  
  // Log multiple records
  for (int i = 0; i < 5; ++i) {
    EXPECT_NO_THROW(client_->info("Message " + std::to_string(i) + " (network will fail)"));
  }
  
  // Flush should complete without throwing (graceful degradation)
  EXPECT_NO_THROW(client_->flush());
  
  // System should still be usable after network failure
  EXPECT_TRUE(client_->is_enabled());
  
  // Should be able to log more records after failure
  EXPECT_NO_THROW(client_->info("Message after network failure"));
  EXPECT_NO_THROW(client_->flush());
}

