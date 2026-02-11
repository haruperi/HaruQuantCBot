cmake_minimum_required(VERSION 3.25)

# vcpkg toolchain integration (must be set before project())
if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
    if(EXISTS "C:/vcpkg/scripts/buildsystems/vcpkg.cmake")
        set(CMAKE_TOOLCHAIN_FILE "C:/vcpkg/scripts/buildsystems/vcpkg.cmake"
            CACHE STRING "Vcpkg toolchain file")
        message(STATUS "Using vcpkg toolchain: ${CMAKE_TOOLCHAIN_FILE}")
    else()
        message(WARNING "vcpkg not found at C:/vcpkg. Dependencies may not be found.")
    endif()
endif()

project(hqt VERSION 0.3.0 LANGUAGES CXX)

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
# add_subdirectory(bridge)  # Disabled for C++ testing only

# Testing
option(BUILD_TESTING "Build tests" ON)
# Tests are added in cpp/CMakeLists.txt when BUILD_TESTING is ON
if(BUILD_TESTING)
    enable_testing()
endif()

# Installation
install(TARGETS EXPORT hqt-targets)
