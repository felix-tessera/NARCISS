# Обновлённый бот с логикой усреднения

import ccxt
import pandas as pd
import pandas_ta as ta
from pybit.unified_trading import HTTP
import time

# --- Настройки API и торговли ---
API_KEY = "w6FuoaEMJvfJVCgspY"
API_SECRET = "ePuwMYEgfNo7p4BZl47IJE5wedV6Q0FfcLvY"
SYMBOL = "XRP/USDT"
LEVERAGE = "2"
ORDER_QTY = 2
EMA_LENGTH = 100
TP_PCT = 0.005
SL_PCT = 0.05
DCA_TRIGGER_PCT = 0.01  # % для усреднения
MAX_DCA_COUNT = 10       # максимум усреднений

session = HTTP(api_key=API_KEY, api_secret=API_SECRET)
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True,
    "options": {"defaultType": "future"}
})

# --- Поддержка состояния позиции ---
position_data = {
    "side": None,
    "entry_prices": [],
    "qty_total": 0,
    "dca_count": 0
}

def fetch_ohlcv(symbol, timeframe='1m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

def log(msg):
    print(f"[LOG] {msg}")

def check_balance(min_required=10):
    try:
        balances = session.get_wallet_balance(accountType="UNIFIED")
        usdt = next((item for item in balances['result']['list'][0]['coin'] if item['coin'] == 'USDT'), None)
        if usdt is None:
            return False
        return float(usdt['walletBalance']) >= min_required
    except:
        return False

def get_indicators():
    try:
        df = fetch_ohlcv(SYMBOL, "1m", limit=200)
        df["ema"] = ta.ema(df["close"], length=EMA_LENGTH)
        ema = df["ema"].iloc[-1]
        close = df["close"].iloc[-1]
        rsi_1m = ta.rsi(df["close"], length=14).iloc[-1]
        rsi_5m = ta.rsi(df["close"].rolling(5).mean(), length=14).iloc[-1]
        rsi_30m = ta.rsi(df["close"].rolling(30).mean(), length=14).iloc[-1]
        cci_1h = ta.cci(df["high"].rolling(60).mean(), df["low"].rolling(60).mean(), df["close"].rolling(60).mean(), length=20).iloc[-1]
        return {
            "price": close, "ema": ema,
            "rsi_1m": rsi_1m, "rsi_5m": rsi_5m, "rsi_30m": rsi_30m, "cci_1h": cci_1h
        }
    except:
        return None

def set_leverage():
    session.set_leverage(category="linear", symbol=SYMBOL.replace("/", ""), buy_leverage=LEVERAGE, sell_leverage=LEVERAGE)

def open_trade(side, price):
    tp = round(price * (1 + TP_PCT) if side == "Buy" else price * (1 - TP_PCT), 4)
    sl = round(price * (1 - SL_PCT) if side == "Buy" else price * (1 + SL_PCT), 4)
    order = session.place_order(
        category="linear",
        symbol=SYMBOL.replace("/", ""),
        side=side,
        order_type="Market",
        qty=str(ORDER_QTY),
        time_in_force="GoodTillCancel",
        take_profit=str(tp),
        stop_loss=str(sl)
    )
    log(f"Открыта {side} позиция по {price} | TP: {tp} | SL: {sl}")
    return price

def try_dca(current_price):
    if position_data["dca_count"] >= MAX_DCA_COUNT:
        return

    avg_price = sum(position_data["entry_prices"]) / len(position_data["entry_prices"])
    trigger_pct = DCA_TRIGGER_PCT
    side = position_data["side"]
    should_dca = (
        side == "Buy" and current_price <= avg_price * (1 - trigger_pct)
    ) or (
        side == "Sell" and current_price >= avg_price * (1 + trigger_pct)
    )

    if should_dca:
        log(f"📉 Усреднение: цена ушла на {trigger_pct*100:.1f}% от средней")
        new_entry = open_trade(side, current_price)
        position_data["entry_prices"].append(new_entry)
        position_data["dca_count"] += 1

def run_bot():
    set_leverage()
    while True:
        indicators = get_indicators()
        if not indicators:
            log("Ошибка при получении индикаторов")
            time.sleep(60)
            continue

        price = indicators["price"]
        ema = indicators["ema"]
        rsi1 = indicators["rsi_1m"]
        rsi5 = indicators["rsi_5m"]
        rsi30 = indicators["rsi_30m"]
        cci1h = indicators["cci_1h"]

        log(f"Цена: {price}, EMA: {ema}, RSI: {rsi1:.1f}, {rsi5:.1f}, {rsi30:.1f}, CCI: {cci1h:.1f}")

        if position_data["side"] is not None:
            try_dca(price)
            time.sleep(60)
            continue

        if not check_balance(min_required=price * ORDER_QTY / float(LEVERAGE)):
            log("❌ Недостаточно средств для входа")
            time.sleep(60)
            continue

        if price > ema and rsi1 < 65 and rsi5 < 65 and rsi30 < 65 and cci1h < 85:
            entry = open_trade("Buy", price)
            position_data.update({"side": "Buy", "entry_prices": [entry], "dca_count": 0})
        elif price < ema and rsi1 > 55 and rsi5 > 55 and rsi30 > 45 and cci1h > -85:
            entry = open_trade("Sell", price)
            position_data.update({"side": "Sell", "entry_prices": [entry], "dca_count": 0})
        else:
            log("Нет сигнала на вход")

        time.sleep(60)

# --- Запуск ---
if __name__ == "__main__":
    run_bot()
