import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

class IPv6Connection:
    def __init__(self, ipv6_addr):
        self.base_url = f"http://[{ipv6_addr}]"
        self.session = requests.Session()
        
        # Настройка повторных попыток
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retry))
    
    def test_connection(self):
        try:
            response = self.session.get(
                f"{self.base_url}/status",
                timeout=10
            )
            return response.status_code == 200
        except requests.exceptions.ConnectionError as e:
            print(f"Ошибка подключения: {e}")
            if "10065" in str(e):
                print("Решение:")
                print("1. Проверьте правильность IPv6 адреса")
                print("2. Убедитесь, что хост доступен в сети")
                print("3. Проверьте firewall на целевом устройстве")
            return False

# Использование
conn = IPv6Connection("2a02:220a:2001:8800:2003:4dff:fe02:1d60")  # Замените на ваш IPv6
if conn.test_connection():
    print("Подключение успешно")
else:
    print("Не удалось установить соединение")