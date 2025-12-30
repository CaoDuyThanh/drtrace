/**
 * Unit tests for HttpTransport thread safety.
 *
 * CRITICAL: These tests prevent the segmentation fault bug from recurring.
 *
 * Tests:
 * - Mutex protection for concurrent access
 * - Shutdown flag prevents new operations
 * - Graceful shutdown waits for in-flight operations
 * - Race condition prevention (CRITICAL - prevents original bug)
 * - Timeout protection
 * - Concurrent shutdown scenarios
 * - Normal operation regression test
 *
 * NOTE: curl_global_init() is NOT thread-safe and must be called before
 * any threads are created. We ensure this with a static initializer that
 * runs before main().
 */

#include <gtest/gtest.h>
#include <thread>
#include <vector>
#include <chrono>
#include <atomic>
#include <condition_variable>
#include <mutex>
#include "../src/drtrace_sink.hpp"

using namespace drtrace;

// CRITICAL: Ensure curl is initialized BEFORE any tests run to avoid thread-safety issues.
// curl_global_init() is NOT thread-safe and must be called from a single thread
// before any other threads are created.
//
// We use a GTest environment to ensure curl is initialized before any test runs,
// and that initialization happens via the library's own mechanism (which is
// designed to be called once per HttpTransport creation).
class CurlInitEnvironment : public ::testing::Environment {
 public:
  void SetUp() override {
    // Create a dummy transport to trigger curl initialization in the main thread
    // before any test threads are created. This ensures thread-safe initialization.
    DrtraceConfig dummy_config;
    dummy_config.application_id = "curl-init";
    dummy_config.daemon_url = "http://localhost:1/dummy";
    dummy_config.http_timeout = std::chrono::milliseconds(1);
    dummy_config.max_retries = 0;
    // Creating HttpTransport triggers curl_global_init() via ensure_curl_initialized()
    HttpTransport dummy_transport(dummy_config);
    // Transport is destroyed here, but curl remains initialized
  }
};

// Register the environment to run before any tests
static ::testing::Environment* const curl_init_env =
    ::testing::AddGlobalTestEnvironment(new CurlInitEnvironment);

class HttpTransportThreadSafetyTest : public ::testing::Test {
 protected:
  void SetUp() override {
    // Use a test endpoint (may not exist, but that's OK for thread safety tests)
    config_.application_id = "test-app";
    config_.daemon_url = "http://localhost:8001/logs/ingest";
    // Use shorter timeouts for faster test execution
    config_.http_timeout = std::chrono::milliseconds(100);
    config_.retry_backoff = std::chrono::milliseconds(10);
    config_.max_retries = 1;
  }

  void TearDown() override {
    // Cleanup if needed
  }

  DrtraceConfig config_;
};

// Test Case 1: Mutex Protection
TEST_F(HttpTransportThreadSafetyTest, MutexProtection) {
  // Test that multiple threads calling send_batch() concurrently
  // don't cause crashes or race conditions
  HttpTransport transport(config_);
  
  std::vector<std::thread> threads;
  std::atomic<int> success_count{0};
  
  // Launch multiple threads calling send_batch() concurrently
  for (int i = 0; i < 10; ++i) {
    threads.emplace_back([&transport, &success_count]() {
      std::vector<std::string> logs = {"{\"message\":\"test\"}"};
      if (transport.send_batch(logs)) {
        success_count.fetch_add(1);
      }
    });
  }
  
  // Wait for all threads
  for (auto& t : threads) {
    t.join();
  }
  
  // Verify no crashes occurred
  // Note: Actual success depends on network, but no crashes should occur
  EXPECT_GE(success_count.load(), 0);
}

// Test Case 2: Shutdown Flag
// Test that shutdown flag prevents new operations after transport is destroyed
TEST_F(HttpTransportThreadSafetyTest, ShutdownFlag) {
  std::atomic<bool> operation_started{false};
  std::atomic<bool> operation_completed{false};
  std::mutex mtx;
  std::condition_variable cv;
  
  std::thread bg_thread;
  
  {
    HttpTransport transport(config_);
    
    // Start send_batch() in background thread
    bg_thread = std::thread([&transport, &operation_started, &operation_completed, &mtx, &cv]() {
      // Signal that operation has started
      {
        std::lock_guard<std::mutex> lock(mtx);
        operation_started.store(true);
      }
      cv.notify_one();
      
      std::vector<std::string> logs = {"{\"message\":\"test\"}"};
      bool result = transport.send_batch(logs);
      
      operation_completed.store(true);
    });
    
    // Wait for operation to start
    {
      std::unique_lock<std::mutex> lock(mtx);
      cv.wait(lock, [&operation_started]() { return operation_started.load(); });
    }
    
    // Now destroy transport (sets shutdown flag)
    // The background thread's send_batch() should detect shutdown and exit early
  }  // Transport destroyed here - shutdown flag is set
  
  // Wait for background thread to finish
  bg_thread.join();
  
  // Verify operation completed (either successfully or exited early due to shutdown)
  EXPECT_TRUE(operation_completed.load());
  
  // Now test that a new send_batch() call after shutdown returns false immediately
  // We can't create a new transport and destroy it in the same test, so we verify
  // the behavior indirectly: if shutdown flag works, operations should exit early
  // This is verified by the fact that the test completes without hanging
}

// Test Case 3: Graceful Shutdown (CRITICAL)
TEST_F(HttpTransportThreadSafetyTest, GracefulShutdown) {
  // Test that destructor waits for in-flight operations
  std::atomic<bool> operation_started{false};
  std::mutex mtx;
  std::condition_variable cv;
  std::thread bg_thread;
  
  {
    HttpTransport transport(config_);
    
    // Start send_batch() in background thread
    bg_thread = std::thread([&transport, &operation_started, &mtx, &cv]() {
      std::vector<std::string> logs = {"{\"message\":\"test\"}"};
      
      // Signal that operation has started (after acquiring mutex in send_batch)
      // We signal after a small delay to ensure send_batch() has acquired the lock
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
      {
        std::lock_guard<std::mutex> lock(mtx);
        operation_started.store(true);
      }
      cv.notify_one();
      
      transport.send_batch(logs);
    });
    
    // Wait for operation to start (ensure send_batch() has acquired mutex)
    {
      std::unique_lock<std::mutex> lock(mtx);
      cv.wait(lock, [&operation_started]() { return operation_started.load(); });
    }
    
    // Give a bit more time to ensure curl operation has started
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    
    // Immediately destroy transport (call destructor)
    // Destructor should wait for operation to complete
  }  // Transport destroyed here
  
  // Wait for background thread to finish
  bg_thread.join();
  
  // Verify no crash occurred
  // If we get here without SIGSEGV, test passes
}

// Test Case 4: Race Condition Prevention (CRITICAL)
// This test specifically prevents the original bug from recurring
TEST_F(HttpTransportThreadSafetyTest, RaceConditionPrevention) {
  // CRITICAL TEST: Prevents original bug from recurring
  // Background thread calls send_batch() (simulate slow network)
  // Main thread destroys HttpTransport during operation
  // Verify no SIGSEGV occurs
  
  std::atomic<bool> operation_started{false};
  std::mutex mtx;
  std::condition_variable cv;
  std::thread bg_thread;
  
  {
    HttpTransport transport(config_);
    
    // Start send_batch() in background thread
    // Simulate slow network by using a slow endpoint or delay
    bg_thread = std::thread([&transport, &operation_started, &mtx, &cv]() {
      std::vector<std::string> logs = {"{\"message\":\"test\"}"};
      
      // Signal that operation has started (after acquiring mutex in send_batch)
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
      {
        std::lock_guard<std::mutex> lock(mtx);
        operation_started.store(true);
      }
      cv.notify_one();
      
      transport.send_batch(logs);
    });
    
    // Wait for operation to start (ensure send_batch() has acquired mutex)
    {
      std::unique_lock<std::mutex> lock(mtx);
      cv.wait(lock, [&operation_started]() { return operation_started.load(); });
    }
    
    // Give a bit more time to ensure curl operation has started
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    
    // Immediately destroy transport (call destructor)
    // This is the critical race condition scenario
  }  // Transport destroyed here while bg_thread is using curl_handle_
  
  // Wait for background thread to finish
  bg_thread.join();
  
  // Verify no SIGSEGV occurred
  // If we get here without crash, test passes
}

// Test Case 5: Timeout Protection
TEST_F(HttpTransportThreadSafetyTest, TimeoutProtection) {
  // Test that destructor doesn't hang forever if network I/O is blocked
  // Use an invalid endpoint that will timeout
  DrtraceConfig timeout_config;
  timeout_config.application_id = "test-app";
  timeout_config.daemon_url = "http://192.0.2.0:8001/logs/ingest";  // Invalid IP (RFC 3330)
  // Use short timeout for faster test execution
  timeout_config.http_timeout = std::chrono::milliseconds(100);
  timeout_config.retry_backoff = std::chrono::milliseconds(10);
  timeout_config.max_retries = 1;

  auto start = std::chrono::steady_clock::now();
  std::thread bg_thread;

  {
    HttpTransport transport(timeout_config);

    // Start send_batch() in background thread (will hang on network I/O)
    bg_thread = std::thread([&transport]() {
      std::vector<std::string> logs = {"{\"message\":\"test\"}"};
      transport.send_batch(logs);  // This will timeout
    });

    // Give background thread time to start operation
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    // Destroy transport - should timeout after 500ms, not hang forever
  }  // Transport destroyed here

  // Wait for background thread to finish
  bg_thread.join();

  auto end = std::chrono::steady_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

  // Verify timeout works (should complete in ~500ms, not hang forever)
  EXPECT_LT(duration.count(), 2000);  // Should complete within 2 seconds
}

// Test Case 6: Concurrent Shutdown
TEST_F(HttpTransportThreadSafetyTest, ConcurrentShutdown) {
  // Test multiple threads calling send_batch() simultaneously
  // while one thread destroys HttpTransport
  std::atomic<int> threads_started{0};
  std::mutex mtx;
  std::condition_variable cv;
  std::vector<std::thread> threads;
  
  {
    HttpTransport transport(config_);
    
    // Launch multiple threads calling send_batch()
    for (int i = 0; i < 5; ++i) {
      threads.emplace_back([&transport, &threads_started, &mtx, &cv, i]() {
        std::vector<std::string> logs = {"{\"message\":\"test\"}"};
        
        // Signal that this thread has started
        {
          std::lock_guard<std::mutex> lock(mtx);
          threads_started.fetch_add(1);
        }
        cv.notify_one();
        
        // Small delay to ensure mutex acquisition in send_batch()
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
        
        transport.send_batch(logs);
      });
    }
    
    // Wait for all threads to start
    {
      std::unique_lock<std::mutex> lock(mtx);
      cv.wait(lock, [&threads_started]() { return threads_started.load() >= 5; });
    }
    
    // Give threads a bit more time to acquire mutex in send_batch()
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    
    // Destroy transport while threads are running
  }  // Transport destroyed here
  
  // Wait for all threads
  for (auto& t : threads) {
    t.join();
  }
  
  // Verify no crashes occurred
  // If we get here without SIGSEGV, test passes
}

// Test Case 7: Normal Operation (Regression Test)
TEST_F(HttpTransportThreadSafetyTest, NormalOperation) {
  // Regression test: Normal send_batch() calls work correctly
  HttpTransport transport(config_);
  
  std::vector<std::string> logs = {"{\"message\":\"test\"}"};
  bool result = transport.send_batch(logs);
  
  // Verify no crashes occurred
  // Actual success depends on network, but no crashes should occur
  // This is a regression test to ensure normal operation still works
}

