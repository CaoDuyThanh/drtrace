# C++ ROS Integration Guide

This guide shows how to integrate DrTrace with ROS (Robot Operating System) projects using Pattern 2 (Direct API).

## Overview

DrTrace Direct API works alongside ROS logging without requiring spdlog. This allows you to:
- Keep using ROS logging (`ROS_INFO`, `ROS_ERROR`, etc.) for ROS-specific messages
- Use DrTrace for application-level structured logging
- No need to add spdlog or create bridges/adapters

## Integration Pattern

**Pattern Used:** Pattern 2 (Direct API - no spdlog required)

### CMake Setup

```cmake
# Add after cmake_minimum_required and project(...) definition.
# Header file should already be copied to third_party/drtrace/drtrace_sink.hpp

# Include the third_party/drtrace directory so the header can be found:
target_include_directories(your_target PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/drtrace
)

# spdlog NOT detected - using direct API (no spdlog required):
# Link required dependencies:
#   - CURL::libcurl (system dependency - must be installed)
target_link_libraries(your_target PRIVATE
    CURL::libcurl
)
```

**Note:** No spdlog setup needed - only `CURL::libcurl` is required.

### C++ Code Integration

```cpp
#include "third_party/drtrace/drtrace_sink.hpp"
#include <ros/ros.h>
#include <cstdlib>

int main(int argc, char** argv) {
    ros::init(argc, argv, "my_ros_node");
    ros::NodeHandle nh;

    // Load configuration from environment (reads DRTRACE_APPLICATION_ID or _drtrace/config.json)
    drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

    // Create DrTrace client (no spdlog required - works alongside ROS logging)
    drtrace::DrtraceClient drtrace_client(config, "my_ros_node");

    // Use ROS logging for ROS-specific messages
    ROS_INFO("ROS node starting");
    ROS_DEBUG("Debug information");

    // Use DrTrace client for application-level logging
    drtrace_client.info("Application starting with DrTrace");
    drtrace_client.error("Error occurred", __FILE__, __LINE__);

    // Both logging systems work independently
    ros::spin();
    return 0;
}
```

## Key Points

1. **No spdlog required**: DrTrace Direct API works without spdlog
2. **Coexistence**: ROS logging and DrTrace logging work side-by-side
3. **No bridges needed**: No need to create adapters between ROS and spdlog
4. **Simple setup**: Only requires `CURL::libcurl` in CMake

## Detection

The log-init agent will automatically detect ROS projects by looking for:
- `#include <ros/ros.h>` in source files
- ROS logging macros (`ROS_INFO`, `ROS_DEBUG`, `ROS_ERROR`, etc.)
- `.launch` files in the project

When ROS is detected and spdlog is not found, the agent will suggest Pattern 2 (Direct API).

## Related Documentation

- [C++ Client README](../../packages/cpp/drtrace-client/README.md): Complete C++ client documentation
- [Log-Init Agent Guide](../../docs/log-init-agent-guide.md): How to use the log-init agent for setup suggestions

