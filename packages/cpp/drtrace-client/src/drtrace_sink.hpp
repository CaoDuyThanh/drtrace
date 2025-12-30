/**
 * DrTrace C++ Client Integration
 *
 * A spdlog sink that enriches log records and sends them to the DrTrace daemon
 * via HTTP POST, matching the unified schema from Story 4.1.
 */

#pragma once

// Standard library includes required for header-only implementation
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <regex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

// libcurl for HTTP transport
#include <curl/curl.h>

// spdlog includes (optional - only needed for spdlog adapter)
// By default, try to detect spdlog availability (if headers are present)
// Users can explicitly disable with DRTRACE_DISABLE_SPDLOG
#ifndef DRTRACE_DISABLE_SPDLOG
  #if __has_include(<spdlog/spdlog.h>)
#include <spdlog/details/log_msg.h>
#include <spdlog/sinks/base_sink.h>
#include <spdlog/spdlog.h>
    #define DRTRACE_SPDLOG_AVAILABLE 1
  #else
    #define DRTRACE_SPDLOG_AVAILABLE 0
  #endif
#else
  // Explicitly disabled
  #define DRTRACE_SPDLOG_AVAILABLE 0
#endif

namespace drtrace {

// Log level enum - defined here for use in DrtraceConfig
// Also available via core::LogLevel (defined later as alias)
namespace core {
  enum class LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3,
    CRITICAL = 4
  };
}

/**
 * Parse log level from string (case-insensitive).
 * Returns DEBUG on invalid input (backward compatible).
 */
inline core::LogLevel parse_log_level(const char* str) {
  if (!str || str[0] == '\0') return core::LogLevel::DEBUG;

  std::string level(str);
  // Convert to lowercase
  for (auto& c : level) {
    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  }

  if (level == "debug") return core::LogLevel::DEBUG;
  if (level == "info") return core::LogLevel::INFO;
  if (level == "warn" || level == "warning") return core::LogLevel::WARN;
  if (level == "error") return core::LogLevel::ERROR;
  if (level == "critical") return core::LogLevel::CRITICAL;

  return core::LogLevel::DEBUG;  // Default on invalid input
}

/**
 * Configuration for the DrTrace C++ client.
 */
struct DrtraceConfig {
  std::string application_id;
  std::string daemon_url = "http://localhost:8001/logs/ingest";
  std::string service_name;
  bool enabled = true;
  size_t batch_size = 10;
  std::chrono::milliseconds flush_interval{5000};  // 5 seconds
  std::chrono::milliseconds circuit_reset_interval{30000};  // 30 seconds - circuit breaker cooldown

  /**
   * Maximum number of log records to buffer.
   * When exceeded, oldest logs are dropped (backpressure).
   * Set to 0 for unlimited (not recommended for production).
   * Default: 10000
   */
  size_t max_buffer_size = 10000;

  /**
   * Minimum log level to send to daemon.
   * Logs below this level are filtered at the client (not sent).
   * Default: DEBUG (send everything - backward compatible)
   */
  core::LogLevel min_level = core::LogLevel::DEBUG;

  /**
   * HTTP request timeout in milliseconds.
   * Default: 1000 (1 second)
   */
  std::chrono::milliseconds http_timeout{1000};

  /**
   * Base backoff time for retry attempts.
   * Actual backoff = base_backoff * attempt_number
   * Default: 100ms
   */
  std::chrono::milliseconds retry_backoff{100};

  /**
   * Maximum retry attempts for failed requests.
   * Default: 3
   */
  int max_retries = 3;

  /**
   * Load configuration from environment variables, with fallback to config file.
   *
   * Priority (highest to lowest):
   *   1. DRTRACE_APPLICATION_ID environment variable
   *   2. _drtrace/config.json file (application_id field)
   *
   * Required:
   *   - DRTRACE_APPLICATION_ID (env var) OR application_id in _drtrace/config.json
   *
   * Optional:
   *   - DRTRACE_DAEMON_URL (default: http://localhost:8001/logs/ingest)
   *   - DRTRACE_SERVICE_NAME
   *   - DRTRACE_ENABLED (default: true, set to "false" to disable)
   */
  static DrtraceConfig from_env();
};

namespace detail {
  // Reference counter for curl_global_init
  // curl_global_init is idempotent (safe to call multiple times)
  // We use reference counting to ensure it's initialized, but never call
  // curl_global_cleanup (should only be called at program termination)
  inline std::atomic<int>& curl_init_ref_count() {
    static std::atomic<int> count{0};
    return count;
  }
  
  inline std::mutex& curl_init_mutex() {
    static std::mutex mtx;
    return mtx;
  }
  
  // Initialize curl once (thread-safe, idempotent)
  inline void ensure_curl_initialized() {
    std::lock_guard<std::mutex> lock(curl_init_mutex());
    if (curl_init_ref_count().fetch_add(1) == 0) {
      curl_global_init(CURL_GLOBAL_DEFAULT);
    }
  }
}

/**
 * HTTP transport for sending log batches to the daemon.
 *
 * Uses libcurl for HTTP POST requests. Handles retries and errors
 * gracefully without throwing exceptions.
 */
class HttpTransport {
 public:
  inline explicit HttpTransport(const DrtraceConfig& config);
  inline ~HttpTransport();

  // Non-copyable
  HttpTransport(const HttpTransport&) = delete;
  HttpTransport& operator=(const HttpTransport&) = delete;

  /**
   * Send a batch of log records to the daemon.
   *
   * This method is thread-safe and handles network errors gracefully.
   * Returns true if the batch was sent successfully, false otherwise.
   *
   * Circuit Breaker Behavior:
   * - When daemon is unavailable, circuit opens and fast-fails (< 1µs)
   * - After circuit_reset_interval, one probe request is allowed
   * - On success, circuit closes; on failure, circuit stays open
   */
  inline bool send_batch(const std::vector<std::string>& log_records);

  /**
   * Check if circuit breaker is open (for testing).
   */
  bool is_circuit_open_for_test() const {
    return is_circuit_open();
  }

 private:
  std::string endpoint_;
  std::string application_id_;
  int max_retries_;
  std::chrono::milliseconds base_backoff_ms_;
  std::chrono::milliseconds http_timeout_;

  void* curl_handle_ = nullptr;  // CURL* handle

  // Thread safety: protect curl_handle_ access
  std::mutex curl_mutex_;
  std::atomic<bool> shutdown_flag_{false};

  // Circuit breaker state - atomic for thread safety
  // States: CLOSED (normal) -> OPEN (fast-fail) -> HALF-OPEN (probe) -> CLOSED/OPEN
  std::atomic<bool> circuit_open_{false};
  std::atomic<int64_t> circuit_open_until_ms_{0};
  std::chrono::milliseconds circuit_reset_interval_{30000};

  /**
   * Get current time in milliseconds since epoch.
   */
  int64_t now_ms() const {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()
    ).count();
  }

  /**
   * Check if circuit is open (should fast-fail).
   * Returns false if circuit is closed or cooldown has expired (half-open).
   */
  bool is_circuit_open() const {
    if (!circuit_open_.load(std::memory_order_acquire)) {
      return false;  // Fast path - circuit closed
    }
    // Check if cooldown expired (half-open state - allow probe request)
    if (now_ms() >= circuit_open_until_ms_.load(std::memory_order_acquire)) {
      return false;  // Allow probe request
    }
    return true;  // Fast-fail
  }

  /**
   * Open the circuit (daemon unavailable).
   * Sets cooldown timer to circuit_reset_interval from now.
   */
  void open_circuit() {
    circuit_open_until_ms_.store(
        now_ms() + circuit_reset_interval_.count(),
        std::memory_order_release
    );
    circuit_open_.store(true, std::memory_order_release);
  }

  /**
   * Close the circuit (daemon is available).
   */
  void close_circuit() {
    circuit_open_.store(false, std::memory_order_release);
  }

  // Wait for any in-flight operations to complete
  inline void wait_for_operations();
};

// =========================
// Core Components (spdlog-independent)
// =========================

namespace core {

// LogLevel enum is defined at the top of the drtrace namespace
// (before DrtraceConfig, so it can be used in config)
// core::LogLevel is available from there

/**
 * Source location information (optional).
 */
struct SourceLocation {
  std::string filename;  // Use std::string for memory safety (copies strings)
  int line = 0;
  std::string function;  // Use std::string for memory safety (copies strings)
};

/**
 * Log record structure (spdlog-independent).
 */
struct LogRecord {
  LogLevel level;
  std::string message;
  std::string logger_name;
  std::chrono::system_clock::time_point timestamp;
  SourceLocation source;
  
  // Additional context (optional)
  std::map<std::string, std::string> context;
};

/**
 * Core DrTrace logging engine (spdlog-independent).
 *
 * Handles:
 * - Serialization of LogRecord to JSON
 * - Batching records
 * - Flushing batches via HttpTransport
 * - Thread-safe operations
 */
class DrtraceCore {
 public:
  explicit DrtraceCore(const DrtraceConfig& config);
  ~DrtraceCore();

  // Non-copyable
  DrtraceCore(const DrtraceCore&) = delete;
  DrtraceCore& operator=(const DrtraceCore&) = delete;

  /**
   * Log a record (thread-safe).
   */
  void log(const LogRecord& record);

  /**
   * Flush pending records immediately.
   */
  void flush();

  /**
   * Check if enabled.
   */
  bool is_enabled() const { return config_.enabled; }

 private:
  const DrtraceConfig& config_;
  std::unique_ptr<HttpTransport> transport_;
  std::vector<std::string> batch_;  // JSON strings
  std::mutex batch_mutex_;
  
  // Flush thread management
  std::thread flush_thread_;
  std::mutex flush_mutex_;
  std::condition_variable flush_cv_;
  bool should_stop_ = false;
  bool flush_thread_running_ = false;

  /**
   * Serialize LogRecord to JSON string (unified schema).
   */
  std::string serialize_record(const LogRecord& record);

  /**
   * Escape JSON string.
   */
  std::string escape_json(const std::string& str);

  /**
   * Flush batch to daemon (internal, thread-safe).
   */
  void flush_internal();

  /**
   * Start background flush thread.
   */
  void start_flush_thread();

  /**
   * Stop background flush thread.
   */
  void stop_flush_thread();

  /**
   * Flush thread function.
   */
  void flush_thread_func();
};

}  // namespace core

// =========================
// spdlog Adapter (Optional - requires spdlog)
// =========================

#if DRTRACE_SPDLOG_AVAILABLE

/**
 * spdlog sink adapter for DrTrace.
 *
 * This sink converts spdlog log messages to core::LogRecord
 * and forwards them to DrtraceCore.
 *
 * API surface unchanged from previous implementation (for consistency).
 */
template <typename Mutex>
class DrtraceSink : public spdlog::sinks::base_sink<Mutex> {
 public:
  explicit DrtraceSink(const DrtraceConfig& config)
      : config_(config), core_(std::make_unique<core::DrtraceCore>(config)) {
  }

  ~DrtraceSink() {
    // Flush any remaining records
    this->flush_();
  }

 protected:
  void sink_it_(const spdlog::details::log_msg& msg) override {
    if (!core_ || !core_->is_enabled()) {
      return;
    }

    // Convert spdlog log_msg to core::LogRecord
    core::LogRecord record = convert_to_log_record(msg);
    
    // Delegate to core (thread-safe)
    core_->log(record);
  }

  void flush_() override {
    if (core_) {
      core_->flush();
    }
  }

 protected:
  /**
   * Convert spdlog log_msg to core::LogRecord.
   * Protected for testing purposes.
   */
  core::LogRecord convert_to_log_record(const spdlog::details::log_msg& msg) {
    core::LogRecord record;
    
    // Map spdlog level to core::LogLevel
    switch (msg.level) {
      case spdlog::level::trace:
      case spdlog::level::debug:
        record.level = core::LogLevel::DEBUG;
        break;
      case spdlog::level::info:
        record.level = core::LogLevel::INFO;
        break;
      case spdlog::level::warn:
        record.level = core::LogLevel::WARN;
        break;
      case spdlog::level::err:
        record.level = core::LogLevel::ERROR;
        break;
      case spdlog::level::critical:
        record.level = core::LogLevel::CRITICAL;
        break;
      default:
        record.level = core::LogLevel::INFO;
        break;
    }
    
    // Copy message and logger name
    record.message = std::string(msg.payload.data(), msg.payload.size());
    record.logger_name = std::string(msg.logger_name.data(), msg.logger_name.size());
    
    // Set timestamp
    record.timestamp = msg.time;
    
    // Set source location (copy strings from spdlog string views for memory safety)
    if (msg.source.filename) {
      record.source.filename = std::string(msg.source.filename);
    }
    record.source.line = msg.source.line;
    if (msg.source.funcname) {
      record.source.function = std::string(msg.source.funcname);
    }
    
    // Add thread ID to context
    std::ostringstream thread_id_str;
    thread_id_str << std::this_thread::get_id();
    record.context["thread_id"] = thread_id_str.str();
    
    return record;
  }

 private:
  DrtraceConfig config_;
  std::unique_ptr<core::DrtraceCore> core_;
};

// Convenience type aliases
using DrtraceSink_mt = DrtraceSink<std::mutex>;  // Multi-threaded
using DrtraceSink_st = DrtraceSink<spdlog::details::null_mutex>;  // Single-threaded

/**
 * Setup DrTrace integration for an existing spdlog logger.
 *
 * This adds a DrtraceSink to the logger without removing existing sinks.
 */
inline void setup_drtrace(std::shared_ptr<spdlog::logger> logger,
                          const DrtraceConfig& config);

/**
 * Create a new spdlog logger with DrTrace integration enabled.
 */
inline std::shared_ptr<spdlog::logger> create_drtrace_logger(
    const std::string& logger_name, const DrtraceConfig& config);

#endif  // DRTRACE_SPDLOG_AVAILABLE

// =========================
// Direct API (No spdlog required)
// =========================

/**
 * Direct DrTrace client API (no spdlog required).
 *
 * Usage:
 *   drtrace::DrtraceClient client(config);
 *   client.info("Application started");
 *   client.error("Something went wrong", __FILE__, __LINE__);
 */
class DrtraceClient {
 public:
  explicit DrtraceClient(const DrtraceConfig& config,
                        const std::string& logger_name = "default")
      : config_(config), logger_name_(logger_name),
        core_(std::make_unique<core::DrtraceCore>(config)) {
  }

  ~DrtraceClient() {
    // Flush any remaining records
    if (core_) {
      core_->flush();
    }
  }

  // Non-copyable
  DrtraceClient(const DrtraceClient&) = delete;
  DrtraceClient& operator=(const DrtraceClient&) = delete;

  /**
   * Log a message.
   *
   * @param level Log level
   * @param message Log message
   * @param filename Optional source filename (for __FILE__)
   * @param line Optional source line (for __LINE__)
   * @param function Optional function name (for __FUNCTION__)
   */
  void log(core::LogLevel level,
           const std::string& message,
           const char* filename = nullptr,
           int line = 0,
           const char* function = nullptr) {
    if (!core_ || !core_->is_enabled()) {
      return;
    }

    core::LogRecord record;
    record.level = level;
    record.message = message;
    record.logger_name = logger_name_;
    record.timestamp = std::chrono::system_clock::now();
    // Copy strings for memory safety (filename/function may be temporary)
    if (filename) {
      record.source.filename = filename;
    }
    record.source.line = line;
    if (function) {
      record.source.function = function;
    }
    
    // Add thread ID to context
    std::ostringstream thread_id_str;
    thread_id_str << std::this_thread::get_id();
    record.context["thread_id"] = thread_id_str.str();

    core_->log(record);
  }

  /**
   * Convenience methods for each log level.
   */
  void debug(const std::string& message,
             const char* filename = nullptr,
             int line = 0,
             const char* function = nullptr) {
    log(core::LogLevel::DEBUG, message, filename, line, function);
  }
  
  void info(const std::string& message,
            const char* filename = nullptr,
            int line = 0,
            const char* function = nullptr) {
    log(core::LogLevel::INFO, message, filename, line, function);
  }
  
  void warn(const std::string& message,
            const char* filename = nullptr,
            int line = 0,
            const char* function = nullptr) {
    log(core::LogLevel::WARN, message, filename, line, function);
  }
  
  void error(const std::string& message,
             const char* filename = nullptr,
             int line = 0,
             const char* function = nullptr) {
    log(core::LogLevel::ERROR, message, filename, line, function);
  }
  
  void critical(const std::string& message,
                const char* filename = nullptr,
                int line = 0,
                const char* function = nullptr) {
    log(core::LogLevel::CRITICAL, message, filename, line, function);
  }

  /**
   * Flush pending logs.
   */
  void flush() {
    if (core_) {
      core_->flush();
    }
  }

  /**
   * Check if enabled.
   */
  bool is_enabled() const {
    return core_ && core_->is_enabled();
  }

 private:
  DrtraceConfig config_;
  std::string logger_name_;
  std::unique_ptr<core::DrtraceCore> core_;
};

// =========================
// Inline Implementations
// =========================

namespace detail {

// Helper for libcurl write callback
struct WriteData {
  std::string data;
};

inline size_t WriteCallback(void* contents, size_t size, size_t nmemb,
                            void* userp) {
  size_t total_size = size * nmemb;
  WriteData* write_data = static_cast<WriteData*>(userp);
  write_data->data.append(static_cast<char*>(contents), total_size);
  return total_size;
}

/**
 * Read application_id from _drtrace/config.json file.
 *
 * This is a simple JSON parser that extracts the "application_id" field.
 * Returns empty string if file doesn't exist or field is not found.
 */
inline std::string read_application_id_from_config(const std::string& config_path) {
  std::ifstream file(config_path);
  if (!file.is_open()) {
    return "";
  }

  // Read entire file into a string
  std::string content((std::istreambuf_iterator<char>(file)),
                      std::istreambuf_iterator<char>());
  file.close();

  // Simple regex-based extraction for "application_id": "value"
  // Handles both "application_id" and "applicationId" (camelCase)
  std::regex pattern(
      R"delim("application_id"\s*:\s*"([^"]+)"|"applicationId"\s*:\s*"([^"]+)")delim");
  std::smatch match;

  if (std::regex_search(content, match, pattern)) {
    // Return the first non-empty capture group
    return match[1].matched ? match[1].str() : match[2].str();
  }

  // Also try nested drtrace.applicationId format
  std::regex nested_pattern(
      R"delim("drtrace"\s*:\s*\{[^}]*"applicationId"\s*:\s*"([^"]+)")delim");
  if (std::regex_search(content, match, nested_pattern)) {
    return match[1].str();
  }

  return "";
}

}  // namespace detail

// DrtraceConfig::from_env inline implementation
inline DrtraceConfig DrtraceConfig::from_env() {
  DrtraceConfig config;

  // Priority 1: Try environment variable first
  const char* app_id = std::getenv("DRTRACE_APPLICATION_ID");

  // Priority 2: Fall back to _drtrace/config.json if env var not set
  if (!app_id) {
    // Try to find config file relative to current working directory
    // Look for _drtrace/config.json in current directory
    std::string config_path = "_drtrace/config.json";
    std::string app_id_from_config =
        detail::read_application_id_from_config(config_path);

    if (!app_id_from_config.empty()) {
      config.application_id = app_id_from_config;
    } else {
      // Priority 3: Final fallback to default value (ensures application never crashes)
      // CRITICAL: Must use same default value as Python and JavaScript: "my-app"
      config.application_id = "my-app";
      // Optional: std::cerr << "Warning: Using default application_id 'my-app'. "
      //                     << "Set DRTRACE_APPLICATION_ID or _drtrace/config.json to customize." << std::endl;
    }
  } else {
    config.application_id = app_id;
  }

  const char* daemon_url = std::getenv("DRTRACE_DAEMON_URL");
  if (daemon_url) {
    config.daemon_url = daemon_url;
  }

  const char* service_name = std::getenv("DRTRACE_SERVICE_NAME");
  if (service_name) {
    config.service_name = service_name;
  }

  const char* enabled = std::getenv("DRTRACE_ENABLED");
  if (enabled && std::string(enabled) == "false") {
    config.enabled = false;
  }

  // Circuit breaker reset interval (milliseconds)
  const char* circuit_reset_ms = std::getenv("DRTRACE_CIRCUIT_RESET_MS");
  if (circuit_reset_ms) {
    try {
      long ms = std::stol(circuit_reset_ms);
      if (ms > 0) {
        config.circuit_reset_interval = std::chrono::milliseconds(ms);
      }
    } catch (...) {
      // Invalid value, use default
    }
  }

  // Maximum buffer size (backpressure)
  const char* max_buffer = std::getenv("DRTRACE_MAX_BUFFER_SIZE");
  if (max_buffer) {
    try {
      long size = std::stol(max_buffer);
      if (size >= 0) {
        config.max_buffer_size = static_cast<size_t>(size);
      }
    } catch (...) {
      // Invalid value, use default
    }
  }

  // Minimum log level (filtering)
  const char* min_level = std::getenv("DRTRACE_MIN_LEVEL");
  if (min_level) {
    config.min_level = parse_log_level(min_level);
  }

  // HTTP timeout (milliseconds)
  const char* http_timeout = std::getenv("DRTRACE_HTTP_TIMEOUT_MS");
  if (http_timeout) {
    try {
      long ms = std::stol(http_timeout);
      if (ms > 0) {
        config.http_timeout = std::chrono::milliseconds(ms);
      }
    } catch (...) {
      // Invalid value, use default
    }
  }

  // Retry backoff (milliseconds)
  const char* retry_backoff = std::getenv("DRTRACE_RETRY_BACKOFF_MS");
  if (retry_backoff) {
    try {
      long ms = std::stol(retry_backoff);
      if (ms > 0) {
        config.retry_backoff = std::chrono::milliseconds(ms);
      }
    } catch (...) {
      // Invalid value, use default
    }
  }

  // Max retries
  const char* max_retries = std::getenv("DRTRACE_MAX_RETRIES");
  if (max_retries) {
    try {
      int retries = std::stoi(max_retries);
      if (retries >= 0) {
        config.max_retries = retries;
      }
    } catch (...) {
      // Invalid value, use default
    }
  }

  return config;
}

// HttpTransport inline implementations
inline HttpTransport::HttpTransport(const DrtraceConfig& config)
    : endpoint_(config.daemon_url),
      application_id_(config.application_id),
      max_retries_(config.max_retries),
      base_backoff_ms_(config.retry_backoff),
      http_timeout_(config.http_timeout),
      circuit_reset_interval_(config.circuit_reset_interval) {
  // Ensure curl is initialized (thread-safe, idempotent)
  detail::ensure_curl_initialized();

  curl_handle_ = curl_easy_init();
  if (!curl_handle_) {
    std::cerr << "Warning: Failed to initialize libcurl for drtrace transport"
              << std::endl;
  }
}

inline void HttpTransport::wait_for_operations() {
  // Wait for any in-flight send_batch() operations to complete.
  // We use a short timeout and retry mechanism to avoid hanging
  // if a network operation is blocked.
  //
  // IMPORTANT: Even if this function times out, the destructor's lock_guard
  // will still block until the mutex is available. This ensures that:
  // 1. If operations complete quickly, we return early (optimization)
  // 2. If operations are slow, we don't wait forever (timeout protection)
  // 3. The destructor's lock_guard ensures operations complete before cleanup
  //
  // This design provides both performance (early return) and safety
  // (guaranteed wait via lock_guard).
  auto start = std::chrono::steady_clock::now();
  auto timeout = start + std::chrono::milliseconds(500);  // 500ms timeout
  
  while (std::chrono::steady_clock::now() < timeout) {
    // Try to acquire lock - if successful, no operations are in progress
    if (curl_mutex_.try_lock()) {
      curl_mutex_.unlock();
      return;  // No operations in progress
    }
    // Lock is held by send_batch(), wait a bit
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  
  // Timeout reached - operations may still be in progress, but we proceed anyway.
  // The destructor's lock_guard will still block until operations complete,
  // ensuring thread safety even if this timeout is reached.
}

inline HttpTransport::~HttpTransport() {
  // Shutdown sequence:
  // 1. Set shutdown flag to prevent new operations from starting
  shutdown_flag_.store(true);
  
  // 2. Wait for any in-flight send_batch() operations to complete
  //    (with timeout to prevent hanging if network I/O is blocked)
  wait_for_operations();
  
  // 3. Acquire mutex before cleanup. This lock_guard will block until
  //    any remaining operations release the mutex, ensuring curl_handle_
  //    is never accessed after cleanup begins.
  std::lock_guard<std::mutex> lock(curl_mutex_);
  
  // 4. Now safe to cleanup curl_handle_ (no operations can be using it)
  if (curl_handle_) {
    curl_easy_cleanup(curl_handle_);
    curl_handle_ = nullptr;
  }
  
  // Decrement reference count
  // Note: We don't call curl_global_cleanup here - it should only be called
  // at program termination, not in destructors. curl_global_init is idempotent
  // and safe to call multiple times, so leaving it initialized is fine.
  detail::curl_init_ref_count().fetch_sub(1);
}

inline bool HttpTransport::send_batch(
    const std::vector<std::string>& log_records) {
  // Shutdown flag check sequence:
  // 1. Check BEFORE acquiring lock (fast path - avoids lock acquisition if shutdown)
  if (shutdown_flag_.load()) {
    return false;
  }

  if (log_records.empty()) {
    return false;
  }

  // Circuit breaker fast-fail check (< 1 microsecond)
  // This is checked BEFORE any network operations to provide fast-fail behavior
  if (is_circuit_open()) {
    return false;  // Fast-fail - daemon known to be unavailable
  }

  // Build JSON payload matching Python client format
  std::ostringstream payload;
  payload << "{\"application_id\":\"" << application_id_ << "\",\"logs\":[";
  for (size_t i = 0; i < log_records.size(); ++i) {
    if (i > 0) {
      payload << ",";
    }
    payload << log_records[i];
  }
  payload << "]}";

  std::string payload_str = payload.str();

  // 2. Acquire lock to check and use curl_handle_
  //    This ensures only one thread accesses curl_handle_ at a time
  std::lock_guard<std::mutex> lock(curl_mutex_);

  // 3. Check AGAIN after acquiring lock (shutdown may have happened between checks)
  //    This double-check pattern prevents race conditions where shutdown happens
  //    between the first check and lock acquisition
  if (shutdown_flag_.load() || !curl_handle_) {
    return false;
  }

  // Setup curl request (all operations protected by mutex)
  curl_easy_reset(curl_handle_);
  curl_easy_setopt(curl_handle_, CURLOPT_URL, endpoint_.c_str());
  curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, payload_str.c_str());
  curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDSIZE, payload_str.length());

  struct curl_slist* headers = nullptr;
  headers = curl_slist_append(headers, "Content-Type: application/json");
  curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

  // Use configurable timeout (milliseconds)
  curl_easy_setopt(curl_handle_, CURLOPT_TIMEOUT_MS,
                   static_cast<long>(http_timeout_.count()));
  curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION,
                   detail::WriteCallback);

  detail::WriteData write_data;
  curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &write_data);

  // Retry loop
  for (int attempt = 1; attempt <= max_retries_; ++attempt) {
    // 4. Check shutdown flag before each retry attempt
    //    This allows long-running operations to exit early if shutdown occurs
    //    during network I/O (e.g., if curl_easy_perform() is slow)
    if (shutdown_flag_.load()) {
      curl_slist_free_all(headers);
      return false;
    }

    CURLcode res = curl_easy_perform(curl_handle_);
    if (res == CURLE_OK) {
      long response_code;
      curl_easy_getinfo(curl_handle_, CURLINFO_RESPONSE_CODE, &response_code);
      if (response_code >= 200 && response_code < 300) {
        // Success - close circuit (daemon is available)
        close_circuit();
        curl_slist_free_all(headers);
        return true;
      }
      // Non-2xx response - will retry or fail
    }

    if (attempt < max_retries_) {
      std::this_thread::sleep_for(base_backoff_ms_ * attempt);
    }
  }

  // All retries failed - open circuit (daemon unavailable)
  open_circuit();

  curl_slist_free_all(headers);
  return false;
}

#if DRTRACE_SPDLOG_AVAILABLE

// setup_drtrace and create_drtrace_logger inline implementations
inline void setup_drtrace(std::shared_ptr<spdlog::logger> logger,
                          const DrtraceConfig& config) {
  if (!config.enabled) {
    return;
  }

  auto sink = std::make_shared<DrtraceSink_mt>(config);
  logger->sinks().push_back(sink);
}

inline std::shared_ptr<spdlog::logger> create_drtrace_logger(
    const std::string& logger_name, const DrtraceConfig& config) {
  auto logger = spdlog::get(logger_name);
  if (logger) {
    return logger;
  }

  logger = std::make_shared<spdlog::logger>(logger_name);
  if (config.enabled) {
    auto sink = std::make_shared<DrtraceSink_mt>(config);
    logger->sinks().push_back(sink);
  }
  spdlog::register_logger(logger);
  return logger;
}

#endif  // DRTRACE_SPDLOG_AVAILABLE

// =========================
// Core Components Inline Implementations
// =========================

namespace core {

// DrtraceCore inline implementations
inline DrtraceCore::DrtraceCore(const DrtraceConfig& config)
    : config_(config), transport_(std::make_unique<HttpTransport>(config)), flush_thread_running_(false) {
  if (config_.enabled) {
    start_flush_thread();
  }
}

inline DrtraceCore::~DrtraceCore() {
  // Stop flush thread first (before flushing to avoid race conditions)
  if (flush_thread_running_) {
    stop_flush_thread();
  }
  // Flush any remaining records (after thread is stopped)
  flush();
}

inline void DrtraceCore::log(const LogRecord& record) {
  if (!config_.enabled) {
    return;
  }

  // Level filtering: skip logs below min_level
  if (record.level < config_.min_level) {
    return;
  }

  bool should_flush = false;
  {
    std::lock_guard<std::mutex> lock(batch_mutex_);

    // Backpressure: drop oldest log if buffer is full
    // This prevents OOM when daemon is unavailable or slow
    if (config_.max_buffer_size > 0 && batch_.size() >= config_.max_buffer_size) {
      batch_.erase(batch_.begin());  // Drop oldest
    }

    std::string json_record = serialize_record(record);
    batch_.push_back(std::move(json_record));

    // Check if batch size reached (flush outside lock)
    should_flush = (batch_.size() >= config_.batch_size);
  }

  // Flush outside the lock to avoid holding lock during network I/O
  if (should_flush) {
    flush_internal();
  }
}

inline void DrtraceCore::flush() {
  // flush_internal() manages its own locking - don't hold lock here
  flush_internal();
}

inline std::string DrtraceCore::escape_json(const std::string& str) {
    std::ostringstream escaped;
    for (char c : str) {
      switch (c) {
        case '"':
          escaped << "\\\"";
          break;
        case '\\':
          escaped << "\\\\";
          break;
        case '\b':
          escaped << "\\b";
          break;
        case '\f':
          escaped << "\\f";
          break;
        case '\n':
          escaped << "\\n";
          break;
        case '\r':
          escaped << "\\r";
          break;
        case '\t':
          escaped << "\\t";
          break;
        default:
          if (static_cast<unsigned char>(c) < 0x20) {
            escaped << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                    << static_cast<int>(c);
          } else {
            escaped << c;
          }
          break;
      }
    }
    return escaped.str();
  }

inline std::string DrtraceCore::serialize_record(const LogRecord& record) {
  std::ostringstream json;
  // Set precision to preserve fractional seconds (6 decimal places = microsecond precision)
  json << std::fixed << std::setprecision(6);

  // Get timestamp as Unix timestamp (seconds since epoch, with fractional seconds)
  auto ts_duration = record.timestamp.time_since_epoch();
  auto ts_seconds = std::chrono::duration_cast<std::chrono::seconds>(ts_duration);
  auto ts_fractional = std::chrono::duration_cast<std::chrono::milliseconds>(
      ts_duration - ts_seconds);
  double ts = ts_seconds.count() + (ts_fractional.count() / 1000.0);

  // Map LogLevel to string
  std::string level_str;
  switch (record.level) {
    case LogLevel::DEBUG:
      level_str = "debug";
      break;
    case LogLevel::INFO:
      level_str = "info";
      break;
    case LogLevel::WARN:
      level_str = "warn";
      break;
    case LogLevel::ERROR:
      level_str = "error";
      break;
    case LogLevel::CRITICAL:
      level_str = "critical";
      break;
  }

  json << "{"
       << "\"ts\":" << ts << ","
       << "\"level\":\"" << escape_json(level_str) << "\","
       << "\"message\":\"" << escape_json(record.message) << "\","
       << "\"application_id\":\"" << escape_json(config_.application_id) << "\","
       << "\"module_name\":\"" << escape_json(record.logger_name) << "\"";

  // Optional service_name
  if (!config_.service_name.empty()) {
    json << ",\"service_name\":\"" << escape_json(config_.service_name) << "\"";
  }

  // Optional file_path and line_no (check for empty strings instead of null pointers)
  if (!record.source.filename.empty()) {
    json << ",\"file_path\":\"" << escape_json(record.source.filename) << "\"";
  }
  if (record.source.line > 0) {
    json << ",\"line_no\":" << record.source.line;
  }

  // Context field
  json << ",\"context\":{"
       << "\"language\":\"cpp\"";
  // Add thread ID
  json << ",\"thread_id\":\"" << std::this_thread::get_id() << "\"";
  // Add any additional context
  for (const auto& [key, value] : record.context) {
    json << ",\"" << escape_json(key) << "\":\"" << escape_json(value) << "\"";
  }
  json << "}";

  json << "}";
  return json.str();
}

inline void DrtraceCore::flush_internal() {
  // RAII locking - manages its own lock, callers should NOT hold batch_mutex_
  std::vector<std::string> to_send;
  {
    std::lock_guard<std::mutex> lock(batch_mutex_);
    if (batch_.empty()) {
      return;
    }
    to_send.swap(batch_);
  }
  // Lock released here - safe to do network I/O without blocking other threads

  // Send batch (transport handles errors internally)
  if (transport_) {
    transport_->send_batch(to_send);
  }
}

inline void DrtraceCore::start_flush_thread() {
  flush_thread_running_ = true;
  flush_thread_ = std::thread([this]() {
    while (true) {
      std::unique_lock<std::mutex> lock(flush_mutex_);
      if (flush_cv_.wait_for(lock, config_.flush_interval,
                              [this] { return should_stop_; })) {
        break;  // Stop requested
      }
      lock.unlock();  // Release flush_mutex_ before calling flush_internal

      // flush_internal() manages batch_mutex_ internally - don't hold it here
      flush_internal();
    }
  });
}

inline void DrtraceCore::stop_flush_thread() {
  // Set stop flag
  {
    std::lock_guard<std::mutex> lock(flush_mutex_);
    should_stop_ = true;
  }
  // Notify flush thread to wake up and check stop flag
  flush_cv_.notify_one();

  // Always join - never detach to avoid use-after-free
  // The flush thread checks should_stop_ in its wait condition, so it will
  // exit promptly. The only delay is if send_batch() is in progress, which
  // is bounded by curl timeout and circuit breaker fast-fail.
  if (flush_thread_.joinable()) {
    flush_thread_.join();
  }

  flush_thread_running_ = false;
}

inline void DrtraceCore::flush_thread_func() {
  // This is handled by the lambda in start_flush_thread
  // Kept for consistency with architecture
}

}  // namespace core

}  // namespace drtrace

