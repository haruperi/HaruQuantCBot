# Building and Testing HQT C++ Core

> **📚 UPDATED GUIDE AVAILABLE**
> For the most up-to-date build instructions, troubleshooting, and lessons learned, see:
> **[C++ Build and Test Guide](docs/cpp_build_and_test_guide.md)**
>
> ✅ **Status:** All 54 tests passing
> 🗓️ **Last Verified:** 2026-02-11
> 🏗️ **Build System:** VS 18 + vcpkg + NMake Makefiles

This guide walks you through building and testing the C++ core engine.

---

## Quick Start (Automated)

**PowerShell (Run as Administrator):**

```powershell
cd D:\Trading\Applications\HaruQuantCBot
.\scripts\setup_and_test.ps1
```

This will:
1. ✅ Verify Visual Studio 2022
2. 📦 Install vcpkg (if needed)
3. 📦 Install Google Test
4. ⚙️ Configure CMake
5. 🔨 Build the project
6. 🧪 Run all tests

---

## Manual Setup (Step-by-Step)

### Step 1: Verify Visual Studio 2022

Ensure you have Visual Studio 2022 with the **"Desktop development with C++"** workload.

**Check in Visual Studio Installer:**
1. Open "Visual Studio Installer"
2. Click "Modify" on Visual Studio 2022
3. Verify "Desktop development with C++" is checked
4. If not, check it and click "Modify" to install

---

### Step 2: Install vcpkg (One-Time Setup)

**Open PowerShell as Administrator:**

```powershell
# Clone vcpkg to C:\vcpkg
cd C:\
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg

# Bootstrap vcpkg
.\bootstrap-vcpkg.bat

# (Optional) Add to PATH for convenience
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\vcpkg", "Machine")
```

**Verify vcpkg is working:**

```powershell
C:\vcpkg\vcpkg version
```

You should see vcpkg version information.

---

### Step 3: Install Google Test

```powershell
cd C:\vcpkg
.\vcpkg install gtest:x64-windows
```

This will download and build Google Test (takes 2-5 minutes).

**Verify installation:**

```powershell
.\vcpkg list | Select-String "gtest"
```

You should see:
```
gtest:x64-windows    <version>    Google's C++ test framework
```

---

### Step 4: Configure CMake

**Option A: Using Developer Command Prompt (Recommended)**

1. Open **"Developer Command Prompt for VS 2022"** from Start Menu
2. Navigate to project:
   ```cmd
   cd /d D:\Trading\Applications\HaruQuantCBot
   ```
3. Configure CMake:
   ```cmd
   cmake -B build -S . ^
     -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ^
     -DBUILD_TESTING=ON ^
     -G "Visual Studio 17 2022" ^
     -A x64
   ```

**Option B: Using PowerShell**

```powershell
cd D:\Trading\Applications\HaruQuantCBot

cmake -B build -S . `
  -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake `
  -DBUILD_TESTING=ON `
  -G "Visual Studio 17 2022" `
  -A x64
```

**Expected output:**
```
-- Build files have been written to: D:/Trading/Applications/HaruQuantCBot/build
```

---

### Step 5: Build the Project

```powershell
cmake --build build --config Release
```

**Expected output:**
```
Build succeeded.
    0 Warning(s)
    0 Error(s)
```

---

### Step 6: Run Tests

```powershell
cd build
ctest --output-on-failure --verbose --build-config Release
```

**Expected output:**
```
Test project D:/Trading/Applications/HaruQuantCBot/build
    Start 1: TickTest.DefaultConstruction
1/76 Test #1: TickTest.DefaultConstruction .....   Passed    0.00 sec
    Start 2: TickTest.ParameterizedConstruction
2/76 Test #2: TickTest.ParameterizedConstruction   Passed    0.00 sec
...
100% tests passed, 0 tests failed out of 76

Total Test time (real) =   0.12 sec
```

---

## Alternative: Run Tests Directly

Instead of using `ctest`, you can run the test executable directly:

```powershell
.\cpp\tests\Release\hqt_tests.exe
```

**With Google Test filters:**

```powershell
# Run only Tick tests
.\cpp\tests\Release\hqt_tests.exe --gtest_filter=TickTest.*

# Run only FixedPoint tests
.\cpp\tests\Release\hqt_tests.exe --gtest_filter=FixedPointTest.*

# List all tests without running
.\cpp\tests\Release\hqt_tests.exe --gtest_list_tests
```

---

## Using Visual Studio IDE (Easiest)

### Option 1: Open CMake Project Directly

1. Open Visual Studio 2022
2. **File → Open → CMake...**
3. Select `D:\Trading\Applications\HaruQuantCBot\CMakeLists.txt`
4. Visual Studio will auto-configure
5. **Configure vcpkg:**
   - Go to **Project → CMake Settings for HQT**
   - Under "CMake toolchain file", enter: `C:\vcpkg\scripts\buildsystems\vcpkg.cmake`
   - Click **Save**
6. **Build → Build All** (or press `Ctrl+Shift+B`)
7. **Test → Run All Tests** (or press `Ctrl+R, A`)

### Option 2: Open Folder

1. **File → Open → Folder...**
2. Select `D:\Trading\Applications\HaruQuantCBot`
3. Visual Studio will detect CMakeLists.txt
4. Follow steps 5-7 above

**Test Explorer:**
- View → Test Explorer (or `Ctrl+E, T`)
- You'll see all 76 tests organized by test suite
- Click "Run All" or right-click individual tests

---

## Troubleshooting

### ❌ "cmake: command not found"

**Solution:** Use "Developer Command Prompt for VS 2022" instead of regular PowerShell/CMD.

Or add CMake to PATH:
```powershell
# Add to system PATH (run as Administrator)
$cmakePath = "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$cmakePath", "Machine")

# Restart PowerShell for changes to take effect
```

---

### ❌ "Could NOT find GTest"

**Solution:** Ensure vcpkg toolchain file is specified:

```powershell
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake
```

If still failing, reinstall Google Test:
```powershell
C:\vcpkg\vcpkg remove gtest:x64-windows
C:\vcpkg\vcpkg install gtest:x64-windows
```

---

### ❌ "C++20 features not available"

**Solution:** Ensure you're using Visual Studio 2022 (not 2019 or older).

Check compiler version:
```powershell
cl
```

Should show: `Microsoft (R) C/C++ Optimizing Compiler Version 19.30 or higher`

---

### ❌ Compilation errors in test files

**Solution:** Please report the specific error messages so we can fix the test code.

Common issues:
- Missing `#include` directives
- Incorrect header paths
- Type mismatches

---

### ⚠️ Tests fail to run

**Solution:** Ensure test executable was built:

```powershell
Test-Path .\build\cpp\tests\Release\hqt_tests.exe
```

If `False`, rebuild:
```powershell
cmake --build build --config Release --target hqt_tests
```

---

## Verification Checklist

Before marking Task 3.1 complete:

- [ ] Visual Studio 2022 with C++ workload installed
- [ ] vcpkg installed and working
- [ ] Google Test installed via vcpkg
- [ ] CMake configuration successful (no errors)
- [ ] Project builds successfully (0 errors)
- [ ] All 76 tests run
- [ ] All 76 tests pass (0 failures)
- [ ] Test coverage verified

---

## Next Steps After Tests Pass

Once all tests pass:

1. ✅ Mark Task 3.1 as **VERIFIED COMPLETE**
2. 📝 Update implementation plan with test results
3. 🚀 Proceed to **Task 3.2: Event Loop & Global Clock**

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `.\scripts\setup_and_test.ps1` | Automated setup + build + test |
| `cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake` | Configure |
| `cmake --build build --config Release` | Build |
| `cd build && ctest --verbose --build-config Release` | Run tests |
| `.\build\cpp\tests\Release\hqt_tests.exe` | Run tests directly |
| `C:\vcpkg\vcpkg list` | List installed packages |

---

## Getting Help

If you encounter issues:

1. Check the error message carefully
2. Review the Troubleshooting section above
3. Verify all prerequisites are installed
4. Check Visual Studio Installer for C++ workload
5. Try cleaning and rebuilding: `Remove-Item build -Recurse -Force` then reconfigure

---

**Last Updated:** 2026-02-11
**Task:** 3.1 - C++ Data Structures & Utilities
**Status:** Awaiting build verification
