# C++ Build Environment Setup Guide

This guide helps you set up the C++ build environment to compile and test the HQT core engine.

## Prerequisites

### Windows (Recommended for full system)

1. **Visual Studio 2022** (Community Edition is free)
   - Download: https://visualstudio.microsoft.com/downloads/
   - Workload: "Desktop development with C++"
   - Includes: MSVC compiler, CMake, vcpkg

2. **vcpkg** (C++ package manager)
   ```powershell
   # Clone vcpkg
   cd C:\
   git clone https://github.com/microsoft/vcpkg.git
   cd vcpkg
   .\bootstrap-vcpkg.bat

   # Add to PATH (PowerShell as Admin)
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\vcpkg", "Machine")
   ```

3. **Install Google Test**
   ```powershell
   cd C:\vcpkg
   .\vcpkg install gtest:x64-windows
   ```

### Linux (For backtesting/optimization only)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y cmake build-essential git

# Install vcpkg
cd ~
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
./bootstrap-vcpkg.sh

# Install Google Test
./vcpkg install gtest
```

## Build and Test

### Option 1: Command Line (Windows)

```powershell
# Navigate to project root
cd D:\Trading\Applications\HaruQuantCBot

# Configure CMake with vcpkg
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake -DBUILD_TESTING=ON

# Build
cmake --build build --config Release

# Run tests
cd build
ctest --output-on-failure --verbose
```

### Option 2: Command Line (Linux)

```bash
# Navigate to project root
cd ~/HaruQuantCBot  # or your path

# Configure
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=~/vcpkg/scripts/buildsystems/vcpkg.cmake -DBUILD_TESTING=ON

# Build
cmake --build build

# Run tests
cd build
ctest --output-on-failure --verbose
```

### Option 3: Visual Studio (Easiest on Windows)

1. Open Visual Studio 2022
2. File → Open → CMake... → Select `CMakeLists.txt`
3. Visual Studio will auto-configure with CMake
4. Set vcpkg path in CMakeSettings.json:
   ```json
   {
     "configurations": [{
       "name": "x64-Debug",
       "cmakeToolchain": "C:/vcpkg/scripts/buildsystems/vcpkg.cmake"
     }]
   }
   ```
5. Build → Build All
6. Test → Run All Tests

## Expected Output

When tests run successfully, you should see:

```
[==========] Running 76 tests from 15 test suites.
[----------] Global test environment set-up.
[----------] 6 tests from TickTest
[ RUN      ] TickTest.DefaultConstruction
[       OK ] TickTest.DefaultConstruction (0 ms)
[ RUN      ] TickTest.ParameterizedConstruction
[       OK ] TickTest.ParameterizedConstruction (0 ms)
...
[==========] 76 tests from 15 test suites ran. (XX ms total)
[  PASSED  ] 76 tests.
```

## Troubleshooting

### "CMake not found"
- Windows: Install Visual Studio 2022 with C++ workload
- Linux: `sudo apt install cmake`

### "GTest not found"
- Install via vcpkg: `vcpkg install gtest`
- Ensure CMake uses vcpkg toolchain file

### "C++20 features not supported"
- MSVC: Use Visual Studio 2022 or newer
- GCC: Use GCC 12+ (`gcc --version`)
- Clang: Use Clang 15+ (`clang --version`)

### Compilation errors
- Check that all header files are in `cpp/include/hqt/`
- Verify `#include` paths in test files
- Ensure C++20 standard is set in CMakeLists.txt

## Quick Verification (Without Full Build)

If you just want to verify syntax without running tests:

```bash
# Linux: Check if headers are valid C++
cd cpp/include
find . -name "*.hpp" -exec g++ -std=c++20 -fsyntax-only {} \;

# Windows (PowerShell with MSVC):
cd cpp/include
Get-ChildItem -Recurse -Filter *.hpp | ForEach-Object { cl /std:c++20 /Zs $_.FullName }
```

## Next Steps After Setup

Once the build environment is working:

1. Run all tests: `ctest --verbose`
2. Check coverage (optional): `cmake --build build --target coverage`
3. Run benchmarks: `./build/cpp/benchmarks/hqt_benchmarks` (when Task 3.2+ complete)
4. Continue to Task 3.2 implementation
