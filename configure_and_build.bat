@echo off
setlocal

echo ========================================
echo HQT C++ Build with VS 18
echo ========================================
echo.

REM Set up paths
set VS_PATH=C:\Program Files\Microsoft Visual Studio\18\Community
set VCVARSALL=%VS_PATH%\VC\Auxiliary\Build\vcvarsall.bat
set CMAKE=C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe
set VCPKG_ROOT=C:\vcpkg
set PROJECT_ROOT=%~dp0

REM Initialize Visual Studio environment
echo Step 1: Setting up Visual Studio environment...
call "%VCVARSALL%" x64
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to setup Visual Studio environment
    exit /b 1
)
echo   Visual Studio environment configured
echo.

cd /d "%PROJECT_ROOT%"

echo Step 2: Configuring CMake with NMake...
"%CMAKE%" -B build -S . ^
  -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%/scripts/buildsystems/vcpkg.cmake" ^
  -DBUILD_TESTING=ON ^
  -DBUILD_BENCHMARKS=OFF ^
  -G "NMake Makefiles" ^
  -DCMAKE_BUILD_TYPE=Release

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: CMake configuration failed!
    exit /b 1
)
echo   CMake configured successfully
echo.

echo Step 3: Building with NMake...
"%CMAKE%" --build build --config Release

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    exit /b 1
)
echo   Build completed successfully
echo.

echo Step 4: Running tests...
cd build
ctest --output-on-failure --verbose -C Release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo SOME TESTS FAILED
    echo ========================================
    cd ..
    exit /b 1
) else (
    echo.
    echo ========================================
    echo ALL TESTS PASSED!
    echo ========================================
    cd ..
    exit /b 0
)
