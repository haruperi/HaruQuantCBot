# HQT C++ Core Engine

# Core library with implementation files (Task 3.4+)
add_library(hqt_core
    src/trading/trade.cpp
)

target_include_directories(hqt_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Set C++20 standard
target_compile_features(hqt_core PUBLIC cxx_std_20)

# Link dependencies (when needed)
# target_link_libraries(hqt_core
#     PUBLIC
#         spdlog::spdlog
#         cppzmq
#         hdf5::hdf5
#         tomlplusplus::tomlplusplus
# )

# Add tests subdirectory
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()

# Add benchmarks subdirectory
option(BUILD_BENCHMARKS "Build benchmark executables" ON)
if(BUILD_BENCHMARKS)
    add_subdirectory(benchmarks)
endif()

message(STATUS "C++ core header-only library configured (Tasks 3.1 & 3.2 complete)")
