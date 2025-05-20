import json
import hmac
import hashlib
import time
import requests


# TODO: Ограничение по часттоте заявок: 20 раз в 2 секунды

# Настройки API
API_KEY = 'mx0vgl2UrjRk87z3Ck'
API_SECRET = '2223f95eec0e4883852192f2e9b603c2'
BASE_URL = 'https://api.mexc.com'

# Торговые настройки
SYMBOL = 'SHIBUSDC'
QUANTITY = 100000

# Генерация подписи запроса
def sign_request(params, secret_key):
    query_string = '&'.join(f"{key}={params[key]}" for key in params)
    signature = hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

# Получение стакана
def get_order_book(symbol):
    url = f"{BASE_URL}/api/v3/depth"
    response = requests.get(url, params={'symbol': symbol, 'limit': 5})  # Анализ до 5 уровней стакана
    return response.json()

# Получение баланса
def get_balance_t():
    endpoint = '/api/v3/account'
    timestamp = int(time.time() * 1000)
    params = {'timestamp': timestamp}
    params['signature'] = sign_request(params, API_SECRET)
    headers = {'X-MEXC-APIKEY': API_KEY}

    response = requests.get(BASE_URL + endpoint, headers=headers, params=params)
    if response.status_code == 200:
        balances = response.json().get('balances', [])
        for asset in balances:
            if asset['asset'] == 'USDC':
                return print(float(asset['free']))
    else:
        return response.status_code

# Создание лимитного ордера 
# TODO: переделать на фьючерсы!
def place_limit_order(symbol, side, quantity, price):
    endpoint = '/api/v3/order'
    timestamp = int(time.time() * 1000)
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'LIMIT',
        'quantity': format(quantity, '.10f'),
        'price': format(price, '.10f'),
        'timeInForce': 'IOC',
        'timestamp': timestamp
    }
    params['signature'] = sign_request(params, API_SECRET)
    headers = {'X-MEXC-APIKEY': API_KEY}
    response = requests.post(BASE_URL + endpoint, headers=headers, params=params)
    return response.json()

def check_order_fill(order_id, symbol):
    if 'orderId' != None:
        order_status = get_order_status(order_id, SYMBOL)
        if order_status.get('status') == 'FILLED':
            buy_price = float(order_status['price'])
            print(f"Куплено по {format(buy_price, '.10f')}")
        else:
            print("Ордер на покупку не исполнен")
    else:
        print("Ордер не существует")

# Получение статуса запроса
def get_order_status(order_id, symbol):
    endpoint = '/api/v3/order'
    timestamp = int(time.time() * 1000)
    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': timestamp
    }
    params['signature'] = sign_request(params, API_SECRET)
    headers = {'X-MEXC-APIKEY': API_KEY}
    response = requests.get(BASE_URL + endpoint, headers=headers, params=params)
    return response.json()

# Получение лучших цен покупки и продажи
def analyze_order_book(order_book):
    bids = order_book.get('bids', [])
    asks = order_book.get('asks', [])
    return float(bids[0][0]), float(asks[0][0])

# Проверка баланса на достаточность средств для размещения ордера
def check_balance_for_buy(balance, price):
    if(balance > price * QUANTITY):
        return True
    else:
        print("Недостаточно средств")
        return False

def trading_loop():
    buy_price = None
    
    while True:
        balance = get_balance_t()
        order_book = get_order_book(SYMBOL)
        best_bid, best_ask = analyze_order_book(order_book)

        if buy_price is None:
                buy_order = place_limit_order(SYMBOL, 'BUY', QUANTITY, best_ask)
                print(buy_order)
                print("Ордер размещен")
        else:
                sell_order = place_limit_order(SYMBOL, 'SELL', QUANTITY, best_bid)
                print(sell_order)
                print("Ордер размещен")
        time.sleep(5)

trading_loop()