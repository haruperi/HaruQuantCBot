/**
 * @file tick.hpp
 * @brief Tick data structure for market price quotes
 *
 * Cache-line aligned tick structure optimized for high-frequency processing.
 * All prices use fixed-point representation (int64_t scaled by symbol digits).
 */

#pragma once

#include <cstdint>

namespace hqt {

/**
 * @brief Tick data structure representing a single price quote
 *
 * Aligned to 64-byte cache line for optimal CPU cache performance.
 * All monetary values are stored as fixed-point integers to avoid
 * floating-point precision issues in PnL calculations.
 *
 * Example: EURUSD (5 digits): 1.10523 → 110523
 *          XAUUSD (2 digits): 2350.50 → 235050
 */
struct alignas(64) Tick {
    // Group int64_t members together to avoid automatic padding
    int64_t timestamp_us;    ///< Timestamp in microseconds since epoch (UTC)
    int64_t bid;             ///< Bid price (fixed-point: value × 10^digits)
    int64_t ask;             ///< Ask price (fixed-point: value × 10^digits)
    int64_t bid_volume;      ///< Volume available at bid
    int64_t ask_volume;      ///< Volume available at ask
    uint32_t symbol_id;      ///< Symbol lookup index (internal)
    int32_t spread_points;   ///< Spread in points (ask - bid)

    // Padding to fill cache line (64 bytes total)
    // Current size: 8*5 + 4 + 4 = 48 bytes, need 16 bytes padding
    char _padding[16];

    /**
     * @brief Default constructor initializes all fields to zero
     */
    constexpr Tick() noexcept
        : timestamp_us(0)
        , bid(0)
        , ask(0)
        , bid_volume(0)
        , ask_volume(0)
        , symbol_id(0)
        , spread_points(0)
        , _padding{}
    {}

    /**
     * @brief Construct a tick with all fields
     */
    constexpr Tick(int64_t ts, uint32_t sym_id, int64_t b, int64_t a,
                   int64_t bv, int64_t av, int32_t spread) noexcept
        : timestamp_us(ts)
        , bid(b)
        , ask(a)
        , bid_volume(bv)
        , ask_volume(av)
        , symbol_id(sym_id)
        , spread_points(spread)
        , _padding{}
    {}

    /**
     * @brief Check if tick is valid (basic sanity checks)
     * @return true if bid > 0, ask > 0, and ask >= bid
     */
    [[nodiscard]] constexpr bool is_valid() const noexcept {
        return bid > 0 && ask > 0 && ask >= bid;
    }

    /**
     * @brief Get mid price (average of bid and ask)
     * @return Mid price in fixed-point
     */
    [[nodiscard]] constexpr int64_t mid_price() const noexcept {
        return (bid + ask) / 2;
    }
};

static_assert(sizeof(Tick) == 64, "Tick must be exactly 64 bytes (cache-line aligned)");
static_assert(alignof(Tick) == 64, "Tick must be aligned to 64-byte boundary");

} // namespace hqt
