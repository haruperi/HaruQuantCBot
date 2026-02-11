cmake_minimum_required(VERSION 3.25)
project(hqt VERSION 0.1.0 LANGUAGES CXX)

# C++20 required
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Compiler flags
if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -Wpedantic -Werror)
endif()

# vcpkg integration note
# To use: cmake -B build -DCMAKE_TOOLCHAIN_FILE=<vcpkg_root>/scripts/buildsystems/vcpkg.cmake
message(STATUS "To use vcpkg, run cmake with -DCMAKE_TOOLCHAIN_FILE=<vcpkg_root>/scripts/buildsystems/vcpkg.cmake")

# Find dependencies (will work once vcpkg is set up)
# find_package(spdlog REQUIRED)
# find_package(cppzmq REQUIRED)
# find_package(HDF5 REQUIRED)
# find_package(tomlplusplus REQUIRED)

# Subdirectories
add_subdirectory(cpp)
add_subdirectory(bridge)

# Testing
option(BUILD_TESTING "Build tests" ON)
if(BUILD_TESTING)
    enable_testing()
    # add_subdirectory(cpp/tests)
    # add_subdirectory(cpp/benchmarks)
endif()

# Installation
install(TARGETS EXPORT hqt-targets)
