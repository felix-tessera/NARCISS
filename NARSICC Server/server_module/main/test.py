import time
import requests
import pandas as pd
import numpy as np
import hmac
import hashlib
from datetime import datetime

# Configuration
API_KEY = 'mx0vgl2UrjRk87z3Ck'
SECRET_KEY = '2223f95eec0e4883852192f2e9b603c2'
BASE_URL = 'https://api.mexc.com'

# Trading parameters
SYMBOL = 'XRPUSDC'
QUANTITY = 7
TIMEFRAMES = ['1m', '5m', '30m']
CCI_PERIOD = 20
RSI_PERIOD = 14
PROFIT_TARGET_PERCENT = 1
MIN_DATA_POINTS = '500'  # Minimum data points required for calculations
MAX_RETRIES = 3

class MexcBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'X-MEXC-APIKEY': API_KEY
        })
    
    def _sign_request(self, params):
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature
    
    def get_klines(self, symbol, interval, limit=100):
        endpoint = '/api/v3/klines'
        params = {
            'symbol': symbol.upper(),  # Ensure uppercase (e.g., BTCUSDT)
            'interval': interval,
            'limit': limit
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    BASE_URL + endpoint,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    print(f"No data received for {symbol} {interval}")
                    return None
                
                # MEXC returns 8 columns (different from Binance's 12)
                df = pd.DataFrame(data, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume'
                ])
                
                # Convert to numeric values
                df['close'] = pd.to_numeric(df['close'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                
                return df
                
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    print(f"Max retries reached for {symbol} {interval}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def get_account_balance(self):
        # Создаем подписанный запрос
        timestamp = int(time.time() * 1000)
        params = {
            'timestamp': timestamp
        }
        
        # Генерируем подпись
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Добавляем подпись к параметрам
        params['signature'] = signature
        
        # Отправляем запрос
        headers = {
            'X-MEXC-APIKEY': API_KEY
        }
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/v3/account",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе баланса: {e}")
            return None
    
    def get_asset_balance(self, asset='USDC'):
        """Получает баланс конкретного актива"""
        account_info = self.get_account_balance()
        if not account_info or 'balances' not in account_info:
            return None
        
        for balance in account_info['balances']:
            if balance['asset'] == asset:
                free = float(balance['free'])
                locked = float(balance['locked'])
                return {'free': free, 'locked': locked, 'total': free + locked}
        
        return {'free': 0.0, 'locked': 0.0, 'total': 0.0}

    def calculate_rsi(self, data, period=RSI_PERIOD):
        try:
            if data is None or len(data) < period:
                return None

            close_prices = data['close'].astype(float)
            delta = close_prices.diff()
            
            # Первые значения для SMMA
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            
            # Первое значение SMA
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # SMMA (Smoothed Moving Average) для последующих значений
            for i in range(period, len(gain)):
                avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i]) / period
                avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i]) / period
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not rsi.empty else None
            
        except Exception as e:
            print(f"Error calculating RSI: {e}")
            return None
    
    def calculate_cci(self, data, period=CCI_PERIOD):
        try:
            if data is None or len(data) < period:
                return None

            # Типичная цена (Typical Price)
            tp = (data['high'].astype(float) + data['low'].astype(float) + data['close'].astype(float)) / 3
            
            # Скользящая средняя типичной цены
            sma = tp.rolling(window=period).mean()
            
            # Среднее абсолютное отклонение (Mean Deviation)
            mad = tp.rolling(window=period).apply(
                lambda x: np.mean(np.abs(x - np.mean(x))), 
                raw=True
            )
            
            # Расчет CCI с защитой от деления на ноль
            cci = (tp - sma) / (0.015 * (mad + 1e-10))  # +1e-10 чтобы избежать деления на 0
            return cci.iloc[-1] if not cci.empty else None
            
        except Exception as e:
            print(f"Error calculating CCI: {e}")
            return None
    
    def get_current_price(self, symbol):
        endpoint = '/api/v3/ticker/price'
        params = {'symbol': symbol}
        
        try:
            response = self.session.get(BASE_URL + endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return float(data['price'])
        except Exception as e:
            print(f"Error getting current price: {e}")
            return None
    
    def create_order(self, symbol, side, quantity, price, order_type='LIMIT'):
        endpoint = '/api/v3/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'price': price,
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        
        params['timeInForce'] = 'GTC'
        
        params['signature'] = self._sign_request(params)
        
        try:
            response = self.session.post(f"{BASE_URL}{endpoint}",
                               headers={'X-MEXC-APIKEY': API_KEY},
                               params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(response.json())
            print(f"Error creating order: {e}")
            return None
    
    def check_open_orders(self, symbol):
        endpoint = '/api/v3/openOrders'
        params = {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000)
        }
        params['signature'] = self._sign_request(params)
        
        try:
            response = self.session.get(BASE_URL + endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error checking open orders: {e}")
            return []
    
    def calculate_profit_price(self, current_price):
        return current_price * (1 + PROFIT_TARGET_PERCENT / 100)

    def run_strategy(self):
        print(f"\nЗапуск для монеты {SYMBOL} время {datetime.now()}")
        
        # Get current price
        current_price = self.get_current_price(SYMBOL)
        if current_price is None:
            print("Failed to get current price, skipping iteration")
            return
        
        print(f"Текущая цена: {current_price} USDC")
        needed_amount = QUANTITY * current_price
        usdc_balance = self.get_asset_balance('USDC')
        usdc_balance = usdc_balance['free']
        if usdc_balance < needed_amount:
            print("Недостаточно средств на балансе!")
        else:
            # Check open orders
            open_orders = self.check_open_orders(SYMBOL)
            if len(open_orders) > 0:
                print(f"Already have {len(open_orders)} open orders, skipping...")
                return
            
            # Get indicator data
            rsi_values = {}
            valid_data = True
            
            for tf in TIMEFRAMES:
                klines = self.get_klines(SYMBOL, tf)
                rsi = self.calculate_rsi(klines, RSI_PERIOD)
                
                if rsi is None:
                    print(f"Could not calculate RSI for {tf} timeframe")
                    valid_data = False
                    break
                    
                rsi_values[tf] = rsi
            
            if not valid_data:
                print("Insufficient data for indicators, skipping iteration")
                return
            
            cci_data = self.get_klines(SYMBOL, '60m')
            cci_value = self.calculate_cci(cci_data, CCI_PERIOD)
            
            if cci_value is None:
                print("Could not calculate CCI")
                return
            
            print(f"RSI values: {rsi_values}")
            print(f"CCI value: {cci_value}")
            
            # Логика выбора
            buy_signal = (rsi_values['1m'] < 55) and (rsi_values['5m'] < 55) and (rsi_values['30m'] < 65) and (cci_value < 85)

            sell_signal = (rsi_values['1m'] > 55) and (rsi_values['5m'] > 55) and (rsi_values['30m'] > 85) and (cci_value > 85)
            if buy_signal:
                print("Сигнал на покупку")
                #TODO: Изменить цену покупки на более низкую
                order = self.create_order(SYMBOL, 'BUY', QUANTITY, current_price)
                if order and 'orderId' in order:
                    print(f"Ордер на покупку размещен: {order}")
                    while order.get('status') != 'filled':
                        print('Ордер на покупку еще не заполнен')
                        time.sleep(5)
                        # Place take-profit order
                    take_profit_price = self.calculate_profit_price(current_price=current_price)
                    time.sleep(2)  # Wait for buy order to potentially execute
                    tp_order = self.create_order(SYMBOL, 'SELL', QUANTITY, take_profit_price)
                        
                    if tp_order and 'orderId' in tp_order:
                        print(f"Ордер на тейк-профит размещен: {tp_order}")
                    else:
                        print("Ошибка при размещении тейк-профит ордера")
            
            elif sell_signal:
                print("Сигнал на продажу")
                order = self.create_order(SYMBOL, 'SELL', QUANTITY, current_price)
                
                if order and 'orderId' in order:
                    print(f"Placed sell order: {order}")

if __name__ == '__main__':
    bot = MexcBot()
    while True:
            bot.run_strategy()
            time.sleep(5)  # Check every 5 sec
