import ccxt
import pandas as pd
import pandas_ta as ta
from pybit.unified_trading import HTTP
import time

# --- Настройки API ---
API_KEY = "w6FuoaEMJvfJVCgspY"
API_SECRET = "ePuwMYEgfNo7p4BZl47IJE5wedV6Q0FfcLvY"
SYMBOL = "XRP/USDT"
LEVERAGE = "5"
ORDER_QTY = "5"  # Объём позиции
EMA_LENGTH = 100  # Длина EMA
TP_PCT = 0.0075     # Тейк-профит
SL_PCT = 0.1     # Стоп-лосс

# --- Подключение к Bybit Unified API ---
session = HTTP(api_key=API_KEY, api_secret=API_SECRET)

# --- Подключение к CCXT (для получения данных) ---
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True,
    "options": {
        "defaultType": "future"
    }
})

# --- Получение OHLCV ---
def fetch_ohlcv(symbol, timeframe='1m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# --- Логирование ---
def log(message):
    print(f"[LOG] {message}")

# --- Проверка баланса ---
def check_balance(min_required=10):
    try:
        balances = session.get_wallet_balance(accountType="UNIFIED")
        usdt_data = next(
            (item for item in balances['result']['list'][0]['coin'] if item['coin'] == 'USDT'),
            None
        )
        if usdt_data is None:
            log("Не удалось найти USDT в кошельке.")
            return False
        available_balance = float(usdt_data['walletBalance'])
        log(f"Доступный баланс: {available_balance:.2f} USDT")
        return available_balance >= min_required
    except Exception as e:
        log(f"Ошибка при получении доступного баланса: {e}")
        return False

def is_position_open():
    try:
        positions = session.get_positions(category="linear", symbol=SYMBOL.replace("/", ""))
        pos_data = positions['result']['list']
        for pos in pos_data:
            size = float(pos['size'])
            if size != 0:
                log(f"Уже есть открытая позиция: {pos['side']} с объёмом {size}")
                return True
        return False
    except Exception as e:
        log(f"Ошибка при проверке открытых позиций: {e}")
        return False

# --- Получение индикаторов ---
def check_indicators():
    try:
        df_1m = fetch_ohlcv(SYMBOL, "1m")
        df_5m = fetch_ohlcv(SYMBOL, "5m")
        df_30m = fetch_ohlcv(SYMBOL, "30m")
        df_1h = fetch_ohlcv(SYMBOL, "1h")
        df_1m["ema"] = ta.ema(df_1m["close"], length=EMA_LENGTH)
        ema = df_1m["ema"].iloc[-1]
        close = df_1m["close"].iloc[-1]

        rsi_1m = ta.rsi(df_1m["close"], length=14).iloc[-1]
        rsi_5m = ta.rsi(df_5m["close"], length=14).iloc[-1]
        rsi_30m = ta.rsi(df_30m["close"], length=14).iloc[-1]
        cci_1h = ta.cci(df_1h["high"], df_1h["low"], df_1h["close"], length=20).iloc[-1]

        return {
            "rsi_1m": rsi_1m,
            "rsi_5m": rsi_5m,
            "rsi_30m": rsi_30m,
            "cci_1h": cci_1h,
            "ema": ema,
            "price": close
        }
    except Exception as e:
        log(f"Ошибка при получении индикаторов: {e}")
        return None
    
# --- Установка плеча ---
def set_leverage():
    try:
        session.set_leverage(
            category="linear",
            symbol=SYMBOL.replace("/", ""),
            buy_leverage=LEVERAGE,
            sell_leverage=LEVERAGE
        )
        log(f"Плечо {LEVERAGE}x установлено для {SYMBOL}")
    except Exception as e:
        log(f"Ошибка установки плеча: {e}")

# --- Открытие сделки ---
def open_trade(side, price):
    entry_price = round(price, 4)
    tp = round(entry_price * (1 + TP_PCT) if side == "Buy" else entry_price * (1 - TP_PCT), 4)
    sl = round(entry_price * (1 - SL_PCT) if side == "Buy" else entry_price * (1 + SL_PCT), 4)

    log(f"Открытие {side} по цене {entry_price}, TP: {tp}, SL: {sl}")

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
    log(f"Открыт ордер ID: {order['result']['orderId']}")
    return order

# --- Главный цикл ---
def run_bot():
    set_leverage()
    while True:
        if is_position_open():
            log("Пропуск, так как уже есть открытая позиция.")
            time.sleep(60)
            continue
        indicators = check_indicators()
        if indicators is None:
            log("Ошибка в индикаторах, пропуск...")
            time.sleep(60)
            continue

        rsi1 = indicators["rsi_1m"]
        rsi5 = indicators["rsi_5m"]
        rsi30 = indicators["rsi_30m"]
        cci1h = indicators["cci_1h"]
        ema = indicators["ema"]
        price = indicators["price"]

        log(f"Цена: {price:.4f}, EMA: {ema:.4f}")
        log(f"RSI: {rsi1:.1f}, {rsi5:.1f}, {rsi30:.1f} | CCI: {cci1h:.1f}")

        if not check_balance(min_required=price * int(ORDER_QTY) / int(LEVERAGE)):
            log("❌ Недостаточно средств для торговли. Ожидание...")
            time.sleep(60)
            continue

        # 📈 Условия для лонга
        if price > ema and rsi1 < 55 and rsi5 < 55 and rsi30 < 65 and cci1h < 85:
            open_trade("Buy", price)

        # 📉 Условия для шорта
        elif price < ema and rsi1 > 45 and rsi5 > 45 and rsi30 > 35 and cci1h > -85:
            open_trade("Sell", price)
        else:
            log("Нет условий для входа")

        time.sleep(60)

# --- Запуск ---
if __name__ == "__main__":
    run_bot()
