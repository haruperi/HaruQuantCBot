/**
 * @file engine.hpp
 * @brief Main backtesting engine facade
 *
 * Wires together all components: EventLoop, CostsEngine, CTrade, DataFeed,
 * CurrencyConverter, and MarginCalculator into a unified interface.
 */

#pragma once

#include "hqt/core/event_loop.hpp"
#include "hqt/core/global_clock.hpp"
#include "hqt/data/data_feed.hpp"
#include "hqt/data/tick.hpp"
#include "hqt/trading/trade.hpp"
#include "hqt/trading/symbol_info.hpp"
#include "hqt/util/currency_converter.hpp"
#include "hqt/util/margin_calculator.hpp"
#include "hqt/costs/costs_engine.hpp"
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <stdexcept>

namespace hqt {

/**
 * @brief Engine exception
 */
class EngineError : public std::runtime_error {
public:
    explicit EngineError(const std::string& msg) : std::runtime_error(msg) {}
};

/**
 * @brief Callback function types
 */
using OnTickCallback = std::function<void(const Tick&, const SymbolInfo&)>;
using OnBarCallback = std::function<void(const Bar&, const SymbolInfo&, Timeframe)>;
using OnTradeCallback = std::function<void(const DealInfo&)>;
using OnOrderCallback = std::function<void(const OrderInfo&)>;

/**
 * @brief Main backtesting engine
 *
 * Central facade that coordinates all backtesting components:
 * - Event-driven simulation via EventLoop
 * - Market data access via DataFeed
 * - Trading operations via CTrade
 * - Execution costs via CostsEngine
 * - Currency conversion via CurrencyConverter
 * - Margin calculations via MarginCalculator
 *
 * Example:
 * @code
 * Engine engine(10000.0, "USD", 100);
 *
 * // Load symbols
 * engine.load_symbol("EURUSD", eurusd_info);
 * engine.load_conversion_pair("EUR", "USD", 1.10);
 *
 * // Register callbacks
 * engine.set_on_tick([](const Tick& tick, const SymbolInfo& symbol) {
 *     std::cout << "Tick: " << symbol.Name() << " @ " << tick.bid << std::endl;
 * });
 *
 * // Run simulation
 * engine.run();
 * @endcode
 */
class Engine {
private:
    // Core components
    EventLoop event_loop_;
    GlobalClock global_clock_;
    std::unique_ptr<IDataFeed> data_feed_;
    CTrade trade_;
    CurrencyConverter currency_converter_;
    std::unique_ptr<MarginCalculator> margin_calculator_;
    std::unique_ptr<CostsEngine> costs_engine_;

    // Callbacks
    OnTickCallback on_tick_;
    OnBarCallback on_bar_;
    OnTradeCallback on_trade_;
    OnOrderCallback on_order_;

    // Symbols
    std::unordered_map<std::string, SymbolInfo> symbols_;
    std::unordered_map<uint32_t, std::string> symbol_id_to_name_;

    // State
    bool running_;
    bool paused_;
    int64_t current_time_us_;

public:
    /**
     * @brief Construct engine with initial account state
     * @param initial_balance Initial account balance
     * @param currency Account currency (e.g., "USD")
     * @param leverage Account leverage (e.g., 100 for 1:100)
     */
    explicit Engine(double initial_balance = 10000.0,
                   const std::string& currency = "USD",
                   int leverage = 100)
        : event_loop_(),
          global_clock_(),
          data_feed_(std::make_unique<BarDataFeed>()),
          trade_(initial_balance, currency, leverage),
          currency_converter_(),
          margin_calculator_(std::make_unique<MarginCalculator>(currency_converter_)),
          costs_engine_(nullptr),
          on_tick_(),
          on_bar_(),
          on_trade_(),
          on_order_(),
          symbols_(),
          symbol_id_to_name_(),
          running_(false),
          paused_(false),
          current_time_us_(0) {
        // Initialize with default zero-cost models
        costs_engine_ = std::make_unique<CostsEngine>(
            std::make_unique<ZeroSlippage>(),
            std::make_unique<ZeroCommission>(),
            std::make_unique<ZeroSwap>(),
            std::make_unique<FixedSpread>(15)  // Default 1.5 pip spread
        );
    }

    // ========================================================================
    // Configuration
    // ========================================================================

    /**
     * @brief Load symbol into engine
     * @param symbol_name Symbol name (e.g., "EURUSD")
     * @param symbol_info Symbol information
     */
    void load_symbol(const std::string& symbol_name, const SymbolInfo& symbol_info) {
        symbols_[symbol_name] = symbol_info;
        symbol_id_to_name_[symbol_info.SymbolId()] = symbol_name;
        trade_.RegisterSymbol(symbol_info);
    }

    /**
     * @brief Load currency conversion pair
     * @param base Base currency (e.g., "EUR")
     * @param quote Quote currency (e.g., "USD")
     * @param rate Exchange rate (1 base = rate quote)
     */
    void load_conversion_pair(const std::string& base,
                             const std::string& quote,
                             double rate) {
        currency_converter_.register_pair(base, quote, rate);
    }

    /**
     * @brief Set execution cost models
     * @param slippage Slippage model
     * @param commission Commission model
     * @param swap Swap model
     * @param spread Spread model
     */
    void set_cost_models(std::unique_ptr<ISlippageModel> slippage,
                        std::unique_ptr<ICommissionModel> commission,
                        std::unique_ptr<ISwapModel> swap,
                        std::unique_ptr<ISpreadModel> spread) {
        costs_engine_ = std::make_unique<CostsEngine>(
            std::move(slippage),
            std::move(commission),
            std::move(swap),
            std::move(spread)
        );
    }

    /**
     * @brief Set data feed (replaces default BarDataFeed)
     * @param feed Data feed implementation
     */
    void set_data_feed(std::unique_ptr<IDataFeed> feed) {
        data_feed_ = std::move(feed);
    }

    // ========================================================================
    // Callbacks
    // ========================================================================

    /**
     * @brief Register callback for tick events
     * @param callback Function called on each tick
     */
    void set_on_tick(OnTickCallback callback) {
        on_tick_ = std::move(callback);
    }

    /**
     * @brief Register callback for bar close events
     * @param callback Function called when bar closes
     */
    void set_on_bar(OnBarCallback callback) {
        on_bar_ = std::move(callback);
    }

    /**
     * @brief Register callback for trade events
     * @param callback Function called when deal is executed
     */
    void set_on_trade(OnTradeCallback callback) {
        on_trade_ = std::move(callback);
    }

    /**
     * @brief Register callback for order events
     * @param callback Function called when order state changes
     */
    void set_on_order(OnOrderCallback callback) {
        on_order_ = std::move(callback);
    }

    // ========================================================================
    // Event Loop Control
    // ========================================================================

    /**
     * @brief Run simulation until all events processed
     */
    void run() {
        running_ = true;
        paused_ = false;

        event_loop_.run([this](const Event& event) {
            if (!running_) return false;
            if (paused_) return true;  // Continue but don't process

            process_event(event);
            return true;
        });

        running_ = false;
    }

    /**
     * @brief Run N simulation steps
     * @param steps Number of events to process
     * @return Number of events actually processed
     */
    size_t run_steps(size_t steps) {
        running_ = true;
        paused_ = false;

        size_t processed = event_loop_.step(steps, [this](const Event& event) {
            if (!running_) return false;
            if (paused_) return true;

            process_event(event);
            return true;
        });

        return processed;
    }

    /**
     * @brief Pause simulation (can be resumed)
     */
    void pause() noexcept {
        paused_ = true;
    }

    /**
     * @brief Resume paused simulation
     */
    void resume() noexcept {
        paused_ = false;
    }

    /**
     * @brief Stop simulation completely
     */
    void stop() noexcept {
        running_ = false;
    }

    /**
     * @brief Check if engine is running
     */
    bool is_running() const noexcept {
        return running_;
    }

    /**
     * @brief Check if engine is paused
     */
    bool is_paused() const noexcept {
        return paused_;
    }

    // ========================================================================
    // Trading Commands (with margin checks)
    // ========================================================================

    /**
     * @brief Open BUY position
     * @param volume Volume in lots
     * @param symbol Symbol name
     * @param sl Stop loss (0 = none)
     * @param tp Take profit (0 = none)
     * @param comment Order comment
     * @return True if successful
     */
    bool buy(double volume,
            const std::string& symbol,
            double sl = 0.0,
            double tp = 0.0,
            const std::string& comment = "") {
        // Margin check
        if (!check_margin_for_order(symbol, volume)) {
            return false;
        }

        return trade_.Buy(volume, symbol, 0.0, sl, tp, comment);
    }

    /**
     * @brief Open SELL position
     * @param volume Volume in lots
     * @param symbol Symbol name
     * @param sl Stop loss (0 = none)
     * @param tp Take profit (0 = none)
     * @param comment Order comment
     * @return True if successful
     */
    bool sell(double volume,
             const std::string& symbol,
             double sl = 0.0,
             double tp = 0.0,
             const std::string& comment = "") {
        // Margin check
        if (!check_margin_for_order(symbol, volume)) {
            return false;
        }

        return trade_.Sell(volume, symbol, 0.0, sl, tp, comment);
    }

    /**
     * @brief Modify position SL/TP
     * @param ticket Position ticket
     * @param sl New stop loss
     * @param tp New take profit
     * @return True if successful
     */
    bool modify(uint64_t ticket, double sl, double tp) {
        return trade_.PositionModify(ticket, sl, tp);
    }

    /**
     * @brief Close position
     * @param ticket Position ticket
     * @return True if successful
     */
    bool close(uint64_t ticket) {
        return trade_.PositionClose(ticket);
    }

    /**
     * @brief Cancel pending order
     * @param ticket Order ticket
     * @return True if successful
     */
    bool cancel(uint64_t ticket) {
        return trade_.OrderDelete(ticket);
    }

    // ========================================================================
    // State Access
    // ========================================================================

    /**
     * @brief Get account info
     */
    const AccountInfo& account() const noexcept {
        return trade_.Account();
    }

    /**
     * @brief Get all open positions
     */
    std::vector<PositionInfo> positions() const {
        return trade_.GetPositions();
    }

    /**
     * @brief Get all pending orders
     */
    std::vector<OrderInfo> orders() const {
        return trade_.GetOrders();
    }

    /**
     * @brief Get all deals
     */
    const std::vector<DealInfo>& deals() const {
        return trade_.GetDeals();
    }

    /**
     * @brief Get symbol info
     * @param symbol_name Symbol name
     * @return Const pointer to symbol info, or nullptr if not found
     */
    const SymbolInfo* get_symbol(const std::string& symbol_name) const noexcept {
        auto it = symbols_.find(symbol_name);
        return (it != symbols_.end()) ? &it->second : nullptr;
    }

    /**
     * @brief Get data feed
     */
    IDataFeed& data_feed() noexcept {
        return *data_feed_;
    }

    const IDataFeed& data_feed() const noexcept {
        return *data_feed_;
    }

    /**
     * @brief Get current simulation timestamp
     */
    int64_t current_time() const noexcept {
        return current_time_us_;
    }

    /**
     * @brief Get event loop
     */
    EventLoop& event_loop() noexcept {
        return event_loop_;
    }

    const EventLoop& event_loop() const noexcept {
        return event_loop_;
    }

private:
    /**
     * @brief Process a single event
     */
    void process_event(const Event& event) {
        current_time_us_ = event.timestamp_us;

        switch (event.type) {
            case EventType::TICK: {
                auto symbol_name_it = symbol_id_to_name_.find(event.symbol_id);
                if (symbol_name_it == symbol_id_to_name_.end()) break;

                auto symbol_it = symbols_.find(symbol_name_it->second);
                if (symbol_it == symbols_.end()) break;

                // Create tick from event data
                Tick tick{
                    event.timestamp_us,
                    event.symbol_id,
                    event.data1,  // bid
                    event.data2,  // ask
                    0, 0, 0  // volumes and spread (not stored in event)
                };

                // Update symbol prices
                trade_.UpdatePrices(symbol_it->second.Name(),
                                  static_cast<double>(tick.bid) / 1e6,
                                  static_cast<double>(tick.ask) / 1e6,
                                  tick.timestamp_us);

                // Invoke callback
                if (on_tick_) {
                    on_tick_(tick, symbol_it->second);
                }
                break;
            }

            case EventType::BAR_CLOSE: {
                auto symbol_name_it = symbol_id_to_name_.find(event.symbol_id);
                if (symbol_name_it == symbol_id_to_name_.end()) break;

                auto symbol_it = symbols_.find(symbol_name_it->second);
                if (symbol_it == symbols_.end()) break;

                // Get bar from data feed
                try {
                    Timeframe tf = static_cast<Timeframe>(event.timeframe);
                    Bar bar = data_feed_->get_last_bar(symbol_it->second.Name(), tf, event.timestamp_us);

                    // Invoke callback
                    if (on_bar_) {
                        on_bar_(bar, symbol_it->second, tf);
                    }
                } catch (const DataFeedError&) {
                    // Bar not available - skip
                }
                break;
            }

            case EventType::ORDER_TRIGGER:
            case EventType::TIMER:
                // Not implemented yet
                break;
        }

        // Update global clock
        global_clock_.update_symbol_time(event.symbol_id, event.timestamp_us);
    }

    /**
     * @brief Check if sufficient margin for new order
     */
    bool check_margin_for_order(const std::string& symbol, double volume) {
        auto symbol_it = symbols_.find(symbol);
        if (symbol_it == symbols_.end()) return false;

        const SymbolInfo& symbol_info = symbol_it->second;

        // Calculate required margin
        double price = symbol_info.Ask();  // Use ask for margin calculation
        double margin = margin_calculator_->required_margin(
            symbol_info,
            ENUM_POSITION_TYPE::POSITION_TYPE_BUY,
            volume,
            price,
            trade_.Account().Leverage()
        );

        // Check if sufficient margin
        auto positions = trade_.GetPositions();
        std::unordered_map<std::string, SymbolInfo> symbols_map(symbols_.begin(), symbols_.end());

        return margin_calculator_->has_sufficient_margin(
            trade_.Account(),
            positions,
            symbols_map,
            margin,
            100.0  // Min 100% margin level
        );
    }
};

} // namespace hqt
