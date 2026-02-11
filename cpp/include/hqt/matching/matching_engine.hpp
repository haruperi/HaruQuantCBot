/**
 * @file matching_engine.hpp
 * @brief Order matching and execution engine
 *
 * Evaluates pending orders against market ticks and executes fills.
 * Applies slippage, commission, and spread models.
 * Handles gap scenarios (fills at gap price if price jumps past SL/TP).
 *
 * Performance target: Process orders in O(n) time per tick where n = pending orders
 */

#pragma once

#include "hqt/data/tick.hpp"
#include "hqt/market/symbol_info.hpp"
#include "hqt/matching/slippage_model.hpp"
#include "hqt/matching/commission_model.hpp"
#include "hqt/matching/swap_model.hpp"
#include "hqt/matching/spread_model.hpp"
#include <memory>
#include <vector>
#include <random>
#include <stdexcept>

namespace hqt {

/**
 * @brief Order execution result
 */
struct ExecutionResult {
    bool executed;              ///< Whether order was executed
    int64_t fill_price;         ///< Actual fill price (fixed-point)
    int64_t slippage;           ///< Slippage applied (fixed-point)
    int64_t commission;         ///< Commission charged (account currency, fixed-point)
    int64_t spread_cost;        ///< Cost due to spread (fixed-point)

    ExecutionResult() noexcept
        : executed(false), fill_price(0), slippage(0), commission(0), spread_cost(0) {}
};

/**
 * @brief Pending order representation
 */
struct PendingOrder {
    uint64_t ticket;            ///< Unique order ticket
    uint32_t symbol_id;         ///< Symbol identifier
    OrderType type;             ///< Order type (LIMIT, STOP, etc.)
    OrderSide side;             ///< Buy or sell
    double volume;              ///< Order volume in lots
    int64_t price;              ///< Order trigger price (fixed-point)
    int64_t sl;                 ///< Stop loss (0 if none)
    int64_t tp;                 ///< Take profit (0 if none)
    int64_t timestamp_us;       ///< Order placement timestamp
};

/**
 * @brief Open position representation
 */
struct Position {
    uint64_t ticket;            ///< Position ticket
    uint32_t symbol_id;         ///< Symbol identifier
    OrderSide side;             ///< Long (BUY) or short (SELL)
    double volume;              ///< Position volume in lots
    int64_t open_price;         ///< Entry price (fixed-point)
    int64_t sl;                 ///< Stop loss (0 if none)
    int64_t tp;                 ///< Take profit (0 if none)
    int64_t open_time_us;       ///< Position open timestamp
    int64_t commission;         ///< Commission paid (fixed-point)
    int64_t swap;               ///< Accumulated swap (fixed-point)
};

/**
 * @brief Matching engine with execution models
 *
 * Evaluates pending orders and open positions against new market data.
 * Calculates realistic fills using slippage, commission, and spread models.
 *
 * Example:
 * @code
 * MatchingEngine engine(
 *     std::make_unique<FixedSlippage>(2),
 *     std::make_unique<FixedPerLot>(7.0),
 *     std::make_unique<StandardSwap>(-0.5, 0.3, SwapType::POINTS),
 *     std::make_unique<FixedSpread>(15)
 * );
 *
 * // Check if order triggers and execute
 * auto result = engine.evaluate_order(order, tick, symbol_info);
 * if (result.executed) {
 *     // Order filled at result.fill_price
 * }
 * @endcode
 */
class MatchingEngine {
private:
    std::unique_ptr<ISlippageModel> slippage_model_;
    std::unique_ptr<ICommissionModel> commission_model_;
    std::unique_ptr<ISwapModel> swap_model_;
    std::unique_ptr<ISpreadModel> spread_model_;
    mutable std::mt19937_64 rng_;

    // Last known prices for gap detection
    struct LastPrice {
        int64_t bid;
        int64_t ask;
        int64_t timestamp_us;
    };
    mutable std::unordered_map<uint32_t, LastPrice> last_prices_;

public:
    /**
     * @brief Construct matching engine with execution models
     * @param slippage Slippage model
     * @param commission Commission model
     * @param swap Swap model
     * @param spread Spread model
     * @param seed Random seed for deterministic execution (default: 0)
     */
    MatchingEngine(std::unique_ptr<ISlippageModel> slippage,
                   std::unique_ptr<ICommissionModel> commission,
                   std::unique_ptr<ISwapModel> swap,
                   std::unique_ptr<ISpreadModel> spread,
                   uint64_t seed = 0)
        : slippage_model_(std::move(slippage)),
          commission_model_(std::move(commission)),
          swap_model_(std::move(swap)),
          spread_model_(std::move(spread)),
          rng_(seed),
          last_prices_() {
        if (!slippage_model_ || !commission_model_ || !swap_model_ || !spread_model_) {
            throw std::invalid_argument("All execution models must be provided");
        }
    }

    /**
     * @brief Update market prices (for gap detection)
     * @param symbol_id Symbol identifier
     * @param tick Current tick
     */
    void update_market(uint32_t symbol_id, const Tick& tick) {
        last_prices_[symbol_id] = {tick.bid, tick.ask, tick.timestamp_us};
    }

    /**
     * @brief Check if order should trigger and execute
     * @param order Pending order
     * @param tick Current market tick
     * @param info Symbol information
     * @return Execution result
     */
    ExecutionResult evaluate_order(const PendingOrder& order, const Tick& tick,
                                   const SymbolInfo& info) {
        ExecutionResult result;

        // Check if order triggers
        bool triggers = false;
        int64_t trigger_price = 0;

        switch (order.type) {
            case OrderType::MARKET:
                // Market orders always execute immediately
                triggers = true;
                trigger_price = (order.side == OrderSide::BUY) ? tick.ask : tick.bid;
                break;

            case OrderType::LIMIT:
                // Limit buy triggers when ask <= limit price
                // Limit sell triggers when bid >= limit price
                if (order.side == OrderSide::BUY && tick.ask <= order.price) {
                    triggers = true;
                    trigger_price = order.price;  // Fill at limit price (or better)
                } else if (order.side == OrderSide::SELL && tick.bid >= order.price) {
                    triggers = true;
                    trigger_price = order.price;
                }
                break;

            case OrderType::STOP:
                // Stop buy triggers when ask >= stop price
                // Stop sell triggers when bid <= stop price
                if (order.side == OrderSide::BUY && tick.ask >= order.price) {
                    triggers = true;
                    trigger_price = tick.ask;  // Fill at market price (gap scenario)
                } else if (order.side == OrderSide::SELL && tick.bid <= order.price) {
                    triggers = true;
                    trigger_price = tick.bid;
                }
                break;

            case OrderType::STOP_LIMIT:
                // Stop-limit triggers like stop but becomes limit order
                // Simplified: treat as stop order for backtesting
                if (order.side == OrderSide::BUY && tick.ask >= order.price) {
                    triggers = true;
                    trigger_price = std::min(tick.ask, order.price);
                } else if (order.side == OrderSide::SELL && tick.bid <= order.price) {
                    triggers = true;
                    trigger_price = std::max(tick.bid, order.price);
                }
                break;
        }

        if (!triggers) {
            return result;  // Order did not trigger
        }

        // Calculate execution price with slippage and spread
        result.executed = true;
        result.slippage = slippage_model_->calculate(order.side, order.volume, tick, info, rng_);
        result.spread_cost = spread_model_->calculate(tick, info, tick.timestamp_us, rng_);

        // Apply slippage to trigger price
        if (order.side == OrderSide::BUY) {
            result.fill_price = trigger_price + result.slippage;
        } else {
            result.fill_price = trigger_price - result.slippage;
        }

        // Calculate commission
        result.commission = commission_model_->calculate(order.side, order.volume,
                                                        result.fill_price, info);

        return result;
    }

    /**
     * @brief Check if position stop loss or take profit triggers
     * @param position Open position
     * @param tick Current market tick
     * @param info Symbol information
     * @return Execution result (executed=true if SL/TP hit)
     */
    ExecutionResult evaluate_position(const Position& position, const Tick& tick,
                                     const SymbolInfo& info) {
        ExecutionResult result;

        bool triggers = false;
        int64_t trigger_price = 0;
        OrderSide close_side = (position.side == OrderSide::BUY) ? OrderSide::SELL : OrderSide::BUY;

        if (position.side == OrderSide::BUY) {
            // Long position: check SL (below) and TP (above)
            if (position.sl > 0 && tick.bid <= position.sl) {
                // Stop loss hit
                triggers = true;
                trigger_price = std::min(tick.bid, position.sl);  // Gap scenario
            } else if (position.tp > 0 && tick.bid >= position.tp) {
                // Take profit hit
                triggers = true;
                trigger_price = std::max(tick.bid, position.tp);  // Gap scenario
            }
        } else {
            // Short position: check SL (above) and TP (below)
            if (position.sl > 0 && tick.ask >= position.sl) {
                // Stop loss hit
                triggers = true;
                trigger_price = std::max(tick.ask, position.sl);  // Gap scenario
            } else if (position.tp > 0 && tick.ask <= position.tp) {
                // Take profit hit
                triggers = true;
                trigger_price = std::min(tick.ask, position.tp);  // Gap scenario
            }
        }

        if (!triggers) {
            return result;  // Position exits not triggered
        }

        // Calculate close execution
        result.executed = true;
        result.slippage = slippage_model_->calculate(close_side, position.volume, tick, info, rng_);
        result.spread_cost = spread_model_->calculate(tick, info, tick.timestamp_us, rng_);

        // Apply slippage to trigger price
        if (close_side == OrderSide::BUY) {
            result.fill_price = trigger_price + result.slippage;
        } else {
            result.fill_price = trigger_price - result.slippage;
        }

        // Calculate commission on close
        result.commission = commission_model_->calculate(close_side, position.volume,
                                                        result.fill_price, info);

        return result;
    }

    /**
     * @brief Execute market order immediately
     * @param side Buy or sell
     * @param volume Order volume in lots
     * @param tick Current market tick
     * @param info Symbol information
     * @return Execution result
     */
    ExecutionResult execute_market_order(OrderSide side, double volume, const Tick& tick,
                                        const SymbolInfo& info) {
        PendingOrder order{};
        order.type = OrderType::MARKET;
        order.side = side;
        order.volume = volume;
        order.timestamp_us = tick.timestamp_us;

        return evaluate_order(order, tick, info);
    }

    /**
     * @brief Calculate daily swap charges for position
     * @param position Open position
     * @param current_price Current market price
     * @param info Symbol information
     * @param timestamp_us Current timestamp
     * @return Swap charges in account currency (fixed-point)
     */
    int64_t calculate_swap(const Position& position, int64_t current_price,
                          const SymbolInfo& info, int64_t timestamp_us) const {
        if (!swap_model_->should_apply(timestamp_us)) {
            return 0;
        }

        // Calculate days held
        int64_t duration_us = timestamp_us - position.open_time_us;
        int days_held = static_cast<int>(duration_us / (24LL * 3600LL * 1'000'000LL));

        if (days_held == 0) {
            return 0;
        }

        // Apply swap multiplier (3x on Wednesday)
        int multiplier = swap_model_->get_multiplier(timestamp_us);

        int64_t swap = swap_model_->calculate(position.side, position.volume,
                                             position.open_price, current_price,
                                             info, days_held);

        return swap * multiplier;
    }

    /**
     * @brief Reset RNG seed for deterministic execution
     * @param seed New random seed
     */
    void set_seed(uint64_t seed) {
        rng_.seed(seed);
    }
};

} // namespace hqt
