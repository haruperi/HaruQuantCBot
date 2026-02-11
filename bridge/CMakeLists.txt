# Nanobind bridge module
cmake_minimum_required(VERSION 3.25)

# Find Python
find_package(Python 3.11 COMPONENTS Interpreter Development.Module REQUIRED)

# Fetch nanobind
include(FetchContent)
FetchContent_Declare(
    nanobind
    GIT_REPOSITORY https://github.com/wjakob/nanobind.git
    GIT_TAG v2.0.0
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(nanobind)

# Python extension module
# Note: Target name is hqt_core_ext, but OUTPUT_NAME is hqt_core (Python module name)
nanobind_add_module(
    hqt_core_ext
    NB_STATIC  # Build static extension

    # Source files
    src/module.cpp
    src/bind_types.cpp
    src/bind_engine.cpp
    src/bind_callbacks.cpp
    src/bind_commands.cpp
)

# Link against C++ core library
target_link_libraries(hqt_core_ext PRIVATE hqt_core)

# Include directories
target_include_directories(hqt_core_ext PRIVATE
    ${CMAKE_SOURCE_DIR}/cpp/include
    ${CMAKE_SOURCE_DIR}/cpp/src
)

# Set C++20 standard
target_compile_features(hqt_core_ext PRIVATE cxx_std_20)

# MSVC-specific settings
if(MSVC)
    target_compile_options(hqt_core_ext PRIVATE /W4)
else()
    target_compile_options(hqt_core_ext PRIVATE -Wall -Wextra)
endif()

# Set output name to match Python module name
set_target_properties(hqt_core_ext PROPERTIES
    OUTPUT_NAME "hqt_core"
)

# Install the module
install(TARGETS hqt_core_ext LIBRARY DESTINATION .)
