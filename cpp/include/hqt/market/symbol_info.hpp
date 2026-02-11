/**
 * @file symbol_info.hpp
 * @brief Symbol specification data structure
 *
 * Complete specification for a trading symbol including contract details,
 * margin requirements, swap rates, and trading constraints.
 */

#pragma once

#include <cstdint>
#include <string>

namespace hqt {

/**
 * @brief Swap calculation type
 */
enum class SwapType : uint8_t {
    POINTS      = 0,  ///< Swap in points
    PERCENTAGE  = 1,  ///< Swap as percentage of contract value
    MONEY       = 2   ///< Swap in account currency
};

/**
 * @brief Symbol trading mode
 */
enum class TradeMode : uint8_t {
    DISABLED    = 0,  ///< Trading disabled
    LONG_ONLY   = 1,  ///< Long positions only
    SHORT_ONLY  = 2,  ///< Short positions only
    CLOSE_ONLY  = 3,  ///< Close only, no new positions
    FULL        = 4   ///< Full trading enabled
};

/**
 * @brief Complete symbol specification
 *
 * Contains all information needed for:
 * - Price formatting and validation
 * - Position sizing calculations
 * - Margin requirements
 * - Swap/rollover calculations
 * - Contract value conversions
 * - Trading constraint enforcement
 */
struct SymbolInfo {
    // Identification
    std::string name;           ///< Symbol name (e.g., "EURUSD", "XAUUSD")
    std::string description;    ///< Human-readable description
    uint32_t symbol_id;         ///< Internal symbol ID for fast lookups

    // Price formatting
    int32_t digits;             ///< Number of decimal places (e.g., 5 for EURUSD, 2 for XAUUSD)
    double point;               ///< Minimal price change (e.g., 0.00001 for 5-digit EURUSD)
    double tick_size;           ///< Minimal price change in points
    double tick_value;          ///< Profit/loss for 1 lot and 1 tick movement

    // Contract specifications
    double contract_size;       ///< Contract size in base currency (e.g., 100000 for standard lot)

    // Margin requirements
    double margin_initial;      ///< Initial margin percentage (or fixed amount)
    double margin_maintenance;  ///< Maintenance margin percentage

    // Swap (rollover) rates
    double swap_long;           ///< Swap for long positions (per lot, per day)
    double swap_short;          ///< Swap for short positions (per lot, per day)
    SwapType swap_type;         ///< How swap is calculated

    // Trading constraints
    TradeMode trade_mode;       ///< Trading restrictions
    double volume_min;          ///< Minimum volume (lots)
    double volume_max;          ///< Maximum volume (lots)
    double volume_step;         ///< Volume step (lot size increment)

    // Currency information
    std::string currency_base;      ///< Base currency (e.g., "EUR" in EURUSD)
    std::string currency_profit;    ///< Profit currency (e.g., "USD" in EURUSD)
    std::string currency_margin;    ///< Margin currency

    /**
     * @brief Default constructor
     */
    SymbolInfo()
        : name()
        , description()
        , symbol_id(0)
        , digits(0)
        , point(0.0)
        , tick_size(0.0)
        , tick_value(0.0)
        , contract_size(0.0)
        , margin_initial(0.0)
        , margin_maintenance(0.0)
        , swap_long(0.0)
        , swap_short(0.0)
        , swap_type(SwapType::POINTS)
        , trade_mode(TradeMode::FULL)
        , volume_min(0.0)
        , volume_max(0.0)
        , volume_step(0.0)
        , currency_base()
        , currency_profit()
        , currency_margin()
    {}

    /**
     * @brief Check if trading is allowed
     * @return true if new positions can be opened
     */
    [[nodiscard]] bool can_trade() const noexcept {
        return trade_mode == TradeMode::FULL ||
               trade_mode == TradeMode::LONG_ONLY ||
               trade_mode == TradeMode::SHORT_ONLY;
    }

    /**
     * @brief Check if long positions are allowed
     */
    [[nodiscard]] bool can_trade_long() const noexcept {
        return trade_mode == TradeMode::FULL || trade_mode == TradeMode::LONG_ONLY;
    }

    /**
     * @brief Check if short positions are allowed
     */
    [[nodiscard]] bool can_trade_short() const noexcept {
        return trade_mode == TradeMode::FULL || trade_mode == TradeMode::SHORT_ONLY;
    }

    /**
     * @brief Validate and round volume to valid step
     * @param volume Requested volume
     * @return Rounded volume clamped to [volume_min, volume_max]
     */
    [[nodiscard]] double validate_volume(double volume) const noexcept {
        // Clamp to range
        if (volume < volume_min) volume = volume_min;
        if (volume > volume_max) volume = volume_max;

        // Round to step
        if (volume_step > 0.0) {
            volume = std::round(volume / volume_step) * volume_step;
        }

        return volume;
    }

    /**
     * @brief Convert fixed-point price to double
     * @param fixed_price Price as int64_t (value × 10^digits)
     * @return Price as double
     */
    [[nodiscard]] double fixed_to_double(int64_t fixed_price) const noexcept {
        double divisor = 1.0;
        for (int32_t i = 0; i < digits; ++i) {
            divisor *= 10.0;
        }
        return static_cast<double>(fixed_price) / divisor;
    }

    /**
     * @brief Convert double price to fixed-point
     * @param price Price as double
     * @return Price as int64_t (value × 10^digits)
     */
    [[nodiscard]] int64_t double_to_fixed(double price) const noexcept {
        double multiplier = 1.0;
        for (int32_t i = 0; i < digits; ++i) {
            multiplier *= 10.0;
        }
        return static_cast<int64_t>(price * multiplier + 0.5);
    }
};

} // namespace hqt
