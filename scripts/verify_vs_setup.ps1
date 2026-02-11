# Visual Studio 2022 Verification Script
# Run this in PowerShell to check your setup

Write-Host "=== Visual Studio 2022 Setup Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check for Visual Studio 2022
$vsPath = "C:\Program Files\Microsoft Visual Studio\2022"
if (Test-Path $vsPath) {
    Write-Host "✅ Visual Studio 2022 found at: $vsPath" -ForegroundColor Green

    # Check for Community/Professional/Enterprise
    $editions = @("Community", "Professional", "Enterprise")
    foreach ($edition in $editions) {
        $editionPath = Join-Path $vsPath $edition
        if (Test-Path $editionPath) {
            Write-Host "   Edition: $edition" -ForegroundColor Green
            $vsInstallPath = $editionPath
        }
    }
} else {
    Write-Host "❌ Visual Studio 2022 not found" -ForegroundColor Red
    Write-Host "   Please install from: https://visualstudio.microsoft.com/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check for CMake
$cmakePath = Get-Command cmake -ErrorAction SilentlyContinue
if ($cmakePath) {
    Write-Host "✅ CMake found: $($cmakePath.Source)" -ForegroundColor Green
    $cmakeVersion = & cmake --version | Select-Object -First 1
    Write-Host "   $cmakeVersion" -ForegroundColor Green
} else {
    Write-Host "⚠️  CMake not in PATH (Visual Studio has it, but may need to add to PATH)" -ForegroundColor Yellow
}

# Check for MSVC compiler
$clPath = Get-Command cl -ErrorAction SilentlyContinue
if ($clPath) {
    Write-Host "✅ MSVC compiler found in PATH" -ForegroundColor Green
} else {
    Write-Host "⚠️  MSVC not in PATH (normal - will use Developer Command Prompt)" -ForegroundColor Yellow
}

# Check for vcpkg
$vcpkgPath = Get-Command vcpkg -ErrorAction SilentlyContinue
if ($vcpkgPath) {
    Write-Host "✅ vcpkg found: $($vcpkgPath.Source)" -ForegroundColor Green
} else {
    Write-Host "⚠️  vcpkg not in PATH - we'll set it up next" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. If CMake/vcpkg are not in PATH, we'll use Visual Studio's Developer Command Prompt"
Write-Host "2. Install vcpkg and Google Test"
Write-Host "3. Configure and build the project"
Write-Host ""
