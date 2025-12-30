cmake_minimum_required(VERSION 3.15)
project(cpp_component)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Fetch spdlog
include(FetchContent)
FetchContent_Declare(
    spdlog-fetch
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG v1.13.0
    GIT_SUBMODULES ""
)
FetchContent_MakeAvailable(spdlog-fetch)

# Find CURL
find_package(CURL REQUIRED)

# Add executable
add_executable(cpp_component
    cpp_component.cpp
)

# Include the header-only DrTrace C++ client copied by init-project
# Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)
target_include_directories(cpp_component PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/drtrace
)

# Link libraries
target_link_libraries(cpp_component PRIVATE
    spdlog::spdlog
    CURL::libcurl
)

