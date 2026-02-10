# HQT Trading System

[![CI](https://github.com/yourusername/hqt/workflows/CI/badge.svg)](https://github.com/yourusername/hqt/actions)

**Hybrid C++/Python Quantitative Trading & Backtesting System**

## Status

🚧 **Phase 1: Foundation Infrastructure** - In Development

Current version: `v0.1.0-foundation` (in progress)

## Overview

HQT is an enterprise-grade quantitative trading and backtesting system featuring:

- **Hybrid Architecture**: C++20 core engine for performance + Python for strategy development
- **Zero-Copy Bridge**: Nanobind for seamless C++/Python interoperability
- **High Performance**: ≥1M ticks/sec backtesting throughput
- **Distributed Optimization**: Ray-based parallel parameter optimization
- **Live Trading**: MT5 broker integration via ZeroMQ
- **Comprehensive Risk Management**: Position sizing, regime detection, portfolio allocation
- **Desktop UI**: PySide6 with PyQtGraph charting
- **REST API**: FastAPI with WebSocket streaming

## Architecture

```
┌─────────────────────────────────────────────────┐
│            UI (PySide6) / API (FastAPI)         │
├─────────────────────────────────────────────────┤
│         Python Control Tower                    │
│  Strategy | Risk | Config | Notifications       │
├─────────────────────────────────────────────────┤
│         Bridge Layer (Nanobind)                 │
├─────────────────────────────────────────────────┤
│         C++20 Core Engine                       │
│  Event Loop | Matching | State | Orders         │
├─────────────────────────────────────────────────┤
│         Data Storage (Parquet/HDF5 + SQL)       │
└─────────────────────────────────────────────────┘
```

## Prerequisites

### Required

- **Python**: 3.11+ (tested on 3.14.0)
- **Git**: 2.40+
- **CMake**: 3.25+ (⚠️ needs installation)
- **vcpkg**: Latest (⚠️ needs installation)
- **C++ Compiler**:
  - Windows: MSVC 2022+
  - Linux: GCC 12+ or Clang 15+

### Optional

- **MT5 Terminal**: For live trading (Windows only)

## Installation

### 1. Install CMake

**Windows:**
```bash
# Via winget
winget install Kitware.CMake

# Or download from https://cmake.org/download/
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install cmake

# Arch
sudo pacman -S cmake
```

### 2. Install vcpkg

```bash
# Clone vcpkg
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg

# Windows
.\bootstrap-vcpkg.bat

# Linux/macOS
./bootstrap-vcpkg.sh
```

### 3. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/hqt.git
cd hqt

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install Python dependencies
pip install -e ".[dev]"

# Build C++ core (once source files exist)
cmake -B build -DCMAKE_TOOLCHAIN_FILE=path/to/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build --config Release

# Initialize database
alembic upgrade head
```

## Quick Start

```bash
# Run tests
pytest tests/

# C++ tests (once implemented)
cd build && ctest

# Start development
python -m hqt --help
```

## Project Structure

```
hqt/
├── cpp/              # C++20 core engine
├── bridge/           # Nanobind C++/Python bridge
├── src/hqt/          # Python packages
├── strategies/       # User strategy files
├── config/           # TOML configuration
├── docs/             # Documentation
├── tests/            # Test suite
└── scripts/          # Utility scripts
```

## Documentation

- [Software Requirements Specification](docs/01_software_requirements_specification.md)
- [System Design Document](docs/02_system_design_document.md)
- [Implementation Plan](docs/03_implementation_plan.md)
- Developer Guide (coming in Phase 1)

## Development Roadmap

- [x] Phase 1.1: Repository scaffold & build system ⬅️ **Current**
- [ ] Phase 1.2: CI/CD pipeline
- [ ] Phase 1.3-1.7: Foundation modules
- [ ] Phase 2: Data infrastructure
- [ ] Phase 3: C++ core engine
- [ ] ... (see Implementation Plan)

## License

MIT License - see LICENSE file

## Contributing

See Developer Guide (coming soon)

## Contact

- Project: https://github.com/yourusername/hqt
- Issues: https://github.com/yourusername/hqt/issues
