/**
 * @file module.cpp
 * @brief Main nanobind module definition for hqt_core
 *
 * This is the entry point for the Python extension module.
 * All binding functions are declared here and called to register types.
 */

#include <nanobind/nanobind.h>

namespace nb = nanobind;

// Forward declarations of binding functions
void bind_types(nb::module_& m);
void bind_engine(nb::module_& m);
void bind_callbacks(nb::module_& m);
void bind_commands(nb::module_& m);

/**
 * @brief Main module initialization
 *
 * This creates the hqt_core Python module and registers all types,
 * classes, and functions from the C++ backend.
 */
NB_MODULE(hqt_core, m) {
    m.doc() = "HaruQuant Trading System - High-Performance C++ Core";

    // Version information
    m.attr("__version__") = "0.3.0";

    // Bind all types (Tick, Bar, SymbolInfo, etc.)
    bind_types(m);

    // Bind Engine class
    bind_engine(m);

    // Bind callback support
    bind_callbacks(m);

    // Bind trading commands
    bind_commands(m);
}
