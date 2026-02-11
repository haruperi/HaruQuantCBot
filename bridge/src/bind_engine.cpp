/**
 * @file bind_engine.cpp
 * @brief Nanobind bindings for the Engine class
 *
 * Exposes the main Engine facade to Python with proper GIL management.
 * The run() method releases the GIL to allow concurrent Python execution.
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "hqt/core/engine.hpp"
#include "hqt/trading/symbol_info.hpp"

namespace nb = nanobind;
using namespace hqt;

void bind_engine(nb::module_& m) {
    nb::class_<Engine>(m, "Engine", "Main backtesting engine facade")
        // Constructor
        .def(nb::init<double, const std::string&, int>(),
             nb::arg("initial_balance") = 10000.0,
             nb::arg("currency") = "USD",
             nb::arg("leverage") = 100,
             "Create engine with initial account state")

        // ====================================================================
        // Configuration Methods
        // ====================================================================

        .def("load_symbol",
             &Engine::load_symbol,
             nb::arg("symbol_name"),
             nb::arg("symbol_info"),
             "Load symbol into engine")

        .def("load_conversion_pair",
             &Engine::load_conversion_pair,
             nb::arg("base"),
             nb::arg("quote"),
             nb::arg("rate"),
             "Load currency conversion pair")

        // ====================================================================
        // Run Loop Control
        // ====================================================================

        .def("run",
             [](Engine& self) {
                 // Release GIL during long-running C++ execution
                 nb::gil_scoped_release release;
                 self.run();
             },
             "Run simulation until all events processed (releases GIL)")

        .def("run_steps",
             [](Engine& self, size_t steps) {
                 // Release GIL during C++ execution
                 nb::gil_scoped_release release;
                 return self.run_steps(steps);
             },
             nb::arg("steps"),
             "Run N simulation steps (releases GIL)")

        .def("pause",
             &Engine::pause,
             "Pause simulation")

        .def("resume",
             &Engine::resume,
             "Resume paused simulation")

        .def("stop",
             &Engine::stop,
             "Stop simulation completely")

        .def("is_running",
             &Engine::is_running,
             "Check if engine is running")

        .def("is_paused",
             &Engine::is_paused,
             "Check if engine is paused")

        // ====================================================================
        // Trading Commands (implemented in bind_commands.cpp)
        // ====================================================================

        .def("buy",
             &Engine::buy,
             nb::arg("volume"),
             nb::arg("symbol"),
             nb::arg("sl") = 0.0,
             nb::arg("tp") = 0.0,
             nb::arg("comment") = "",
             "Open BUY position with margin check")

        .def("sell",
             &Engine::sell,
             nb::arg("volume"),
             nb::arg("symbol"),
             nb::arg("sl") = 0.0,
             nb::arg("tp") = 0.0,
             nb::arg("comment") = "",
             "Open SELL position with margin check")

        .def("modify",
             &Engine::modify,
             nb::arg("ticket"),
             nb::arg("sl"),
             nb::arg("tp"),
             "Modify position SL/TP")

        .def("close",
             &Engine::close,
             nb::arg("ticket"),
             "Close position")

        .def("cancel",
             &Engine::cancel,
             nb::arg("ticket"),
             "Cancel pending order")

        // ====================================================================
        // State Access (Read-Only)
        // ====================================================================

        .def("account",
             &Engine::account,
             nb::rv_policy::reference_internal,
             "Get account information")

        .def("positions",
             &Engine::positions,
             "Get all open positions")

        .def("orders",
             &Engine::orders,
             "Get all pending orders")

        .def("deals",
             &Engine::deals,
             nb::rv_policy::reference_internal,
             "Get all deals")

        .def("get_symbol",
             &Engine::get_symbol,
             nb::arg("symbol_name"),
             nb::rv_policy::reference_internal,
             "Get symbol info by name (returns None if not found)")

        .def("current_time",
             &Engine::current_time,
             "Get current simulation timestamp (microseconds)")

        // ====================================================================
        // Data Feed Access
        // ====================================================================

        .def("data_feed",
             nb::overload_cast<>(&Engine::data_feed),
             nb::rv_policy::reference_internal,
             "Get data feed reference")

        // ====================================================================
        // Event Loop Access
        // ====================================================================

        .def("event_loop",
             nb::overload_cast<>(&Engine::event_loop),
             nb::rv_policy::reference_internal,
             "Get event loop reference")

        // ====================================================================
        // Special Methods
        // ====================================================================

        .def("__repr__",
             [](const Engine& e) {
                 const auto& acc = e.account();
                 return "<Engine balance=" + std::to_string(acc.Balance() / 1e6) +
                        " currency=" + acc.Currency() +
                        " running=" + (e.is_running() ? "True" : "False") + ">";
             });
}
