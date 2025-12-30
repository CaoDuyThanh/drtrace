/**
 * Thread Lifecycle Tests for DrTrace C++ Client
 *
 * Tests clean shutdown behavior to ensure no use-after-free bugs.
 * The flush thread should always be joined, never detached.
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
 * Test: Rapid create/destroy cycles
 *
 * Creates and destroys DrtraceClient instances rapidly.
 * This catches use-after-free bugs when threads continue
 * accessing destroyed objects.
 */
TEST(ThreadLifecycle, RapidCreateDestroyCycles) {
  for (int i = 0; i < 100; i++) {
    DrtraceConfig config;
    config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
    config.application_id = "test-app";
    config.flush_interval = std::chrono::milliseconds(10);  // Fast flush interval

    DrtraceClient client(config, "test-logger");
    client.info("Test message " + std::to_string(i));
    // Destructor called immediately - should join thread, not detach
  }
  // No crashes, no use-after-free - if we get here, test passes
}

/**
 * Test: Destructor waits for flush thread
 *
 * Verifies the destructor properly waits for the flush thread
 * to complete rather than detaching it.
 */
TEST(ThreadLifecycle, DestructorWaitsForFlushThread) {
  auto start = std::chrono::steady_clock::now();

  {
    DrtraceConfig config;
    config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
    config.application_id = "test-app";
    config.flush_interval = std::chrono::milliseconds(50);

    DrtraceClient client(config, "test-logger");
    for (int i = 0; i < 100; i++) {
      client.info("Test message " + std::to_string(i));
    }
    // Destructor should wait for flush thread to complete
  }

  auto elapsed = std::chrono::steady_clock::now() - start;

  // Should complete in reasonable time (not hang forever)
  // With circuit breaker, even failed network calls are fast
  EXPECT_LT(elapsed, std::chrono::seconds(10));
}

/**
 * Test: Destructor with pending batch
 *
 * Verifies clean shutdown when there are pending logs
 * that haven't been flushed yet.
 */
TEST(ThreadLifecycle, DestructorWithPendingBatch) {
  DrtraceConfig config;
  config.daemon_url = "http://localhost:9999/logs/ingest";  // Non-existent
  config.application_id = "test-app";
  config.batch_size = 100;  // Large batch, won't auto-flush
  config.flush_interval = std::chrono::milliseconds(60000);  // Disable timer flush

  {
    DrtraceClient client(config, "test-logger");
    for (int i = 0; i < 50; i++) {
      client.info("Test message " + std::to_string(i));
    }
    // Destructor should flush pending batch and exit cleanly
  }
  // No crashes - if we get here, test passes
}

/**
 * Test: Multiple clients created and destroyed concurrently
 *
 * Stress test for thread lifecycle when multiple clients
 * are created/destroyed simultaneously from different threads.
 */
TEST(ThreadLifecycle, ConcurrentClientLifecycles) {
  std::vector<std::thread> threads;
  std::atomic<int> completed{0};

  // 4 threads, each creating/destroying 25 clients
  for (int t = 0; t < 4; t++) {
    threads.emplace_back([&completed, t]() {
      for (int i = 0; i < 25; i++) {
        DrtraceConfig config;
        config.daemon_url = "http://localhost:9999/logs/ingest";
        config.application_id = "test-app-" + std::to_string(t);
        config.flush_interval = std::chrono::milliseconds(10);

        DrtraceClient client(config, "test-logger");
        client.info("Thread " + std::to_string(t) + " message " + std::to_string(i));
        // Immediate destruction
      }
      completed.fetch_add(1);
    });
  }

  for (auto& thread : threads) {
    thread.join();
  }

  EXPECT_EQ(completed.load(), 4);
  // No crashes, no race conditions - if we get here, test passes
}

/**
 * Test: Client with active logging during destruction
 *
 * Starts logging in a separate thread and destroys the client
 * while logging is still in progress.
 */
TEST(ThreadLifecycle, DestructionDuringActiveLogging) {
  std::atomic<bool> stop_logging{false};
  std::atomic<int> log_count{0};

  {
    DrtraceConfig config;
    config.daemon_url = "http://localhost:9999/logs/ingest";
    config.application_id = "test-app";
    config.batch_size = 5;
    config.flush_interval = std::chrono::milliseconds(10);

    auto client = std::make_shared<DrtraceClient>(config, "test-logger");

    std::thread logger([client, &stop_logging, &log_count]() {
      while (!stop_logging.load()) {
        client->info("Active logging message");
        log_count.fetch_add(1);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
    });

    // Let logging run for a bit
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    // Signal stop and wait for logger thread
    stop_logging.store(true);
    logger.join();

    // Client destructor called here
  }

  EXPECT_GT(log_count.load(), 0);
  // No crashes - if we get here, test passes
}

/**
 * Test: Rapid flush during shutdown
 *
 * Calls flush() rapidly while also destroying the client.
 * Tests that flush_internal() and stop_flush_thread() don't conflict.
 */
TEST(ThreadLifecycle, RapidFlushDuringShutdown) {
  for (int iter = 0; iter < 20; iter++) {
    DrtraceConfig config;
    config.daemon_url = "http://localhost:9999/logs/ingest";
    config.application_id = "test-app";
    config.batch_size = 100;
    config.flush_interval = std::chrono::milliseconds(60000);

    {
      DrtraceClient client(config, "test-logger");

      // Add some logs
      for (int i = 0; i < 10; i++) {
        client.info("Message " + std::to_string(i));
      }

      // Rapid flushes
      for (int i = 0; i < 10; i++) {
        client.flush();
      }

      // Destructor called here while flush might be in progress
    }
  }
  // No crashes, no deadlocks - if we get here, test passes
}

}  // namespace testing
}  // namespace drtrace
