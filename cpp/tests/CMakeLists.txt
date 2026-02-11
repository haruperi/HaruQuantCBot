# Google Test framework
find_package(GTest REQUIRED)
include(GoogleTest)

# Enable testing
enable_testing()

# Test executable
add_executable(hqt_tests
    test_data_structures.cpp
    test_utilities.cpp
)

# Link against Google Test and our library (when created)
target_link_libraries(hqt_tests
    PRIVATE
    GTest::gtest
    GTest::gtest_main
)

# Include directories
target_include_directories(hqt_tests
    PRIVATE
    ${CMAKE_SOURCE_DIR}/cpp/include
)

# Set C++20 standard
target_compile_features(hqt_tests PRIVATE cxx_std_20)

# Discover tests
gtest_discover_tests(hqt_tests)

# Add test target
add_test(NAME AllTests COMMAND hqt_tests)
