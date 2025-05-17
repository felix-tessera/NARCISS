import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc

# --- Настройки стратегии ---
SYMBOL = "XRP/USDT"
TIMEFRAME = "1m"
START_DATE = "2025-04-08"
END_DATE = "2025-05-08"

INITIAL_BALANCE = 100  # Начальный баланс USDT
LEVERAGE = 1 # плечо
ORDER_QTY = 10  # Количество монет
TP_PCT = 0.005    # Тейк-профит 0.5%
SL_PCT = 0.05     # Стоп-лосс 5%
EMA_LENGTH = 100 # EMA фильтр тренда
LIQUIDATION_PCT = 1 / LEVERAGE  # Условия ликвидации

# --- Загрузка исторических данных ---
def fetch_historical_data(symbol, timeframe, since, until):
    exchange = ccxt.bybit()
    all_data = []
    since_ts = exchange.parse8601(since + "T00:00:00Z")
    until_ts = exchange.parse8601(until + "T00:00:00Z")

    while since_ts < until_ts:
        data = exchange.fetch_ohlcv(symbol, timeframe, since=since_ts, limit=1000)
        if not data:
            break
        last_ts = data[-1][0]
        since_ts = last_ts + 60_000
        all_data.extend(data)

    df = pd.DataFrame(all_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# --- Индикаторы ---
def apply_strategy(df):
    df["rsi_1m"] = ta.rsi(df["close"], length=14)
    df["rsi_5m"] = ta.rsi(df["close"].rolling(5).mean(), length=14)
    df["rsi_30m"] = ta.rsi(df["close"].rolling(30).mean(), length=14)
    df["cci_1h"] = ta.cci(df["high"], df["low"], df["close"], length=20)
    df["ema_trend"] = ta.ema(df["close"], length=EMA_LENGTH)
    return df

# --- Бэктест ---
def backtest(df, balance, leverage, order_qty):
    trades = []
    equity_curve = [balance]
    max_balance = balance
    max_drawdown = 0
    liquidated = False
    position = None
    stats = {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "profit": 0.0,
        "longs": 0,
        "shorts": 0
    }

    for i in range(max(EMA_LENGTH, 61), len(df)):
        row = df.iloc[i]
        price = row["close"]
        ema_trend = row["ema_trend"]
        time = row["timestamp"]

        rsi_1m = row["rsi_1m"]
        rsi_5m = row["rsi_5m"]
        rsi_30m = row["rsi_30m"]
        cci_1h = row["cci_1h"]

        if position is None:
            # 📈 Условия для ЛОНГА
            if (
                price > ema_trend and
                rsi_1m < 55 and
                rsi_5m < 55 and
                rsi_30m < 65 and
                cci_1h < 85
            ):
                entry_price = price
                tp_price = entry_price * (1 + TP_PCT)
                sl_price = entry_price * (1 - SL_PCT)
                position = {
                    "type": "long",
                    "entry_price": entry_price,
                    "tp_price": tp_price,
                    "sl_price": sl_price
                }
                trades.append({"timestamp": time, "price": price, "type": "long", "action": "entry"})
                stats["total_trades"] += 1
                stats["longs"] += 1

            # 📉 Условия для ШОРТА
            elif (
                price < ema_trend and
                rsi_1m > 45 and
                rsi_5m > 45 and
                rsi_30m > 35 and
                cci_1h > -85
            ):
                entry_price = price
                tp_price = entry_price * (1 - TP_PCT)
                sl_price = entry_price * (1 + SL_PCT)
                position = {
                    "type": "short",
                    "entry_price": entry_price,
                    "tp_price": tp_price,
                    "sl_price": sl_price
                }
                trades.append({"timestamp": time, "price": price, "type": "short", "action": "entry"})
                stats["total_trades"] += 1
                stats["shorts"] += 1

        elif position["type"] == "long":
            if row["high"] >= position["tp_price"]:
                profit = (position["tp_price"] - position["entry_price"]) * order_qty * leverage
                balance += profit
                stats["wins"] += 1
                stats["profit"] += profit
                max_balance = max(max_balance, balance)
                drawdown = (max_balance - balance) / max_balance
                max_drawdown = max(max_drawdown, drawdown)
                equity_curve.append(balance)
                trades.append({"timestamp": time, "price": position["tp_price"], "type": "long", "action": "exit"})
                position = None
            elif row["low"] <= position["sl_price"]:
                loss = (position["entry_price"] - position["sl_price"]) * order_qty * leverage
                balance -= loss
                stats["losses"] += 1
                stats["profit"] -= loss
                max_balance = max(max_balance, balance)
                drawdown = (max_balance - balance) / max_balance
                max_drawdown = max(max_drawdown, drawdown)
                equity_curve.append(balance)
                trades.append({"timestamp": time, "price": position["sl_price"], "type": "long", "action": "exit"})
                position = None
            if balance <= 0:
                liquidated = True
                equity_curve.append(balance)
                break

        elif position["type"] == "short":
            if row["low"] <= position["tp_price"]:
                profit = (position["entry_price"] - position["tp_price"]) * order_qty * leverage
                balance += profit
                stats["wins"] += 1
                stats["profit"] += profit
                equity_curve.append(balance)
                trades.append({"timestamp": time, "price": position["tp_price"], "type": "short", "action": "exit"})
                position = None
            elif row["high"] >= position["sl_price"]:
                loss = (position["sl_price"] - position["entry_price"]) * order_qty * leverage
                balance -= loss
                stats["losses"] += 1
                stats["profit"] -= loss
                equity_curve.append(balance)
                trades.append({"timestamp": time, "price": position["sl_price"], "type": "short", "action": "exit"})
                position = None
            if balance <= 0:
                liquidated = True
                equity_curve.append(balance)
                break

    return balance, stats, equity_curve, max_drawdown, liquidated, trades

def plot_chart(df, trades):
    df_plot = df.copy()
    df_plot["timestamp_num"] = mdates.date2num(df_plot["timestamp"])
    ohlc = df_plot[["timestamp_num", "open", "high", "low", "close"]]

    plt.figure(figsize=(15, 6))
    ax = plt.subplot()

    candlestick_ohlc(ax, ohlc.values, width=0.0007, colorup='green', colordown='red')

    for trade in trades:
        ts = mdates.date2num(trade["timestamp"])
        color = 'green' if trade["type"] == "long" else 'red'
        marker = '^' if trade["action"] == "entry" else 'v'
        ax.plot(ts, trade["price"], marker=marker, color=color, markersize=8)

    ax.xaxis_date()
    ax.set_title("Сделки на графике")
    ax.set_xlabel("Время")
    ax.set_ylabel("Цена")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- Запуск бэктеста ---
if __name__ == "__main__":
    print("Загрузка исторических данных...")
    df = fetch_historical_data(SYMBOL, TIMEFRAME, START_DATE, END_DATE)
    df = apply_strategy(df)

    print("Запуска бэктеста...")
    final_balance, stats, equity_curve, max_drawdown, liquidated, trades = backtest(df, INITIAL_BALANCE, LEVERAGE, ORDER_QTY)

    print("\n--- Результаты бэктеста ---")
    print(f"Начальный баланс: {INITIAL_BALANCE:.2f} USDT")
    print(f"Конечный баланс: {final_balance:.2f} USDT")
    print(f"Сделок всего: {stats['total_trades']}")
    print(f"Открыто лонг сделок: {stats['longs']}")
    print(f"Открыто шорт сделок: {stats['shorts']}")
    print(f"Прибыльных: {stats['wins']}, Убыточных: {stats['losses']}")
    print(f"Средняя прибыль со сделки: {stats['profit'] / stats['wins']}")
    print(f"Общая прибыль: {stats['profit']:.2f} USDT")
    if stats['total_trades'] > 0:
        win_rate = stats['wins'] / stats['total_trades'] * 100
        print(f"Винрейт: {win_rate:.2f}%")
    print(f"Максимальная просадка: {max_drawdown * 100:.2f}%")
    print(f"{'💥 Ликвидация произошла!' if liquidated else '✅ Ликвидации не было.'}")
    plot_chart(df, trades)