/**
 * C++ component for multi-language example.
 * 
 * This demonstrates DrTrace integration in a C++ component that works
 * alongside a Python component.
 */

#include <iostream>
#include <vector>
#include <stdexcept>
#include "third_party/drtrace/drtrace_sink.hpp"

int main() {
    // Configure DrTrace
    drtrace::DrtraceConfig config;
    config.application_id = "multi-language-app";
    config.daemon_url = "http://localhost:8001/logs/ingest";
    config.service_name = "multi-language-app";
    config.enabled = true;
    
    // Create logger with DrTrace integration
    auto logger = drtrace::create_drtrace_logger("cpp_component", config);
    logger->set_level(spdlog::level::info);
    
    // Log startup
    logger->info("Starting C++ component");
    
    try {
        // Simulate normal operations
        logger->info("Processing C++ operations");
        
        // Process some data
        std::vector<int> data = {1, 2, 3, 4, 5};
        logger->info("Processing {} items", data.size());
        
        // Simulate computation
        int result = 0;
        for (int value : data) {
            result += value;
        }
        logger->info("Computed result: {}", result);
        
        // Trigger an error
        try {
            std::vector<int> empty_data;
            if (empty_data.empty()) {
                throw std::runtime_error("Cannot process empty data vector");
            }
        } catch (const std::exception& e) {
            logger->error("Error in C++ component: {}", e.what());
        }
        
        logger->info("C++ component completed");
        
    } catch (const std::exception& e) {
        logger->error("Fatal error in C++ component: {}", e.what());
        return 1;
    }
    
    // Flush logs before exit
    logger->flush();
    
    return 0;
}

