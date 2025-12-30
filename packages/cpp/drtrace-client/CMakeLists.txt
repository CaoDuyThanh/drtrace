cmake_minimum_required(VERSION 3.14)
project(drtrace_cpp_client)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(CURL REQUIRED)
find_package(PkgConfig REQUIRED)

# Option to disable spdlog (for direct API only)
option(DRTRACE_DISABLE_SPDLOG "Disable spdlog support (direct API only)" OFF)

# Use FetchContent (needed for both spdlog and Google Test)
include(FetchContent)

# Fetch spdlog (only if not disabled)
if(NOT DRTRACE_DISABLE_SPDLOG)
FetchContent_Declare(
    spdlog-fetch
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG        v1.13.0
    GIT_SUBMODULES ""
)

FetchContent_MakeAvailable(spdlog-fetch)
endif()

## Header-only layout
## Note: The recommended integration pattern is now header-only.
## Consumers should:
##   - Copy src/drtrace_sink.hpp into their project (e.g., third_party/drtrace/drtrace_sink.hpp)
##   - Include the header and link against required dependencies:
##     * For spdlog adapter: spdlog::spdlog and CURL::libcurl
##     * For direct API: CURL::libcurl only (no spdlog required)
##
## The header supports two integration patterns:
##   1. spdlog adapter (DrtraceSink) - for projects using spdlog
##   2. Direct API (DrtraceClient) - for projects without spdlog
##
## This CMakeLists.txt is retained only to fetch spdlog via FetchContent
## and to allow advanced users to build a library if they wish to do so.

# Optional static library for advanced/legacy users
# Note: drtrace_sink.cpp is now a minimal stub (all implementation is in header)
# Only build library if spdlog is available (library requires spdlog for linking)
if(NOT DRTRACE_DISABLE_SPDLOG)
  add_library(drtrace_cpp_client STATIC
  src/drtrace_sink.cpp
)

target_include_directories(drtrace_cpp_client
  PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CURL_INCLUDE_DIRS}
)

target_link_libraries(drtrace_cpp_client
  PUBLIC
    spdlog::spdlog
    ${CURL_LIBRARIES}
)
endif()


# Install shared agent specs from root agents/ directory
# Agents are copied to share/drtrace/agents/ during installation
file(GLOB AGENT_FILES "../../agents/*.md")
if(AGENT_FILES)
  install(FILES ${AGENT_FILES}
    DESTINATION share/drtrace/agents
  )
endif()

# =========================
# Unit Tests
# =========================
option(BUILD_TESTS "Build unit tests" ON)
option(BUILD_COVERAGE "Build with code coverage" OFF)

if(BUILD_TESTS)
  enable_testing()
  
  # Use FetchContent to get Google Test
  FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
    GIT_SUBMODULES ""
  )
  
  FetchContent_MakeAvailable(googletest)
  
  # Coverage flags
  if(BUILD_COVERAGE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} --coverage -g -O0")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} --coverage")
  endif()
  
  # Test executable for core components
  add_executable(test_core tests/test_core.cpp)
  target_include_directories(test_core PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_core PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME CoreTests COMMAND test_core)
  
  # Test executable for DrtraceClient (no spdlog required)
  add_executable(test_client tests/test_client.cpp)
  target_include_directories(test_client PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_client PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME ClientTests COMMAND test_client)
  
  # Test executable for DrtraceSink (requires spdlog - only build if spdlog available)
  if(NOT DRTRACE_DISABLE_SPDLOG)
    # spdlog is available (fetched via FetchContent above)
    add_executable(test_sink tests/test_sink.cpp)
    target_include_directories(test_sink PRIVATE
      ${CMAKE_CURRENT_SOURCE_DIR}/src
    )
    target_link_libraries(test_sink PRIVATE
      GTest::gtest
      GTest::gtest_main
      spdlog::spdlog
      ${CURL_LIBRARIES}
    )
    add_test(NAME SinkTests COMMAND test_sink)
  endif()
  
  # Test executable for DrtraceConfig fallback behavior
  add_executable(test_config_fallback tests/test_config_fallback.cpp)
  target_include_directories(test_config_fallback PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_config_fallback PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME ConfigFallbackTests COMMAND test_config_fallback)
  
  # Test executable for HttpTransport thread safety (CRITICAL - prevents segfault bug)
  add_executable(test_http_transport_thread_safety tests/test_http_transport_thread_safety.cpp)
  target_include_directories(test_http_transport_thread_safety PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_http_transport_thread_safety PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME HttpTransportThreadSafetyTests COMMAND test_http_transport_thread_safety)

  # Test executable for circuit breaker pattern
  add_executable(test_circuit_breaker tests/test_circuit_breaker.cpp)
  target_include_directories(test_circuit_breaker PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_circuit_breaker PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME CircuitBreakerTests COMMAND test_circuit_breaker)

  # Test executable for flush mutex safety (RAII locking verification)
  add_executable(test_flush_mutex_safety tests/test_flush_mutex_safety.cpp)
  target_include_directories(test_flush_mutex_safety PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_flush_mutex_safety PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME FlushMutexSafetyTests COMMAND test_flush_mutex_safety)

  # Test executable for thread lifecycle (clean shutdown, no use-after-free)
  add_executable(test_thread_lifecycle tests/test_thread_lifecycle.cpp)
  target_include_directories(test_thread_lifecycle PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_thread_lifecycle PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME ThreadLifecycleTests COMMAND test_thread_lifecycle)

  # Test executable for backpressure (bounded memory usage)
  add_executable(test_backpressure tests/test_backpressure.cpp)
  target_include_directories(test_backpressure PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_backpressure PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME BackpressureTests COMMAND test_backpressure)

  # Test executable for log level filtering
  add_executable(test_level_filtering tests/test_level_filtering.cpp)
  target_include_directories(test_level_filtering PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_level_filtering PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME LevelFilteringTests COMMAND test_level_filtering)

  # Test executable for configurable timeouts
  add_executable(test_configurable_timeouts tests/test_configurable_timeouts.cpp)
  target_include_directories(test_configurable_timeouts PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_configurable_timeouts PRIVATE
    GTest::gtest
    GTest::gtest_main
    ${CURL_LIBRARIES}
  )
  add_test(NAME ConfigurableTimeoutsTests COMMAND test_configurable_timeouts)

  # Test program for timestamp fix verification
  add_executable(test_timestamp_fix tests/test_timestamp_fix.cpp)
  target_include_directories(test_timestamp_fix PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_link_libraries(test_timestamp_fix PRIVATE
    ${CURL_LIBRARIES}
    pthread
  )
  
  # Coverage target
if(BUILD_COVERAGE)
  find_program(LCOV_PATH lcov)
  find_program(GENHTML_PATH genhtml)
  
  if(LCOV_PATH AND GENHTML_PATH)
    # Build list of test targets (conditionally include test_sink)
    set(COVERAGE_TEST_TARGETS test_core test_client)
    if(NOT DRTRACE_DISABLE_SPDLOG)
      list(APPEND COVERAGE_TEST_TARGETS test_sink)
    endif()
    
    add_custom_target(coverage
      COMMAND ${LCOV_PATH} --directory . --capture --output-file coverage.info
      COMMAND ${LCOV_PATH} --remove coverage.info '/usr/*' '*/tests/*' '*/googletest/*' --output-file coverage.info
      COMMAND ${GENHTML_PATH} coverage.info --output-directory coverage_report
      COMMAND ${CMAKE_COMMAND} -E echo "Coverage report generated in coverage_report/index.html"
      WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
      DEPENDS ${COVERAGE_TEST_TARGETS}
    )
  endif()
endif()
endif()

