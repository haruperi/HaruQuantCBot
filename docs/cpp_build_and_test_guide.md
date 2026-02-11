# C++ Build and Test Guide for HQT

**Last Updated:** 2026-02-11
**Visual Studio Version:** VS 18 (Visual Studio 2026)
**Status:** ✅ Verified Working (54/54 tests passing)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Building the Project](#building-the-project)
5. [Running Tests](#running-tests)
6. [Project Structure](#project-structure)
7. [Troubleshooting](#troubleshooting)
8. [Lessons Learned](#lessons-learned)
9. [Best Practices](#best-practices)
10. [Common Issues and Solutions](#common-issues-and-solutions)

---

## Quick Start

**For subsequent builds after initial setup:**

```batch
cd D:\Trading\Applications\HaruQuantCBot
configure_and_build.bat
```

This will:
- Set up Visual Studio environment
- Configure CMake
- Build all C++ code
- Run all 54 tests

**Expected output:**
```
[==========] 54 tests from 8 test suites ran.
[  PASSED  ] 54 tests.
```

---

## Prerequisites

### 1. Visual Studio 2026 (VS 18)

**Location:** `C:\Program Files\Microsoft Visual Studio\18\Community`

**Required Components:**
- Desktop development with C++
- MSVC v143 or later compiler
- Windows SDK
- CMake tools for Windows

### 2. Tools Already Installed

After initial setup, you should have:
- ✅ vcpkg at `C:\vcpkg`
- ✅ CMake 3.31.10 (downloaded by vcpkg)
- ✅ All C++ dependencies installed via vcpkg

---

## Initial Setup

**⚠️ Only needed once - skip if already completed**

### Step 1: Install vcpkg

```powershell
# Open PowerShell as Administrator
cd C:\
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
.\bootstrap-vcpkg.bat
```

### Step 2: Install Dependencies

Dependencies are automatically installed by CMake on first configure. The following packages will be built:

- **Google Test 1.17.0** - Unit testing framework
- **spdlog 1.17.0** - Fast C++ logging library
- **zeromq 4.3.5** + **cppzmq 4.11.0** - High-performance messaging
- **hdf5 2.0.0** - HDF5 data format library
- **tomlplusplus 3.4.0** - TOML config file parser
- **benchmark 1.9.5** - Microbenchmarking library
- **fmt 12.1.0** - String formatting library
- **zlib 1.3.1** - Compression library

**Time:** First build takes ~7-10 minutes to build all dependencies.

---

## Building the Project

### Method 1: Automated Script (Recommended)

```batch
cd D:\Trading\Applications\HaruQuantCBot
configure_and_build.bat
```

**What it does:**
1. Sets up Visual Studio 2026 Developer Command Prompt environment
2. Runs CMake configuration with vcpkg toolchain
3. Builds all C++ code using NMake
4. Runs all tests with verbose output

### Method 2: Manual Build

```batch
# 1. Open Developer Command Prompt for VS 2026
# Start Menu → Visual Studio 2026 → Developer Command Prompt

# 2. Navigate to project
cd D:\Trading\Applications\HaruQuantCBot

# 3. Set up Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

# 4. Configure CMake
C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe ^
  -B build -S . ^
  -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ^
  -DBUILD_TESTING=ON ^
  -G "NMake Makefiles" ^
  -DCMAKE_BUILD_TYPE=Release

# 5. Build
C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe ^
  --build build --config Release

# 6. Run tests
cd build\cpp\tests
hqt_tests.exe
```

### Build Output Location

```
D:\Trading\Applications\HaruQuantCBot\
├── build/
│   ├── cpp/
│   │   └── tests/
│   │       └── hqt_tests.exe          ← Test executable
│   └── vcpkg_installed/               ← Installed dependencies
└── configure_and_build.bat            ← Build script
```

---

## Running Tests

### Run All Tests

```batch
cd D:\Trading\Applications\HaruQuantCBot\build\cpp\tests
hqt_tests.exe
```

### Run Specific Test Suite

```batch
# Run only FixedPoint tests
hqt_tests.exe --gtest_filter=FixedPointTest.*

# Run only Tick tests
hqt_tests.exe --gtest_filter=TickTest.*

# Run only Bar tests
hqt_tests.exe --gtest_filter=BarTest.*

# Run only Timestamp tests
hqt_tests.exe --gtest_filter=TimestampTest.*
```

### List All Tests

```batch
hqt_tests.exe --gtest_list_tests
```

### Expected Test Output

```
[==========] Running 54 tests from 8 test suites.
[----------] 5 tests from TickTest
[----------] 8 tests from BarTest
[----------] 2 tests from TimeframeTest
[----------] 5 tests from SymbolInfoTest
[----------] 14 tests from FixedPointTest
[----------] 5 tests from TimestampTest
[----------] 7 tests from SeededRNGTest
[----------] 8 tests from EventTest
[==========] 54 tests from 8 test suites ran. (1 ms total)
[  PASSED  ] 54 tests.
```

---

## Project Structure

### C++ Source Organization

```
cpp/
├── include/hqt/              ← All header files (header-only library)
│   ├── data/
│   │   ├── tick.hpp          ← Tick data structure (64-byte cache-aligned)
│   │   ├── bar.hpp           ← OHLCV bar structure (128-byte aligned)
│   │   └── symbol_info.hpp   ← Symbol specifications
│   ├── market/
│   │   └── symbol_info.hpp   ← Trading constraints & conversions
│   ├── util/
│   │   ├── fixed_point.hpp   ← Fixed-point arithmetic (no floats!)
│   │   ├── timestamp.hpp     ← Microsecond timestamp utilities
│   │   └── random.hpp        ← Seeded RNG for reproducibility
│   └── core/
│       └── event.hpp         ← Event structure for priority queue
└── tests/
    ├── test_data_structures.cpp  ← Tests for Tick, Bar, Symbol (20 tests)
    └── test_utilities.cpp        ← Tests for utils & Event (34 tests)
```

### CMake Build Configuration

```
CMakeLists.txt               ← Root CMake configuration
├── cpp/CMakeLists.txt       ← C++ library definition
└── cpp/tests/CMakeLists.txt ← Test executable configuration
```

---

## Troubleshooting

### Issue 1: "CMake not found"

**Solution:** Use Developer Command Prompt for VS 2026, not regular CMD/PowerShell.

```batch
# Correct terminal:
# Start Menu → Visual Studio 2026 → Developer Command Prompt
```

### Issue 2: "vcpkg dependencies not found"

**Symptom:** `Could NOT find GTest` or similar errors

**Solution:** Ensure vcpkg toolchain file is specified:

```batch
cmake -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ...
```

### Issue 3: "Generator not found" or "Ninja not found"

**Solution:** Use **NMake Makefiles** generator, not Ninja:

```batch
cmake -G "NMake Makefiles" ...
```

**Why?** Ninja requires separate installation. NMake comes with Visual Studio.

### Issue 4: Build succeeds but tests show "No tests were found"

**Solution:** Run test executable directly:

```batch
cd build\cpp\tests
hqt_tests.exe
```

**Why?** ctest discovery may fail, but the executable works fine.

### Issue 5: Compilation errors about struct size

**Example:**
```
error C2338: 'Tick must be exactly 64 bytes'
```

**Cause:** Compiler automatic padding differs from expectations.

**Solution:** Member order matters! Group same-sized types together:

```cpp
// ✅ GOOD - No automatic padding
struct alignas(64) Tick {
    int64_t timestamp_us;  // 8 bytes
    int64_t bid;           // 8 bytes
    int64_t ask;           // 8 bytes
    int64_t bid_volume;    // 8 bytes
    int64_t ask_volume;    // 8 bytes
    uint32_t symbol_id;    // 4 bytes
    int32_t spread_points; // 4 bytes
    char _padding[16];     // 16 bytes
};  // Total: 64 bytes

// ❌ BAD - Automatic padding inserted
struct alignas(64) Tick {
    int64_t timestamp_us;  // 8 bytes
    uint32_t symbol_id;    // 4 bytes
    // [4 bytes automatic padding here!]
    int64_t bid;           // 8 bytes
    // ...
};
```

---

## Lessons Learned

### 1. Struct Alignment and Padding

**Problem:** MSVC adds automatic padding to align members to their natural boundaries.

**Solution:**
- Group members by size: all `int64_t` together, then `int32_t`, then smaller types
- This eliminates automatic padding
- Explicitly add padding at the end to reach target size

**Example from our code:**
```cpp
// Reordered from: timestamp, symbol_id, bid, ask, ...
// To: timestamp, bid, ask, bid_volume, ask_volume, symbol_id, spread_points
// Eliminated 4 bytes of automatic padding between symbol_id and bid
```

### 2. Enum Underlying Type Sizing

**Problem:** `enum class Timeframe : uint8_t` overflowed when value exceeded 255.

```cpp
// ❌ WRONG - Values up to 43200 don't fit in uint8_t (max 255)
enum class Timeframe : uint8_t {
    D1  = 1440,   // Truncated!
    W1  = 10080,  // Truncated!
    MN1 = 43200   // Truncated!
};
```

**Solution:** Use `uint16_t` (max 65535) for enums with large values:

```cpp
// ✅ CORRECT - uint16_t can hold values up to 65535
enum class Timeframe : uint16_t {
    M1  = 1,
    M5  = 5,
    M15 = 15,
    M30 = 30,
    H1  = 60,
    H4  = 240,
    D1  = 1440,
    W1  = 10080,
    MN1 = 43200
};
```

**Cascading changes needed:**
- Update `Event` struct to use `uint16_t` for timeframe field
- Update function signatures accepting timeframe
- Update tests to cast to `uint16_t` instead of `uint8_t`

### 3. CMake Generator Selection

**Problem:** Tried to use Ninja generator but Ninja wasn't installed.

```
CMake Error: CMake was unable to find a build program corresponding to "Ninja"
```

**Solution:** Use **NMake Makefiles** generator instead:

```batch
cmake -G "NMake Makefiles" ...
```

**Why NMake?**
- ✅ Comes bundled with Visual Studio (no separate install)
- ✅ Works reliably with MSVC compiler
- ✅ Simpler single-threaded build (easier debugging)
- ❌ Ninja: Faster parallel builds BUT requires separate installation

### 4. Visual Studio Environment Setup

**Problem:** CMake/compiler not found when running from regular CMD.

**Solution:** Must call `vcvarsall.bat` to set up environment:

```batch
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
```

**What this does:**
- Sets up compiler paths (`cl.exe`)
- Configures linker paths
- Sets include directories
- Configures build tools (nmake, etc.)

**Best practice:** Use Developer Command Prompt or call vcvarsall in batch scripts.

### 5. Test Data Accuracy

**Problem:** Tests failed because Unix timestamps were calculated incorrectly.

```cpp
// ❌ WRONG - Incorrect timestamp for 2026-02-10 14:30:00 UTC
int64_t ts = Timestamp::from_seconds(1'770'672'600);
// Actual date: 2026-02-09 (off by 17 hours!)

// ✅ CORRECT - Use Python or online converter to verify
int64_t ts = Timestamp::from_seconds(1'770'733'800);
// Actual date: 2026-02-10 14:30:00 UTC
```

**Lesson:** Always verify timestamps with external tools:

```python
import datetime
dt = datetime.datetime(2026, 2, 10, 14, 30, 0, tzinfo=datetime.timezone.utc)
print(int(dt.timestamp()))  # 1770733800
```

### 6. vcpkg Baseline Specification

**Problem:** Using `"builtin-baseline": "LATEST"` in vcpkg.json caused errors.

```json
{
  "builtin-baseline": "LATEST"  // ❌ Invalid!
}
```

**Solution:** Use specific commit hash:

```json
{
  "builtin-baseline": "f310de9dc9f16bd016e06d6c9a1decc07a918273"
}
```

**How to find baseline:**
- Check vcpkg error messages (they suggest valid commits)
- Or use a recent commit from https://github.com/microsoft/vcpkg

### 7. Warning-as-Error Handling

**Problem:** Warnings treated as errors stopped compilation:

```
warning C4244: conversion from 'int64_t' to 'int', possible loss of data
error C2220: the following warning is treated as error
```

**Solutions:**
1. **Fix the code** (preferred):
   ```cpp
   // ❌ Wrong
   int value = rng.next_int(1, 100);  // Returns int64_t!

   // ✅ Correct
   int64_t value = rng.next_int(1, 100);
   ```

2. **Suppress specific warnings** (use sparingly):
   ```cpp
   #pragma warning(disable: 4244)
   ```

3. **Explicitly discard [[nodiscard]]**:
   ```cpp
   // ❌ Wrong - warning C4834
   rng.next_int(1, 100);

   // ✅ Correct - explicitly discard
   (void)rng.next_int(1, 100);
   ```

### 8. Include Dependencies in Tests

**Problem:** Tests compiled but runtime errors occurred due to missing includes.

```cpp
// test_utilities.cpp
TEST(EventTest, BarCloseEventCreation) {
    Event e = Event::bar_close(1000000, 1, Timeframe::H1);  // ❌ Timeframe not found!
}
```

**Solution:** Include all necessary headers:

```cpp
#include "hqt/core/event.hpp"
#include "hqt/data/bar.hpp"  // ✅ Add this - Timeframe is defined here
```

**Lesson:** Even if Event uses Timeframe, test files must include Bar's header if they reference Timeframe enum directly.

---

## Best Practices

### 1. Always Test Compilation After Code Changes

```batch
# Quick recompile (from project root)
cd D:\Trading\Applications\HaruQuantCBot
configure_and_build.bat
```

**Don't assume it compiles!** Especially after:
- Changing struct member order
- Adding/removing padding
- Changing enum underlying types
- Modifying function signatures

### 2. Run Specific Test Suites During Development

```batch
# Faster feedback loop - test only what you changed
hqt_tests.exe --gtest_filter=FixedPointTest.*
```

Don't wait for all 54 tests when debugging one component.

### 3. Verify Struct Sizes with Static Asserts

```cpp
struct alignas(64) Tick {
    // ... members ...
};

// Add these ALWAYS
static_assert(sizeof(Tick) == 64, "Tick must be exactly 64 bytes");
static_assert(alignof(Tick) == 64, "Tick must be aligned to 64-byte boundary");
```

Catches size errors at compile time, not runtime!

### 4. Use Constexpr for Compile-Time Validation

```cpp
// ✅ Good - compiler verifies at compile time
constexpr bool test_tick_creation() {
    Tick t(1000, 1, 100, 101, 10, 10, 1);
    return t.is_valid();
}
static_assert(test_tick_creation(), "Tick construction must work");
```

### 5. Document Non-Obvious Decisions

```cpp
// Group int64_t members together to avoid automatic padding
// MSVC adds padding between uint32_t and int64_t to align to 8-byte boundary
struct alignas(64) Tick {
    int64_t timestamp_us;     // Keep all int64_t together
    int64_t bid;              // ...
    int64_t ask;              // ...
    uint32_t symbol_id;       // Then smaller types
    int32_t spread_points;
    char _padding[16];        // Explicit padding to 64 bytes
};
```

Future developers (including yourself) will thank you!

### 6. Keep Test Data Realistic

```cpp
// ✅ Good - Real prices for EURUSD (5 digits)
int64_t bid = 110520;  // 1.10520
int64_t ask = 110525;  // 1.10525

// ❌ Bad - Unrealistic values
int64_t bid = 100;
int64_t ask = 1000000;  // Spread of 999900 points?!
```

### 7. Clean Build When In Doubt

```batch
# Nuclear option - delete build dir and rebuild
cd D:\Trading\Applications\HaruQuantCBot
rmdir /S /Q build
configure_and_build.bat
```

Use when:
- CMake cache is corrupted
- Generator changed (Ninja → NMake)
- Weird linker errors
- "It works on my machine" syndrome

---

## Common Issues and Solutions

### Issue: "LNK2019: unresolved external symbol"

**Cause:** Missing library link or function implementation.

**Solution:** Our project is header-only, so check:
1. All functions are `inline` or `constexpr`
2. All templates are in headers
3. No `.cpp` implementations (except tests)

### Issue: Tests pass but ctest says "No tests were found"

**Cause:** ctest test discovery failed (known issue with our setup).

**Solution:** This is cosmetic. Run tests directly:
```batch
build\cpp\tests\hqt_tests.exe
```

### Issue: "fatal error C1083: Cannot open include file"

**Cause:** Include path not set correctly.

**Solution:** Check CMake configuration includes:
```cmake
target_include_directories(hqt_tests PRIVATE
    ${CMAKE_SOURCE_DIR}/cpp/include
)
```

### Issue: Very slow first build (7-10 minutes)

**Cause:** vcpkg building all dependencies from source.

**Solution:**
- ✅ This is normal for first build
- ✅ Subsequent builds are much faster (<10 seconds)
- ✅ Dependencies are cached in `C:\Users\<user>\AppData\Local\vcpkg\archives`

---

## Performance Notes

### Build Times

| Operation | Time | Notes |
|-----------|------|-------|
| First configure (with dependency install) | 7-10 min | One-time cost |
| Subsequent configure | 5-15 sec | Dependencies cached |
| Full rebuild (clean) | 10-15 sec | Compiling tests only |
| Incremental build (1 file changed) | 2-5 sec | Very fast |
| Running all 54 tests | 1-3 ms | Extremely fast |

### Optimization Tips

1. **Don't clean unless necessary** - Incremental builds are fast
2. **Run specific test suites** during development - Full suite for final verification
3. **Use header-only design** - No separate compilation/linking overhead
4. **Keep vcpkg cache** - Don't delete `AppData\Local\vcpkg\archives`

---

## Next Steps

### Current Status: ✅ Task 3.1 Complete

**Implemented:**
- ✅ Tick data structure (cache-aligned)
- ✅ Bar/OHLCV data structure
- ✅ Symbol info with trading constraints
- ✅ Fixed-point arithmetic (eliminates float precision errors)
- ✅ Microsecond timestamp utilities
- ✅ Seeded RNG for deterministic testing
- ✅ Event structure for priority queue
- ✅ 54 comprehensive unit tests (all passing)

**Ready for:**
- 🚀 Task 3.2: Event Loop & Global Clock
- 🚀 Task 3.3: Order Management System
- 🚀 Task 3.4: Position & Portfolio Tracker

### Adding New Tests

1. Edit `cpp/tests/test_*.cpp`
2. Follow Google Test patterns:
   ```cpp
   TEST(ComponentTest, FeatureName) {
       // Arrange
       Component c;

       // Act
       auto result = c.do_something();

       // Assert
       EXPECT_EQ(result, expected_value);
   }
   ```
3. Rebuild: `configure_and_build.bat`
4. Verify: Test count increases by 1

### Adding New Components

1. Create header in `cpp/include/hqt/<category>/`
2. Add corresponding test in `cpp/tests/test_<category>.cpp`
3. Ensure all functions are `inline`, `constexpr`, or template
4. Add static asserts for compile-time validation
5. Build and verify tests pass

---

## Reference: Full Build Command

For copy-paste reference, here's the complete manual build sequence:

```batch
@echo off
REM Navigate to project
cd D:\Trading\Applications\HaruQuantCBot

REM Setup Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

REM Configure with CMake
C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe ^
  -B build -S . ^
  -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ^
  -DBUILD_TESTING=ON ^
  -G "NMake Makefiles" ^
  -DCMAKE_BUILD_TYPE=Release

REM Build
C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe ^
  --build build --config Release

REM Run tests
cd build\cpp\tests
hqt_tests.exe
cd ..\..\..
```

---

## Support and Resources

### Documentation
- This guide: `docs/cpp_build_and_test_guide.md`
- C++ data structures: `docs/cpp_data_structures.md`
- Build instructions: `BUILDING.md`

### Key Files
- Build script: `configure_and_build.bat`
- CMake config: `CMakeLists.txt`, `cpp/CMakeLists.txt`, `cpp/tests/CMakeLists.txt`
- vcpkg manifest: `vcpkg.json`

### Quick Commands
```batch
# Build everything
configure_and_build.bat

# Run all tests
build\cpp\tests\hqt_tests.exe

# Run specific tests
build\cpp\tests\hqt_tests.exe --gtest_filter=FixedPointTest.*

# List all tests
build\cpp\tests\hqt_tests.exe --gtest_list_tests

# Clean rebuild
rmdir /S /Q build && configure_and_build.bat
```

---

**Document Version:** 1.0
**Last Verified:** 2026-02-11
**Test Status:** ✅ 54/54 passing
**Ready for:** Phase 3, Task 3.2
