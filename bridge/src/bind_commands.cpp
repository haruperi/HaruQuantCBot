/**
 * @file bind_commands.cpp
 * @brief Nanobind bindings for trading commands and error handling
 *
 * Registers C++ exceptions as Python exceptions so they can be caught
 * in Python code. Trading command bindings are minimal since they're
 * already exposed in bind_engine.cpp.
 */

#include <nanobind/nanobind.h>

#include "hqt/core/engine.hpp"
#include "hqt/trading/symbol_info.hpp"
#include "hqt/data/data_feed.hpp"
#include "hqt/data/mmap_reader.hpp"
#include "hqt/costs/costs_engine.hpp"

namespace nb = nanobind;
using namespace hqt;

void bind_commands(nb::module_& m) {
    // ========================================================================
    // Exception Handling
    // ========================================================================

    // Register C++ exceptions as Python exceptions
    nb::exception<EngineError>(m, "EngineError");
    nb::exception<DataFeedError>(m, "DataFeedError");
    nb::exception<MmapError>(m, "MmapError");

    // Note: Trading command bindings are in bind_engine.cpp
    // This file focuses on exception registration and any additional
    // command utilities.

    // ========================================================================
    // Helper Functions for Trading
    // ========================================================================

    m.def("to_price",
          [](int64_t fixed_point_price, int digits = 5) -> double {
              return static_cast<double>(fixed_point_price) / 1e6;
          },
          nb::arg("fixed_point_price"),
          nb::arg("digits") = 5,
          "Convert fixed-point price to double");

    m.def("from_price",
          [](double price) -> int64_t {
              return static_cast<int64_t>(price * 1e6);
          },
          nb::arg("price"),
          "Convert double price to fixed-point");

    // ========================================================================
    // Validation Helpers
    // ========================================================================

    m.def("validate_volume",
          [](double volume, const SymbolInfo& symbol) -> bool {
              if (volume < symbol.VolumeMin()) return false;
              if (volume > symbol.VolumeMax()) return false;

              // Check step
              double step = symbol.VolumeStep();
              if (step > 0.0) {
                  double remainder = std::fmod(volume - symbol.VolumeMin(), step);
                  if (std::abs(remainder) > 1e-8) return false;
              }

              return true;
          },
          nb::arg("volume"),
          nb::arg("symbol"),
          "Validate volume against symbol constraints");

    m.def("validate_price",
          [](double price, const SymbolInfo& symbol) -> bool {
              if (price <= 0.0) return false;

              // Check tick size
              double tick = symbol.TickSize();
              if (tick > 0.0) {
                  double remainder = std::fmod(price, tick);
                  if (std::abs(remainder) > 1e-8) return false;
              }

              return true;
          },
          nb::arg("price"),
          nb::arg("symbol"),
          "Validate price against symbol constraints");

    m.def("round_to_tick",
          [](double price, const SymbolInfo& symbol) -> double {
              double tick = symbol.TickSize();
              if (tick <= 0.0) return price;
              return std::round(price / tick) * tick;
          },
          nb::arg("price"),
          nb::arg("symbol"),
          "Round price to nearest tick");

    m.def("round_to_volume_step",
          [](double volume, const SymbolInfo& symbol) -> double {
              double step = symbol.VolumeStep();
              if (step <= 0.0) return volume;

              double min_vol = symbol.VolumeMin();
              double steps = std::round((volume - min_vol) / step);
              return min_vol + steps * step;
          },
          nb::arg("volume"),
          nb::arg("symbol"),
          "Round volume to nearest valid step");

    // ========================================================================
    // Constants and Enumerations
    // ========================================================================

    m.attr("VERSION") = "0.3.0";
    m.attr("BUILD_DATE") = __DATE__;
    m.attr("BUILD_TIME") = __TIME__;
}
