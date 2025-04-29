import requests

def calculate_target_price(target_profit, coin_price, count_usdt, leverage):
    count_usdt *= leverage
    target_percentage = (target_profit / count_usdt) * 100
    target_price = coin_price * (1 + (target_percentage / 100))
    print(f"Необходимый процент изменения цены: {target_percentage}%")
    print(f"Необходимое изменение цены в usdt: {target_price}$. Дистанция: {target_price - coin_price}$")