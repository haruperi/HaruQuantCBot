@echo off
setlocal

echo ========================================
echo Building HQT C++ Core
echo ========================================
echo.

REM Set paths
set CMAKE=C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe
set VCPKG_ROOT=C:\vcpkg
set PROJECT_ROOT=%~dp0

cd /d "%PROJECT_ROOT%"

echo Step 1: Configuring CMake...
"%CMAKE%" -B build -S . ^
  -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%/scripts/buildsystems/vcpkg.cmake" ^
  -DBUILD_TESTING=ON ^
  -G "Visual Studio 17 2022" ^
  -A x64

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: CMake configuration failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Building...
"%CMAKE%" --build build --config Release

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo Step 3: Running tests...
cd build
"%CMAKE%" -E chdir . ctest --output-on-failure --verbose --build-config Release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo SOME TESTS FAILED
    echo ========================================
    cd ..
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo ALL TESTS PASSED!
    echo ========================================
    cd ..
    pause
    exit /b 0
)
