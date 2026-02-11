@echo off
cd /d "%~dp0"

call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe -B build -S . -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake -DBUILD_TESTING=ON -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release

if %ERRORLEVEL% NEQ 0 (
    echo CMake configuration failed
    exit /b 1
)

C:\vcpkg\downloads\tools\cmake-3.31.10-windows\cmake-3.31.10-windows-x86_64\bin\cmake.exe --build build --config Release

if %ERRORLEVEL% NEQ 0 (
    echo Build failed
    exit /b 1
)

echo Build successful!
build\cpp\tests\hqt_tests.exe
