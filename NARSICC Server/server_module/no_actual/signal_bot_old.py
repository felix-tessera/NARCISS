import ccxt
import pandas as pd
import pandas_ta as ta
from pybit.unified_trading import HTTP
import time

# --- Настройки API ---
API_KEY = "w6FuoaEMJvfJVCgspY"
API_SECRET = "ePuwMYEgfNo7p4BZl47IJE5wedV6Q0FfcLvY"
SYMBOL = "BTCUSDT"
LEVERAGE = 5
ORDER_QTY = 0.01  # Объём позиции

# --- Подключение к Bybit Unified API ---
session = HTTP(api_key=API_KEY, api_secret=API_SECRET)

# --- Подключение к CCXT (для получения OHLCV данных) ---
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True,
    "options": {
        "defaultType": "future"
    }
})

def fetch_ohlcv(symbol, timeframe='1m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# --- Логирование ---
def log(message):
    print(f"[LOG] {message}")

# --- Получение индикаторов ---
def check_indicators():
    try:
        df_1m = fetch_ohlcv("BTC/USDT", "1m")
        df_5m = fetch_ohlcv("BTC/USDT", "5m")
        df_30m = fetch_ohlcv("BTC/USDT", "30m")
        df_1h = fetch_ohlcv("BTC/USDT", "1h")

        rsi_1m = ta.rsi(df_1m["close"], length=14).iloc[-1]
        rsi_5m = ta.rsi(df_5m["close"], length=14).iloc[-1]
        rsi_30m = ta.rsi(df_30m["close"], length=14).iloc[-1]
        cci_1h = ta.cci(df_1h["high"], df_1h["low"], df_1h["close"], length=20).iloc[-1]

        return rsi_1m, rsi_5m, rsi_30m, cci_1h
    except Exception as e:
        log(f"Ошибка при получении индикаторов: {e}")
        return None, None, None, None

# --- Получение информации о статусе ордера ---
def get_order_status(order_id):
    return session.get_order(order_id=order_id)

# --- Открытие лимитного ордера с TP ---
def open_limit_order_with_tp(symbol, side, qty, leverage, entry_price, tp_offset=0.3):
    # Установка плеча
    session.set_leverage(
        category="linear",
        symbol=symbol,
        buy_leverage=leverage,
        sell_leverage=leverage
    )

    # Установить лимитную цену
    entry_price = round(entry_price, 2)
    tp_price = round(entry_price * (1.01 if side == "Buy" else 0.99), 2)

    # Открытие лимитного ордера
    log(f"Открытие лимитного ордера {side} на {symbol} по цене {entry_price}")
    entry = session.place_order(
        category="linear",
        symbol=symbol,
        side=side,
        order_type="Limit",
        qty=qty,
        price=entry_price,
        time_in_force="GoodTillCancel"
    )

    # Получаем ID ордера
    order_id = entry['result']['order_id']

    # Проверяем, что ордер исполнен
    order_status = get_order_status(order_id)
    while order_status['result']['status'] != "Filled":
        log(f"Ордер {order_id} не исполнен, ожидаем...")
        time.sleep(5)
        order_status = get_order_status(order_id)

    log(f"Ордер {order_id} исполнен, ставим TP ордер")

    # Установить тейк-профит (лимитный ордер)
    tp = session.place_order(
        category="linear",
        symbol=symbol,
        side="Sell" if side == "Buy" else "Buy",
        order_type="Limit",
        qty=qty,
        price=tp_price,
        reduce_only=True,
        time_in_force="GoodTillCancel"
    )

    log(f"Тейк-профит для ордера {order_id} установлен на {tp_price}")
    return entry, tp

# --- Главный цикл бота ---
def run_bot():
    while True:
        rsi_1m, rsi_5m, rsi_30m, cci_1h = check_indicators()

        if None in (rsi_1m, rsi_5m, rsi_30m, cci_1h):
            log("Пропускаем цикл из-за ошибок в индикаторах")
            time.sleep(60)
            continue

        log(f"RSI 1m: {rsi_1m}, RSI 5m: {rsi_5m}, RSI 30m: {rsi_30m}, CCI 1h: {cci_1h}")

        # Условия для лонга
        if rsi_1m < 55 and rsi_5m < 55 and rsi_30m < 65 and cci_1h < 85:
            ticker = session.get_ticker(category="linear", symbol=SYMBOL)
            mark_price = float(ticker['list'][0]['lastPrice'])

            log("Условия выполнены, открываем ордер...")
            open_limit_order_with_tp(SYMBOL, "Buy", ORDER_QTY, LEVERAGE, mark_price)
        else:
            log("Условия не выполнены для лонга")

        time.sleep(60)

# --- Запуск бота ---
if __name__ == "__main__":
    run_bot()