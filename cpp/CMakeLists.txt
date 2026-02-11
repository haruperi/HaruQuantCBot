# HQT C++ Core Engine

# Header-only library for now (data structures and utilities)
add_library(hqt_core INTERFACE)

target_include_directories(hqt_core
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Will become a normal library when we add source files
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
