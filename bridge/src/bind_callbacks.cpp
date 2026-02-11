/**
 * @file bind_callbacks.cpp
 * @brief Nanobind bindings for Engine callbacks
 *
 * Handles callback registration with proper GIL management.
 * When C++ calls Python callbacks, the GIL must be acquired.
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/function.h>

#include "hqt/core/engine.hpp"
#include "hqt/data/tick.hpp"
#include "hqt/data/bar.hpp"
#include "hqt/trading/symbol_info.hpp"
#include "hqt/trading/deal_info.hpp"
#include "hqt/trading/order_info.hpp"

namespace nb = nanobind;
using namespace hqt;

void bind_callbacks(nb::module_& m) {
    // Add callback methods to Engine class
    nb::class_<Engine> engine_class(m, "Engine");

    // ========================================================================
    // Tick Callback
    // ========================================================================

    engine_class.def("set_on_tick",
        [](Engine& self, nb::object callback) {
            if (callback.is_none()) {
                // Clear callback
                self.set_on_tick(nullptr);
                return;
            }

            // Wrap Python callback with GIL acquire
            self.set_on_tick([callback = nb::steal(callback)](
                const Tick& tick,
                const SymbolInfo& symbol) {
                // Acquire GIL before calling Python
                nb::gil_scoped_acquire acquire;
                try {
                    callback(tick, symbol);
                } catch (const nb::python_error& e) {
                    // Log Python exception but don't propagate to C++
                    // (would terminate backtest)
                    nb::print("Python callback error:", e.what());
                }
            });
        },
        nb::arg("callback"),
        "Register callback for tick events (callback(tick, symbol))");

    // ========================================================================
    // Bar Callback
    // ========================================================================

    engine_class.def("set_on_bar",
        [](Engine& self, nb::object callback) {
            if (callback.is_none()) {
                self.set_on_bar(nullptr);
                return;
            }

            self.set_on_bar([callback = nb::steal(callback)](
                const Bar& bar,
                const SymbolInfo& symbol,
                Timeframe tf) {
                nb::gil_scoped_acquire acquire;
                try {
                    callback(bar, symbol, tf);
                } catch (const nb::python_error& e) {
                    nb::print("Python callback error:", e.what());
                }
            });
        },
        nb::arg("callback"),
        "Register callback for bar close events (callback(bar, symbol, timeframe))");

    // ========================================================================
    // Trade Callback
    // ========================================================================

    engine_class.def("set_on_trade",
        [](Engine& self, nb::object callback) {
            if (callback.is_none()) {
                self.set_on_trade(nullptr);
                return;
            }

            self.set_on_trade([callback = nb::steal(callback)](
                const DealInfo& deal) {
                nb::gil_scoped_acquire acquire;
                try {
                    callback(deal);
                } catch (const nb::python_error& e) {
                    nb::print("Python callback error:", e.what());
                }
            });
        },
        nb::arg("callback"),
        "Register callback for trade events (callback(deal))");

    // ========================================================================
    // Order Callback
    // ========================================================================

    engine_class.def("set_on_order",
        [](Engine& self, nb::object callback) {
            if (callback.is_none()) {
                self.set_on_order(nullptr);
                return;
            }

            self.set_on_order([callback = nb::steal(callback)](
                const OrderInfo& order) {
                nb::gil_scoped_acquire acquire;
                try {
                    callback(order);
                } catch (const nb::python_error& e) {
                    nb::print("Python callback error:", e.what());
                }
            });
        },
        nb::arg("callback"),
        "Register callback for order events (callback(order))");

    // ========================================================================
    // Decorator-Style Callback Registration (Pythonic API)
    // ========================================================================

    engine_class.def("on_tick",
        [](Engine& self, nb::object callback) -> nb::object {
            // Register callback
            if (!callback.is_none()) {
                self.set_on_tick([callback = nb::steal(callback)](
                    const Tick& tick,
                    const SymbolInfo& symbol) {
                    nb::gil_scoped_acquire acquire;
                    try {
                        callback(tick, symbol);
                    } catch (const nb::python_error& e) {
                        nb::print("Python callback error:", e.what());
                    }
                });
            }
            // Return callback for decorator pattern
            return callback;
        },
        nb::arg("callback"),
        "Decorator-style tick callback registration");

    engine_class.def("on_bar",
        [](Engine& self, nb::object callback) -> nb::object {
            if (!callback.is_none()) {
                self.set_on_bar([callback = nb::steal(callback)](
                    const Bar& bar,
                    const SymbolInfo& symbol,
                    Timeframe tf) {
                    nb::gil_scoped_acquire acquire;
                    try {
                        callback(bar, symbol, tf);
                    } catch (const nb::python_error& e) {
                        nb::print("Python callback error:", e.what());
                    }
                });
            }
            return callback;
        },
        nb::arg("callback"),
        "Decorator-style bar callback registration");

    engine_class.def("on_trade",
        [](Engine& self, nb::object callback) -> nb::object {
            if (!callback.is_none()) {
                self.set_on_trade([callback = nb::steal(callback)](
                    const DealInfo& deal) {
                    nb::gil_scoped_acquire acquire;
                    try {
                        callback(deal);
                    } catch (const nb::python_error& e) {
                        nb::print("Python callback error:", e.what());
                    }
                });
            }
            return callback;
        },
        nb::arg("callback"),
        "Decorator-style trade callback registration");

    engine_class.def("on_order",
        [](Engine& self, nb::object callback) -> nb::object {
            if (!callback.is_none()) {
                self.set_on_order([callback = nb::steal(callback)](
                    const OrderInfo& order) {
                    nb::gil_scoped_acquire acquire;
                    try {
                        callback(order);
                    } catch (const nb::python_error& e) {
                        nb::print("Python callback error:", e.what());
                    }
                });
            }
            return callback;
        },
        nb::arg("callback"),
        "Decorator-style order callback registration");
}
