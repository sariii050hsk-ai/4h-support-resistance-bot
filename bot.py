import os
import time
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CHECK_SECONDS = 30
ALERT_RATIO = 0.70

sent_alerts = {}


def send_telegram(message):
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
print("Telegram bilgileri eksik.")
return

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

try:
requests.post(
url,
data={
"chat_id": TELEGRAM_CHAT_ID,
"text": message
},
timeout=10
)
except Exception as e:
print("Telegram hata:", e)


def get_top_20():
url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"

response = requests.get(url, timeout=15)
response.raise_for_status()

data = response.json()

coins = []

for item in data:
try:
contract = item["contract"]

if not contract.endswith("_USDT"):
continue

change = float(item.get("change_percentage", 0))
volume = float(item.get("volume_24h_quote", 0))

coins.append((contract, change, volume))

except (ValueError, TypeError, KeyError):
continue

coins.sort(key=lambda x: x[1], reverse=True)

return coins[:20]


def get_previous_4h_candle(contract):
url = "https://api.gateio.ws/api/v4/futures/usdt/candlesticks"

params = {
"contract": contract,
"interval": "4h",
"limit": 2
}

response = requests.get(url, params=params, timeout=15)
response.raise_for_status()

candles = response.json()

if len(candles) < 2:
return None

previous = candles[-2]

high = float(previous["h"])
low = float(previous["l"])

return high, low


def get_price(contract):
url = f"https://api.gateio.ws/api/v4/futures/usdt/tickers"

response = requests.get(
url,
params={"contract": contract},
timeout=15
)

response.raise_for_status()
data = response.json()

if not data:
return None

return float(data[0]["last"])


def check_coin(contract):
levels = get_previous_4h_candle(contract)

if not levels:
return

high, low = levels
price = get_price(contract)

if price is None:
return

candle_range = high - low

if candle_range <= 0:
return

long_level = low + candle_range * (1 - ALERT_RATIO)
short_level = high - candle_range * (1 - ALERT_RATIO)

long_key = contract + "_LONG"
short_key = contract + "_SHORT"

# Fiyat mumun içinden desteğe yaklaşıyor
if low < price <= long_level:
if not sent_alerts.get(long_key):
send_telegram(
f"🟢 LONG YAKLAŞIM\n"
f"{contract}\n"
f"Fiyat: {price}\n"
f"4H Destek: {low}\n"
f"Önceki 4H mum desteğine %70 yaklaştı."
)
sent_alerts[long_key] = True
else:
sent_alerts[long_key] = False

# Fiyat mumun içinden dirence yaklaşıyor
if short_level <= price < high:
if not sent_alerts.get(short_key):
send_telegram(
f"🔴 SHORT YAKLAŞIM\n"
f"{contract}\n"
f"Fiyat: {price}\n"
f"4H Direnç: {high}\n"
f"Önceki 4H mum direncine %70 yaklaştı."
)
sent_alerts[short_key] = True
else:
sent_alerts[short_key] = False


def main():
send_telegram("✅ 4H Destek/Direnç botu çalıştı.")

while True:
try:
top_coins = get_top_20()

print("Kontrol edilen coinler:")
print([coin[0] for coin in top_coins])

for contract, change, volume in top_coins:
try:
check_coin(contract)
except Exception as e:
print(contract, "hata:", e)

time.sleep(CHECK_SECONDS)

except Exception as e:
print("Ana döngü hata:", e)
time.sleep(30)


if name == "main":
main()
