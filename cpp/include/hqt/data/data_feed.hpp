/**
 * @file data_feed.hpp
 * @brief Data feed interfaces with Point-In-Time (PIT) safety
 *
 * Provides time-aware data access ensuring backtesting never looks into the future.
 * All queries are PIT-safe by construction.
 */

#pragma once

#include "hqt/data/tick.hpp"
#include "hqt/data/bar.hpp"
#include "hqt/core/event.hpp"
#include <vector>
#include <string>
#include <memory>
#include <unordered_map>
#include <stdexcept>

namespace hqt {

/**
 * @brief Exception for data feed errors
 */
class DataFeedError : public std::runtime_error {
public:
    explicit DataFeedError(const std::string& msg) : std::runtime_error(msg) {}
};

/**
 * @brief Data feed interface for time-series data access
 *
 * All methods are Point-In-Time (PIT) safe - they only return data
 * that would have been available at the specified timestamp.
 */
class IDataFeed {
public:
    virtual ~IDataFeed() = default;

    /**
     * @brief Load symbol data into the feed
     * @param symbol Symbol name (e.g., "EURUSD")
     * @param timeframe Timeframe (e.g., Timeframe::M1)
     * @return Number of bars loaded
     */
    virtual size_t load_symbol(const std::string& symbol, Timeframe timeframe) = 0;

    /**
     * @brief Get bars available at or before timestamp (PIT-safe)
     * @param symbol Symbol name
     * @param timeframe Timeframe
     * @param timestamp_us Maximum timestamp (microseconds)
     * @param max_bars Maximum number of bars to return (0 = all)
     * @return Vector of bars, newest first
     * @throws DataFeedError if symbol/timeframe not loaded
     */
    virtual std::vector<Bar> get_bars(const std::string& symbol,
                                      Timeframe timeframe,
                                      int64_t timestamp_us,
                                      size_t max_bars = 0) const = 0;

    /**
     * @brief Get last bar at or before timestamp (PIT-safe)
     * @param symbol Symbol name
     * @param timeframe Timeframe
     * @param timestamp_us Maximum timestamp
     * @return Last available bar
     * @throws DataFeedError if no data available
     */
    virtual Bar get_last_bar(const std::string& symbol,
                            Timeframe timeframe,
                            int64_t timestamp_us) const = 0;

    /**
     * @brief Check if symbol/timeframe data is loaded
     * @param symbol Symbol name
     * @param timeframe Timeframe
     * @return True if data is available
     */
    virtual bool has_data(const std::string& symbol, Timeframe timeframe) const noexcept = 0;

    /**
     * @brief Get total number of bars for symbol/timeframe
     * @param symbol Symbol name
     * @param timeframe Timeframe
     * @return Total bars loaded (0 if not loaded)
     */
    virtual size_t get_bar_count(const std::string& symbol, Timeframe timeframe) const noexcept = 0;

    /**
     * @brief Get timestamp range for loaded data
     * @param symbol Symbol name
     * @param timeframe Timeframe
     * @return Pair of (start_timestamp_us, end_timestamp_us)
     * @throws DataFeedError if symbol/timeframe not loaded
     */
    virtual std::pair<int64_t, int64_t> get_time_range(const std::string& symbol,
                                                        Timeframe timeframe) const = 0;
};

/**
 * @brief In-memory bar data feed with PIT access
 *
 * Stores bar data in memory and provides fast PIT-safe lookups.
 * Uses binary search for timestamp queries.
 *
 * Example:
 * @code
 * BarDataFeed feed;
 * feed.load_symbol("EURUSD", Timeframe::M1);
 *
 * // Get last 100 bars available at timestamp
 * auto bars = feed.get_bars("EURUSD", Timeframe::M1, current_time, 100);
 * @endcode
 */
class BarDataFeed : public IDataFeed {
private:
    // Key: "SYMBOL_TIMEFRAME" (e.g., "EURUSD_1")
    std::unordered_map<std::string, std::vector<Bar>> data_;

    /**
     * @brief Create lookup key for symbol/timeframe
     */
    static std::string make_key(const std::string& symbol, Timeframe timeframe) {
        return symbol + "_" + std::to_string(static_cast<uint16_t>(timeframe));
    }

    /**
     * @brief Find index of last bar at or before timestamp using binary search
     * @return Index in vector, or -1 if no bars available
     */
    int64_t find_last_index(const std::vector<Bar>& bars, int64_t timestamp_us) const noexcept {
        if (bars.empty()) return -1;

        // Binary search for last bar <= timestamp
        int64_t left = 0;
        int64_t right = static_cast<int64_t>(bars.size()) - 1;
        int64_t result = -1;

        while (left <= right) {
            int64_t mid = left + (right - left) / 2;
            if (bars[mid].timestamp_us <= timestamp_us) {
                result = mid;
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }

        return result;
    }

public:
    BarDataFeed() = default;

    /**
     * @brief Load bars from vector (copies data)
     * @param symbol Symbol name
     * @param timeframe Timeframe
     * @param bars Vector of bars (must be sorted by timestamp ascending)
     * @return Number of bars loaded
     */
    size_t load_bars(const std::string& symbol, Timeframe timeframe, const std::vector<Bar>& bars) {
        std::string key = make_key(symbol, timeframe);
        data_[key] = bars;
        return bars.size();
    }

    /**
     * @brief Load bars from vector (moves data)
     * @param symbol Symbol name
     * @param timeframe Timeframe
     * @param bars Vector of bars (must be sorted by timestamp ascending)
     * @return Number of bars loaded
     */
    size_t load_bars(const std::string& symbol, Timeframe timeframe, std::vector<Bar>&& bars) {
        std::string key = make_key(symbol, timeframe);
        size_t count = bars.size();
        data_[key] = std::move(bars);
        return count;
    }

    // IDataFeed implementation

    size_t load_symbol(const std::string& symbol, Timeframe timeframe) override {
        // This method would load from external source (file, database, etc.)
        // For now, data must be loaded via load_bars()
        std::string key = make_key(symbol, timeframe);
        auto it = data_.find(key);
        return (it != data_.end()) ? it->second.size() : 0;
    }

    std::vector<Bar> get_bars(const std::string& symbol,
                              Timeframe timeframe,
                              int64_t timestamp_us,
                              size_t max_bars = 0) const override {
        std::string key = make_key(symbol, timeframe);
        auto it = data_.find(key);
        if (it == data_.end()) {
            throw DataFeedError("Data not loaded for " + key);
        }

        const auto& bars = it->second;
        int64_t last_idx = find_last_index(bars, timestamp_us);

        if (last_idx < 0) {
            return {};  // No bars available at this timestamp
        }

        // Calculate how many bars to return
        size_t count = (max_bars == 0) ? (last_idx + 1) : std::min(max_bars, static_cast<size_t>(last_idx + 1));
        size_t start_idx = last_idx + 1 - count;

        // Return bars in reverse order (newest first)
        std::vector<Bar> result;
        result.reserve(count);
        for (int64_t i = last_idx; i >= static_cast<int64_t>(start_idx); --i) {
            result.push_back(bars[i]);
        }

        return result;
    }

    Bar get_last_bar(const std::string& symbol,
                    Timeframe timeframe,
                    int64_t timestamp_us) const override {
        std::string key = make_key(symbol, timeframe);
        auto it = data_.find(key);
        if (it == data_.end()) {
            throw DataFeedError("Data not loaded for " + key);
        }

        const auto& bars = it->second;
        int64_t last_idx = find_last_index(bars, timestamp_us);

        if (last_idx < 0) {
            throw DataFeedError("No data available at timestamp " + std::to_string(timestamp_us));
        }

        return bars[last_idx];
    }

    bool has_data(const std::string& symbol, Timeframe timeframe) const noexcept override {
        std::string key = make_key(symbol, timeframe);
        auto it = data_.find(key);
        return it != data_.end() && !it->second.empty();
    }

    size_t get_bar_count(const std::string& symbol, Timeframe timeframe) const noexcept override {
        std::string key = make_key(symbol, timeframe);
        auto it = data_.find(key);
        return (it != data_.end()) ? it->second.size() : 0;
    }

    std::pair<int64_t, int64_t> get_time_range(const std::string& symbol,
                                                Timeframe timeframe) const override {
        std::string key = make_key(symbol, timeframe);
        auto it = data_.find(key);
        if (it == data_.end() || it->second.empty()) {
            throw DataFeedError("Data not loaded for " + key);
        }

        const auto& bars = it->second;
        return {bars.front().timestamp_us, bars.back().timestamp_us};
    }

    /**
     * @brief Get direct access to bar vector (for testing/advanced use)
     * @return Const reference to bars, or nullptr if not loaded
     */
    const std::vector<Bar>* get_bars_direct(const std::string& symbol, Timeframe timeframe) const noexcept {
        std::string key = make_key(symbol, timeframe);
        auto it = data_.find(key);
        return (it != data_.end()) ? &it->second : nullptr;
    }

    /**
     * @brief Clear all loaded data
     */
    void clear() noexcept {
        data_.clear();
    }

    /**
     * @brief Get total memory usage estimate in bytes
     */
    size_t memory_usage() const noexcept {
        size_t total = 0;
        for (const auto& [key, bars] : data_) {
            total += key.size() + bars.size() * sizeof(Bar);
        }
        return total;
    }
};

} // namespace hqt
