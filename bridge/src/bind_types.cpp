/**
 * @file bind_types.cpp
 * @brief Nanobind bindings for C++ data structures
 *
 * Exposes market data types (Tick, Bar), symbol info, account state,
 * positions, orders, and deals to Python as read-only or immutable types.
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "hqt/data/tick.hpp"
#include "hqt/data/bar.hpp"
#include "hqt/trading/symbol_info.hpp"
#include "hqt/trading/account_info.hpp"
#include "hqt/trading/position_info.hpp"
#include "hqt/trading/order_info.hpp"
#include "hqt/trading/deal_info.hpp"

namespace nb = nanobind;
using namespace hqt;

void bind_types(nb::module_& m) {
    // ========================================================================
    // Enums
    // ========================================================================

    nb::enum_<Timeframe>(m, "Timeframe", "Bar timeframe enumeration")
        .value("TICK", Timeframe::TICK)
        .value("M1", Timeframe::M1)
        .value("M5", Timeframe::M5)
        .value("M15", Timeframe::M15)
        .value("M30", Timeframe::M30)
        .value("H1", Timeframe::H1)
        .value("H4", Timeframe::H4)
        .value("D1", Timeframe::D1)
        .value("W1", Timeframe::W1)
        .value("MN1", Timeframe::MN1);

    nb::enum_<ENUM_POSITION_TYPE>(m, "PositionType", "Position type enumeration")
        .value("BUY", ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
        .value("SELL", ENUM_POSITION_TYPE::POSITION_TYPE_SELL);

    nb::enum_<ENUM_ORDER_TYPE>(m, "OrderType", "Order type enumeration")
        .value("BUY", ENUM_ORDER_TYPE::ORDER_TYPE_BUY)
        .value("SELL", ENUM_ORDER_TYPE::ORDER_TYPE_SELL)
        .value("BUY_LIMIT", ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT)
        .value("SELL_LIMIT", ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT)
        .value("BUY_STOP", ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP)
        .value("SELL_STOP", ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP)
        .value("BUY_STOP_LIMIT", ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT)
        .value("SELL_STOP_LIMIT", ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT);

    nb::enum_<ENUM_DEAL_TYPE>(m, "DealType", "Deal type enumeration")
        .value("BUY", ENUM_DEAL_TYPE::DEAL_TYPE_BUY)
        .value("SELL", ENUM_DEAL_TYPE::DEAL_TYPE_SELL)
        .value("BALANCE", ENUM_DEAL_TYPE::DEAL_TYPE_BALANCE)
        .value("CREDIT", ENUM_DEAL_TYPE::DEAL_TYPE_CREDIT)
        .value("CHARGE", ENUM_DEAL_TYPE::DEAL_TYPE_CHARGE)
        .value("CORRECTION", ENUM_DEAL_TYPE::DEAL_TYPE_CORRECTION)
        .value("BONUS", ENUM_DEAL_TYPE::DEAL_TYPE_BONUS)
        .value("COMMISSION", ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION)
        .value("COMMISSION_DAILY", ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_DAILY)
        .value("COMMISSION_MONTHLY", ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_MONTHLY)
        .value("COMMISSION_AGENT_DAILY", ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_AGENT_DAILY)
        .value("COMMISSION_AGENT_MONTHLY", ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_AGENT_MONTHLY)
        .value("INTEREST", ENUM_DEAL_TYPE::DEAL_TYPE_INTEREST)
        .value("BUY_CANCELED", ENUM_DEAL_TYPE::DEAL_TYPE_BUY_CANCELED)
        .value("SELL_CANCELED", ENUM_DEAL_TYPE::DEAL_TYPE_SELL_CANCELED)
        .value("DIVIDEND", ENUM_DEAL_TYPE::DEAL_TYPE_DIVIDEND)
        .value("DIVIDEND_FRANKED", ENUM_DEAL_TYPE::DEAL_TYPE_DIVIDEND_FRANKED)
        .value("TAX", ENUM_DEAL_TYPE::DEAL_TYPE_TAX);

    // ========================================================================
    // Market Data Types (Read-Only)
    // ========================================================================

    nb::class_<Tick>(m, "Tick", "Tick data structure")
        .def_ro("timestamp_us", &Tick::timestamp_us, "Timestamp in microseconds")
        .def_ro("symbol_id", &Tick::symbol_id, "Symbol ID")
        .def_ro("bid", &Tick::bid, "Bid price (fixed-point, divide by 1e6)")
        .def_ro("ask", &Tick::ask, "Ask price (fixed-point, divide by 1e6)")
        .def_ro("bid_volume", &Tick::bid_volume, "Bid volume")
        .def_ro("ask_volume", &Tick::ask_volume, "Ask volume")
        .def_ro("spread", &Tick::spread, "Spread in points")
        .def("__repr__", [](const Tick& t) {
            return "<Tick bid=" + std::to_string(t.bid / 1e6) +
                   " ask=" + std::to_string(t.ask / 1e6) + ">";
        });

    nb::class_<Bar>(m, "Bar", "Bar (candlestick) data structure")
        .def_ro("timestamp_us", &Bar::timestamp_us, "Bar open time in microseconds")
        .def_ro("symbol_id", &Bar::symbol_id, "Symbol ID")
        .def_ro("open", &Bar::open, "Open price (fixed-point)")
        .def_ro("high", &Bar::high, "High price (fixed-point)")
        .def_ro("low", &Bar::low, "Low price (fixed-point)")
        .def_ro("close", &Bar::close, "Close price (fixed-point)")
        .def_ro("tick_volume", &Bar::tick_volume, "Tick volume")
        .def_ro("spread", &Bar::spread, "Average spread")
        .def_ro("real_volume", &Bar::real_volume, "Real volume")
        .def("__repr__", [](const Bar& b) {
            return "<Bar O=" + std::to_string(b.open / 1e6) +
                   " H=" + std::to_string(b.high / 1e6) +
                   " L=" + std::to_string(b.low / 1e6) +
                   " C=" + std::to_string(b.close / 1e6) + ">";
        });

    // ========================================================================
    // Symbol Information (Read-Only)
    // ========================================================================

    nb::class_<SymbolInfo>(m, "SymbolInfo", "Symbol specification")
        .def("name", &SymbolInfo::Name, "Get symbol name")
        .def("symbol_id", &SymbolInfo::SymbolId, "Get symbol ID")
        .def("digits", &SymbolInfo::Digits, "Get price digits")
        .def("point", &SymbolInfo::Point, "Get point size")
        .def("contract_size", &SymbolInfo::ContractSize, "Get contract size")
        .def("tick_size", &SymbolInfo::TickSize, "Get tick size")
        .def("tick_value", &SymbolInfo::TickValue, "Get tick value")
        .def("currency_base", &SymbolInfo::CurrencyBase, "Get base currency")
        .def("currency_profit", &SymbolInfo::CurrencyProfit, "Get profit currency")
        .def("currency_margin", &SymbolInfo::CurrencyMargin, "Get margin currency")
        .def("bid", &SymbolInfo::Bid, "Get current bid")
        .def("ask", &SymbolInfo::Ask, "Get current ask")
        .def("spread", &SymbolInfo::Spread, "Get current spread")
        .def("volume_min", &SymbolInfo::VolumeMin, "Get minimum volume")
        .def("volume_max", &SymbolInfo::VolumeMax, "Get maximum volume")
        .def("volume_step", &SymbolInfo::VolumeStep, "Get volume step")
        .def("__repr__", [](const SymbolInfo& s) {
            return "<SymbolInfo " + s.Name() + ">";
        });

    // ========================================================================
    // Account Information (Read-Only)
    // ========================================================================

    nb::class_<AccountInfo>(m, "AccountInfo", "Account state information")
        .def("balance", &AccountInfo::Balance, "Get balance in account currency (fixed-point)")
        .def("equity", &AccountInfo::Equity, "Get equity in account currency (fixed-point)")
        .def("margin", &AccountInfo::Margin, "Get used margin (fixed-point)")
        .def("margin_free", &AccountInfo::MarginFree, "Get free margin (fixed-point)")
        .def("margin_level", &AccountInfo::MarginLevel, "Get margin level percentage")
        .def("profit", &AccountInfo::Profit, "Get total profit (fixed-point)")
        .def("currency", &AccountInfo::Currency, "Get account currency")
        .def("leverage", &AccountInfo::Leverage, "Get leverage")
        .def("__repr__", [](const AccountInfo& a) {
            return "<AccountInfo balance=" + std::to_string(a.Balance() / 1e6) +
                   " equity=" + std::to_string(a.Equity() / 1e6) +
                   " currency=" + a.Currency() + ">";
        });

    // ========================================================================
    // Position Information (Read-Only)
    // ========================================================================

    nb::class_<PositionInfo>(m, "PositionInfo", "Position information")
        .def("ticket", &PositionInfo::Ticket, "Get position ticket")
        .def("symbol", &PositionInfo::Symbol, "Get symbol name")
        .def("type", &PositionInfo::Type, "Get position type")
        .def("volume", &PositionInfo::Volume, "Get volume")
        .def("price_open", &PositionInfo::PriceOpen, "Get open price")
        .def("price_current", &PositionInfo::PriceCurrent, "Get current price")
        .def("stop_loss", &PositionInfo::StopLoss, "Get stop loss")
        .def("take_profit", &PositionInfo::TakeProfit, "Get take profit")
        .def("profit", &PositionInfo::Profit, "Get profit (fixed-point)")
        .def("swap", &PositionInfo::Swap, "Get swap (fixed-point)")
        .def("commission", &PositionInfo::Commission, "Get commission (fixed-point)")
        .def("time", &PositionInfo::Time, "Get open time (microseconds)")
        .def("time_update", &PositionInfo::TimeUpdate, "Get last update time")
        .def("magic", &PositionInfo::Magic, "Get magic number")
        .def("comment", &PositionInfo::Comment, "Get comment")
        .def("__repr__", [](const PositionInfo& p) {
            return "<PositionInfo #" + std::to_string(p.Ticket()) +
                   " " + p.Symbol() +
                   " vol=" + std::to_string(p.Volume()) +
                   " profit=" + std::to_string(p.Profit() / 1e6) + ">";
        });

    // ========================================================================
    // Order Information (Read-Only)
    // ========================================================================

    nb::class_<OrderInfo>(m, "OrderInfo", "Pending order information")
        .def("ticket", &OrderInfo::Ticket, "Get order ticket")
        .def("symbol", &OrderInfo::Symbol, "Get symbol name")
        .def("type", &OrderInfo::Type, "Get order type")
        .def("volume", &OrderInfo::Volume, "Get volume")
        .def("price_open", &OrderInfo::PriceOpen, "Get order price")
        .def("stop_loss", &OrderInfo::StopLoss, "Get stop loss")
        .def("take_profit", &OrderInfo::TakeProfit, "Get take profit")
        .def("time_setup", &OrderInfo::TimeSetup, "Get setup time")
        .def("time_expiration", &OrderInfo::TimeExpiration, "Get expiration time")
        .def("magic", &OrderInfo::Magic, "Get magic number")
        .def("comment", &OrderInfo::Comment, "Get comment")
        .def("__repr__", [](const OrderInfo& o) {
            return "<OrderInfo #" + std::to_string(o.Ticket()) +
                   " " + o.Symbol() +
                   " vol=" + std::to_string(o.Volume()) + ">";
        });

    // ========================================================================
    // Deal Information (Read-Only)
    // ========================================================================

    nb::class_<DealInfo>(m, "DealInfo", "Deal (trade execution) information")
        .def("ticket", &DealInfo::Ticket, "Get deal ticket")
        .def("order", &DealInfo::Order, "Get order ticket")
        .def("symbol", &DealInfo::Symbol, "Get symbol name")
        .def("type", &DealInfo::Type, "Get deal type")
        .def("position_id", &DealInfo::PositionId, "Get position ID")
        .def("volume", &DealInfo::Volume, "Get volume")
        .def("price", &DealInfo::Price, "Get execution price")
        .def("profit", &DealInfo::Profit, "Get profit (fixed-point)")
        .def("swap", &DealInfo::Swap, "Get swap (fixed-point)")
        .def("commission", &DealInfo::Commission, "Get commission (fixed-point)")
        .def("time", &DealInfo::Time, "Get execution time")
        .def("magic", &DealInfo::Magic, "Get magic number")
        .def("comment", &DealInfo::Comment, "Get comment")
        .def("__repr__", [](const DealInfo& d) {
            return "<DealInfo #" + std::to_string(d.Ticket()) +
                   " " + d.Symbol() +
                   " profit=" + std::to_string(d.Profit() / 1e6) + ">";
        });
}
