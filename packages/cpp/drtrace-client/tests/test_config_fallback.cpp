/**
 * Unit tests for DrtraceConfig::from_env() fallback behavior.
 * 
 * Tests:
 * - Fallback to "my-app" when application_id is missing
 * - Environment variable override
 * - Config file reading
 * - Consistency with Python and JavaScript default value
 */

#include <gtest/gtest.h>
#include <cstdlib>
#include <fstream>
#include <filesystem>
#include "../src/drtrace_sink.hpp"

#ifdef _WIN32
#include <windows.h>
#define unsetenv(name) SetEnvironmentVariableA(name, nullptr)
#define setenv(name, value, overwrite) SetEnvironmentVariableA(name, value)
#else
#include <unistd.h>
#endif

using namespace drtrace;

class DrtraceConfigFallbackTest : public ::testing::Test {
 protected:
  void SetUp() override {
    // Save original environment variables
    original_app_id_ = std::getenv("DRTRACE_APPLICATION_ID");
    original_daemon_url_ = std::getenv("DRTRACE_DAEMON_URL");
    
    // Clear environment variables
    unsetenv("DRTRACE_APPLICATION_ID");
    unsetenv("DRTRACE_DAEMON_URL");
    
    // Create temporary directory for config file
    temp_dir_ = std::filesystem::temp_directory_path() / "drtrace_test_config";
    std::filesystem::create_directories(temp_dir_);
    
    // Change to temp directory
    original_cwd_ = std::filesystem::current_path();
    std::filesystem::current_path(temp_dir_);
  }
  
  void TearDown() override {
    // Restore original working directory
    std::filesystem::current_path(original_cwd_);
    
    // Clean up temp directory
    std::filesystem::remove_all(temp_dir_);
    
    // Restore environment variables
    if (original_app_id_) {
      setenv("DRTRACE_APPLICATION_ID", original_app_id_, 1);
    } else {
      unsetenv("DRTRACE_APPLICATION_ID");
    }
    
    if (original_daemon_url_) {
      setenv("DRTRACE_DAEMON_URL", original_daemon_url_, 1);
    } else {
      unsetenv("DRTRACE_DAEMON_URL");
    }
  }
  
  void CreateConfigFile(const std::string& application_id) {
    std::filesystem::create_directories("_drtrace");
    std::ofstream config_file("_drtrace/config.json");
    config_file << R"({"application_id": ")" << application_id << R"("})";
    config_file.close();
  }
  
  void RemoveConfigFile() {
    std::filesystem::remove_all("_drtrace");
  }
  
  const char* original_app_id_;
  const char* original_daemon_url_;
  std::filesystem::path temp_dir_;
  std::filesystem::path original_cwd_;
};

// Test Case 1: No env var, no config file - should fallback to "my-app"
TEST_F(DrtraceConfigFallbackTest, FallbackToDefaultWhenMissing) {
  RemoveConfigFile();
  
  // Should not throw exception, should use default "my-app"
  DrtraceConfig config;
  EXPECT_NO_THROW({
    config = DrtraceConfig::from_env();
  });
  
  EXPECT_EQ(config.application_id, "my-app");
}

// Test Case 2: Env var override - should use env var value
TEST_F(DrtraceConfigFallbackTest, EnvVarOverride) {
  RemoveConfigFile();
  setenv("DRTRACE_APPLICATION_ID", "test-app", 1);
  
  DrtraceConfig config = DrtraceConfig::from_env();
  EXPECT_EQ(config.application_id, "test-app");
  
  unsetenv("DRTRACE_APPLICATION_ID");
}

// Test Case 3: Config file present - should use config file value
TEST_F(DrtraceConfigFallbackTest, ConfigFileFallback) {
  CreateConfigFile("artos");
  unsetenv("DRTRACE_APPLICATION_ID");
  
  DrtraceConfig config = DrtraceConfig::from_env();
  EXPECT_EQ(config.application_id, "artos");
}

// Test Case 4: Env var takes precedence over config file
TEST_F(DrtraceConfigFallbackTest, EnvVarTakesPrecedenceOverConfigFile) {
  CreateConfigFile("artos");
  setenv("DRTRACE_APPLICATION_ID", "env-override", 1);
  
  DrtraceConfig config = DrtraceConfig::from_env();
  EXPECT_EQ(config.application_id, "env-override");
  
  unsetenv("DRTRACE_APPLICATION_ID");
}

// Test Case 5: Consistency test - verify default value matches Python/JavaScript
TEST_F(DrtraceConfigFallbackTest, ConsistencyWithOtherLanguages) {
  RemoveConfigFile();
  
  DrtraceConfig config = DrtraceConfig::from_env();
  // CRITICAL: Must use same default value as Python and JavaScript: "my-app"
  EXPECT_EQ(config.application_id, "my-app");
}

// Test Case 6: Empty config file - should fallback to default
TEST_F(DrtraceConfigFallbackTest, EmptyConfigFileFallback) {
  std::filesystem::create_directories("_drtrace");
  std::ofstream config_file("_drtrace/config.json");
  config_file << R"({})";
  config_file.close();
  
  DrtraceConfig config = DrtraceConfig::from_env();
  EXPECT_EQ(config.application_id, "my-app");
}

// Test Case 7: Invalid JSON config file - should fallback to default
TEST_F(DrtraceConfigFallbackTest, InvalidConfigFileFallback) {
  std::filesystem::create_directories("_drtrace");
  std::ofstream config_file("_drtrace/config.json");
  config_file << R"({invalid json})";
  config_file.close();
  
  DrtraceConfig config = DrtraceConfig::from_env();
  EXPECT_EQ(config.application_id, "my-app");
}

