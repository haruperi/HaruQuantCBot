/**
 * @file bar.hpp
 * @brief OHLCV bar data structure and timeframe enum
 *
 * Cache-line aligned bar structure for candlestick data.
 * Supports multiple timeframes from M1 to MN1.
 */

#pragma once

#include <cstdint>
#include <string_view>

namespace hqt {

/**
 * @brief Timeframe enumeration with minute values
 *
 * Each enum value represents the timeframe duration in minutes.
 * This allows easy arithmetic comparisons and conversions.
 */
enum class Timeframe : uint8_t {
    M1   = 1,      ///< 1 minute
    M5   = 5,      ///< 5 minutes
    M15  = 15,     ///< 15 minutes
    M30  = 30,     ///< 30 minutes
    H1   = 60,     ///< 1 hour (60 minutes)
    H4   = 240,    ///< 4 hours (240 minutes)
    D1   = 1440,   ///< 1 day (1440 minutes)
    W1   = 10080,  ///< 1 week (10080 minutes)
    MN1  = 43200   ///< 1 month (30 days = 43200 minutes, approximate)
};

/**
 * @brief Convert timeframe to string representation
 * @param tf Timeframe enum value
 * @return String name (e.g., "M1", "H4", "D1")
 */
[[nodiscard]] constexpr std::string_view timeframe_to_string(Timeframe tf) noexcept {
    switch (tf) {
        case Timeframe::M1:  return "M1";
        case Timeframe::M5:  return "M5";
        case Timeframe::M15: return "M15";
        case Timeframe::M30: return "M30";
        case Timeframe::H1:  return "H1";
        case Timeframe::H4:  return "H4";
        case Timeframe::D1:  return "D1";
        case Timeframe::W1:  return "W1";
        case Timeframe::MN1: return "MN1";
        default:             return "UNKNOWN";
    }
}

/**
 * @brief Get timeframe duration in minutes
 * @param tf Timeframe enum value
 * @return Duration in minutes
 */
[[nodiscard]] constexpr int32_t timeframe_minutes(Timeframe tf) noexcept {
    return static_cast<int32_t>(tf);
}

/**
 * @brief OHLCV bar data structure
 *
 * Aligned to 64-byte cache line. Represents a candlestick bar with
 * open, high, low, close prices, volume, and spread information.
 */
struct alignas(64) Bar {
    int64_t timestamp_us;     ///< Bar open time in microseconds since epoch (UTC)
    uint32_t symbol_id;       ///< Symbol lookup index
    Timeframe timeframe;      ///< Bar timeframe (M1, H1, etc.)
    int64_t open;             ///< Open price (fixed-point)
    int64_t high;             ///< High price (fixed-point)
    int64_t low;              ///< Low price (fixed-point)
    int64_t close;            ///< Close price (fixed-point)
    int64_t tick_volume;      ///< Number of ticks in bar
    int64_t real_volume;      ///< Actual traded volume (if available)
    int32_t spread_points;    ///< Average spread in points

    // Padding to align to cache line boundary
    // Current size: 8+4+1+8+8+8+8+8+8+4 = 65 bytes
    // Padding to 128 bytes (2 cache lines) for consistent alignment
    char _padding[63];

    /**
     * @brief Default constructor initializes all fields to zero
     */
    constexpr Bar() noexcept
        : timestamp_us(0)
        , symbol_id(0)
        , timeframe(Timeframe::M1)
        , open(0)
        , high(0)
        , low(0)
        , close(0)
        , tick_volume(0)
        , real_volume(0)
        , spread_points(0)
        , _padding{}
    {}

    /**
     * @brief Construct a bar with all fields
     */
    constexpr Bar(int64_t ts, uint32_t sym_id, Timeframe tf,
                  int64_t o, int64_t h, int64_t l, int64_t c,
                  int64_t tv, int64_t rv, int32_t spread) noexcept
        : timestamp_us(ts)
        , symbol_id(sym_id)
        , timeframe(tf)
        , open(o)
        , high(h)
        , low(l)
        , close(c)
        , tick_volume(tv)
        , real_volume(rv)
        , spread_points(spread)
        , _padding{}
    {}

    /**
     * @brief Check if bar is valid (OHLC relationship holds)
     * @return true if high >= max(open, close) and low <= min(open, close)
     */
    [[nodiscard]] constexpr bool is_valid() const noexcept {
        const int64_t max_oc = (open > close) ? open : close;
        const int64_t min_oc = (open < close) ? open : close;
        return high >= max_oc && low <= min_oc && high >= low;
    }

    /**
     * @brief Check if bar is bullish (close > open)
     */
    [[nodiscard]] constexpr bool is_bullish() const noexcept {
        return close > open;
    }

    /**
     * @brief Check if bar is bearish (close < open)
     */
    [[nodiscard]] constexpr bool is_bearish() const noexcept {
        return close < open;
    }

    /**
     * @brief Get bar range (high - low)
     */
    [[nodiscard]] constexpr int64_t range() const noexcept {
        return high - low;
    }

    /**
     * @brief Get bar body size (abs(close - open))
     */
    [[nodiscard]] constexpr int64_t body() const noexcept {
        return (close > open) ? (close - open) : (open - close);
    }
};

static_assert(sizeof(Bar) == 128, "Bar must be 128 bytes (2 cache lines)");
static_assert(alignof(Bar) == 64, "Bar must be aligned to 64-byte boundary");

} // namespace hqt
