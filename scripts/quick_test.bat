@echo off
REM Quick build and test script for Windows
REM Double-click this file or run from Command Prompt

echo.
echo ========================================
echo HQT C++ Quick Build and Test
echo ========================================
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

cd /d "%PROJECT_ROOT%"

echo Project root: %CD%
echo.

REM Check if build directory exists
if exist build (
    echo Build directory already exists.
    echo.
) else (
    echo Creating build directory...
    mkdir build
)

REM Configure CMake (assumes vcpkg is at C:\vcpkg)
echo Configuring CMake...
cmake -B build -S . ^
  -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ^
  -DBUILD_TESTING=ON ^
  -G "Visual Studio 17 2022" ^
  -A x64

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: CMake configuration failed!
    echo Make sure you run this from "Developer Command Prompt for VS 2022"
    echo or have CMake in your PATH.
    echo.
    pause
    exit /b 1
)

echo.
echo Building project...
cmake --build build --config Release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed!
    echo Check the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo Running tests...
cd build
ctest --output-on-failure --verbose --build-config Release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo SOME TESTS FAILED
    echo ========================================
    echo.
    cd ..
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo ALL TESTS PASSED!
    echo ========================================
    echo.
    cd ..
    pause
    exit /b 0
)
