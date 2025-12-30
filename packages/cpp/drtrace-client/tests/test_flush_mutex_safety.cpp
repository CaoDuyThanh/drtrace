/**
 * Mutex Safety Tests for DrTrace C++ Client
 *
 * Tests the thread-safe flush operations in DrtraceCore.
 * Ensures no deadlocks, race conditions, or mutex violations.
 */

#include <gtest/gtest.h>
#include <atomic>
#include <chrono>
#include <thread>
#include <vector>

#include "drtrace_sink.hpp"

namespace drtrace {
namespace testing {

/**
 * Test: Concurrent flush operations
 *
 * Multiple threads calling flush() concurrently should not cause
 * deadlocks or crashes.
 */
TEST(MutexSafety, ConcurrentFlushOperations) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.flush_interval = std::chrono::milliseconds(60000);  // Long interval (disable auto-flush)

  DrtraceClient client(config, "test-logger");

  std::vector<std::thread> threads;
  std::atomic<int> flush_count{0};

  // 10 threads calling flush concurrently
  for (int i = 0; i < 10; i++) {
    threads.emplace_back([&client, &flush_count]() {
      for (int j = 0; j < 100; j++) {
        client.flush();
        flush_count.fetch_add(1);
      }
    });
  }

  for (auto& t : threads) {
    t.join();
  }

  EXPECT_EQ(flush_count.load(), 1000);
  // No crashes, no deadlocks - if we get here, test passes
}

/**
 * Test: Concurrent log and flush operations
 *
 * One thread logging while another thread flushing should not cause
 * data races or deadlocks.
 */
TEST(MutexSafety, ConcurrentLogAndFlush) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.batch_size = 100;  // Large batch to avoid auto-flush during logging
  config.flush_interval = std::chrono::milliseconds(60000);  // Disable auto-flush

  DrtraceClient client(config, "test-logger");

  std::atomic<int> log_count{0};
  std::atomic<int> flush_count{0};

  std::thread logger([&client, &log_count]() {
    for (int i = 0; i < 1000; i++) {
      client.info("Message " + std::to_string(i));
      log_count.fetch_add(1);
    }
  });

  std::thread flusher([&client, &flush_count]() {
    for (int i = 0; i < 100; i++) {
      client.flush();
      flush_count.fetch_add(1);
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
  });

  logger.join();
  flusher.join();

  EXPECT_EQ(log_count.load(), 1000);
  EXPECT_EQ(flush_count.load(), 100);
  // No crashes, no data races - if we get here, test passes
}

/**
 * Test: Multiple loggers and flushers
 *
 * Multiple threads logging and flushing simultaneously should work correctly.
 */
TEST(MutexSafety, MultipleLoggersAndFlushers) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.batch_size = 50;
  config.flush_interval = std::chrono::milliseconds(60000);  // Disable auto-flush

  DrtraceClient client(config, "test-logger");

  std::vector<std::thread> threads;
  std::atomic<int> total_operations{0};

  // 4 logger threads
  for (int t = 0; t < 4; t++) {
    threads.emplace_back([&client, &total_operations, t]() {
      for (int i = 0; i < 250; i++) {
        client.info("Thread " + std::to_string(t) + " message " + std::to_string(i));
        total_operations.fetch_add(1);
      }
    });
  }

  // 2 flusher threads
  for (int t = 0; t < 2; t++) {
    threads.emplace_back([&client, &total_operations]() {
      for (int i = 0; i < 50; i++) {
        client.flush();
        total_operations.fetch_add(1);
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
      }
    });
  }

  for (auto& t : threads) {
    t.join();
  }

  // 4 loggers × 250 logs + 2 flushers × 50 flushes = 1100 operations
  EXPECT_EQ(total_operations.load(), 1100);
}

/**
 * Test: Rapid log with auto-flush
 *
 * Rapidly logging messages that trigger auto-flush (batch size reached)
 * should not cause deadlocks.
 */
TEST(MutexSafety, RapidLogWithAutoFlush) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.batch_size = 5;  // Small batch to trigger frequent auto-flushes
  config.flush_interval = std::chrono::milliseconds(60000);  // Disable timer-based flush

  DrtraceClient client(config, "test-logger");

  std::atomic<int> log_count{0};

  // Multiple threads logging rapidly
  std::vector<std::thread> threads;
  for (int t = 0; t < 4; t++) {
    threads.emplace_back([&client, &log_count]() {
      for (int i = 0; i < 100; i++) {
        client.info("Rapid message " + std::to_string(i));
        log_count.fetch_add(1);
      }
    });
  }

  for (auto& t : threads) {
    t.join();
  }

  client.flush();  // Final flush

  EXPECT_EQ(log_count.load(), 400);
  // No deadlocks - if we get here, test passes
}

/**
 * Test: Flush during shutdown
 *
 * Flushing while the client is being destroyed should not cause crashes.
 */
TEST(MutexSafety, FlushDuringShutdown) {
  std::atomic<bool> done{false};

  std::thread flusher;

  {
    DrtraceConfig config;
    config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
    config.application_id = "test-app";
    config.flush_interval = std::chrono::milliseconds(60000);

    DrtraceClient client(config, "test-logger");

    // Add some logs
    for (int i = 0; i < 50; i++) {
      client.info("Pre-shutdown message " + std::to_string(i));
    }

    // Start a flusher thread
    flusher = std::thread([&client, &done]() {
      while (!done.load()) {
        client.flush();
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
    });

    // Small delay to let flusher run
    std::this_thread::sleep_for(std::chrono::milliseconds(20));

    // Signal flusher to stop
    done.store(true);

    // Client destructor called here while flusher may still be running
  }

  // Wait for flusher to finish
  if (flusher.joinable()) {
    flusher.join();
  }

  // No crashes - if we get here, test passes
}

/**
 * Test: RAII lock guarantee
 *
 * Verify that locks are properly released even when operations complete early.
 */
TEST(MutexSafety, RAIILockGuarantee) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.batch_size = 100;
  config.flush_interval = std::chrono::milliseconds(60000);

  DrtraceClient client(config, "test-logger");

  // Flush empty batch (should return early without issues)
  for (int i = 0; i < 100; i++) {
    client.flush();
  }

  // Now log and flush
  client.info("Test message");
  client.flush();

  // If locks weren't properly released, this would deadlock
  client.info("Post-flush message");
  client.flush();

  // No deadlocks - if we get here, test passes
}

}  // namespace testing
}  // namespace drtrace
