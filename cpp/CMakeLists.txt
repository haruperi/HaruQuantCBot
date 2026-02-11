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

message(STATUS "C++ core header-only library configured (Task 3.1 complete)")
