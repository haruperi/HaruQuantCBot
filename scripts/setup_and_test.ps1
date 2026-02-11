# Complete C++ Build Environment Setup and Test Script
# Run this in PowerShell (as Administrator for vcpkg installation)

param(
    [switch]$SkipVcpkgInstall = $false
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  HQT C++ Build Environment Setup & Test                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get project root
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "📁 Project root: $projectRoot" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 1: Check Visual Studio
# ============================================================================
Write-Host "Step 1: Checking Visual Studio 2022..." -ForegroundColor Cyan

$vsPath = "C:\Program Files\Microsoft Visual Studio\2022"
$vsFound = $false
$editions = @("Community", "Professional", "Enterprise")

foreach ($edition in $editions) {
    $editionPath = Join-Path $vsPath $edition
    if (Test-Path $editionPath) {
        Write-Host "  ✅ Found Visual Studio 2022 $edition" -ForegroundColor Green
        $vsInstallPath = $editionPath
        $vsFound = $true
        break
    }
}

if (-not $vsFound) {
    Write-Host "  ❌ Visual Studio 2022 not found!" -ForegroundColor Red
    Write-Host "     Please install from: https://visualstudio.microsoft.com/downloads/" -ForegroundColor Yellow
    Write-Host "     Required workload: 'Desktop development with C++'" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# Step 2: Setup vcpkg
# ============================================================================
Write-Host ""
Write-Host "Step 2: Setting up vcpkg..." -ForegroundColor Cyan

$vcpkgRoot = "C:\vcpkg"

if (-not (Test-Path $vcpkgRoot) -and -not $SkipVcpkgInstall) {
    Write-Host "  📦 Installing vcpkg to $vcpkgRoot..." -ForegroundColor Yellow
    Write-Host "     This may take a few minutes..." -ForegroundColor Yellow

    # Clone vcpkg
    git clone https://github.com/microsoft/vcpkg.git $vcpkgRoot

    # Bootstrap vcpkg
    Set-Location $vcpkgRoot
    .\bootstrap-vcpkg.bat

    # Return to project root
    Set-Location $projectRoot

    Write-Host "  ✅ vcpkg installed successfully" -ForegroundColor Green
} elseif (Test-Path $vcpkgRoot) {
    Write-Host "  ✅ vcpkg already installed at $vcpkgRoot" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Skipping vcpkg installation (use -SkipVcpkgInstall:`$false to install)" -ForegroundColor Yellow
}

$vcpkgExe = Join-Path $vcpkgRoot "vcpkg.exe"

# ============================================================================
# Step 3: Install Google Test
# ============================================================================
Write-Host ""
Write-Host "Step 3: Installing Google Test..." -ForegroundColor Cyan

if (Test-Path $vcpkgExe) {
    # Check if gtest is already installed
    $gtestInstalled = & $vcpkgExe list | Select-String "gtest"

    if ($gtestInstalled) {
        Write-Host "  ✅ Google Test already installed" -ForegroundColor Green
    } else {
        Write-Host "  📦 Installing Google Test (this may take a few minutes)..." -ForegroundColor Yellow
        & $vcpkgExe install gtest:x64-windows

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Google Test installed successfully" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Failed to install Google Test" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "  ⚠️  vcpkg not found, skipping Google Test installation" -ForegroundColor Yellow
}

# ============================================================================
# Step 4: Configure CMake
# ============================================================================
Write-Host ""
Write-Host "Step 4: Configuring CMake..." -ForegroundColor Cyan

$buildDir = Join-Path $projectRoot "build"
$vcpkgToolchain = Join-Path $vcpkgRoot "scripts\buildsystems\vcpkg.cmake"

# Remove old build directory if exists
if (Test-Path $buildDir) {
    Write-Host "  🗑️  Removing old build directory..." -ForegroundColor Yellow
    Remove-Item $buildDir -Recurse -Force
}

Write-Host "  ⚙️  Running CMake configure..." -ForegroundColor Yellow

# Use cmake from Visual Studio or PATH
$cmakeCmd = "cmake"

try {
    & $cmakeCmd -B $buildDir -S $projectRoot `
        -DCMAKE_TOOLCHAIN_FILE="$vcpkgToolchain" `
        -DBUILD_TESTING=ON `
        -G "Visual Studio 17 2022" `
        -A x64

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ CMake configured successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ CMake configuration failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ❌ CMake not found in PATH" -ForegroundColor Red
    Write-Host "     Try running this script from 'Developer Command Prompt for VS 2022'" -ForegroundColor Yellow
    Write-Host "     Or add CMake to PATH from: $vsInstallPath\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# Step 5: Build the project
# ============================================================================
Write-Host ""
Write-Host "Step 5: Building the project..." -ForegroundColor Cyan

Write-Host "  🔨 Building (this may take a minute)..." -ForegroundColor Yellow

& $cmakeCmd --build $buildDir --config Release

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Build completed successfully" -ForegroundColor Green
} else {
    Write-Host "  ❌ Build failed" -ForegroundColor Red
    Write-Host "     Check the error messages above for details" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# Step 6: Run the tests
# ============================================================================
Write-Host ""
Write-Host "Step 6: Running tests..." -ForegroundColor Cyan
Write-Host ""

Set-Location $buildDir

& ctest --output-on-failure --verbose --build-config Release

$testExitCode = $LASTEXITCODE

Set-Location $projectRoot

Write-Host ""
if ($testExitCode -eq 0) {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✅ ALL TESTS PASSED!                                         ║" -ForegroundColor Green
    Write-Host "║                                                                ║" -ForegroundColor Green
    Write-Host "║  Task 3.1 is now VERIFIED and COMPLETE                        ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
} else {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║  ❌ SOME TESTS FAILED                                         ║" -ForegroundColor Red
    Write-Host "║                                                                ║" -ForegroundColor Red
    Write-Host "║  Please review the error messages above                       ║" -ForegroundColor Red
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📊 Test Results Summary:" -ForegroundColor Cyan
Write-Host "   Build directory: $buildDir" -ForegroundColor White
Write-Host "   Test executable: $buildDir\cpp\tests\Release\hqt_tests.exe" -ForegroundColor White
Write-Host ""
Write-Host "💡 To run tests manually:" -ForegroundColor Cyan
Write-Host "   cd $buildDir" -ForegroundColor White
Write-Host "   ctest --verbose --build-config Release" -ForegroundColor White
Write-Host ""
Write-Host "   Or run the test executable directly:" -ForegroundColor White
Write-Host "   .\cpp\tests\Release\hqt_tests.exe" -ForegroundColor White
Write-Host ""
