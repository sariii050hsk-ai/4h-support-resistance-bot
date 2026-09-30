import os
import time
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ALERT_DISTANCE = 0.007 # %0.70
CHECK_INTERVAL = 20

BASE_URL = "https://api.gateio.ws/api/v4"

alert_state = {}


def telegram_send(message):
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
print("Telegram ayarlari eksik.")
return

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

try:
response = requests.post(
url,
data={
"chat_id": TELEGRAM_CHAT_ID,
"text": message,
},
timeout=10,
)
response.raise_for_status()

except Exception as e:
print("Telegram hatasi:", e)


def get_contracts():
url = f"{BASE_URL}/futures/usdt/contracts"

response = requests.get(url, timeout=15)
response.raise_for_status()

contracts = response.json()

symbols = []

for contract in contracts:
name = contract.get("name")

if name and name.endswith("_USDT"):
symbols.append(name)

return symbols


def get_previous_4h_candle(symbol):
url = f"{BASE_URL}/futures/usdt/candlesticks"

params = {
"contract": symbol,
"interval": "4h",
"limit": 2,
}

response = requests.get(
url,
params=params,
timeout=15,
)
response.raise_for_status()

candles = response.json()

if len(candles) < 2:
return None

# Son mum calisan 4H mumdur.
# Bir onceki mum kapanmis 4H mumdur.
candle = candles[-2]

high = float(candle["h"])
low = float(candle["l"])
candle_time = int(candle["t"])

return high, low, candle_time


def get_last_price(symbol):
url = f"{BASE_URL}/futures/usdt/tickers"

params = {
"contract": symbol,
}

response = requests.get(
url,
params=params,
timeout=15,
)
response.raise_for_status()

data = response.json()

if not data:
return None

return float(data[0]["last"])


def check_symbol(symbol):
try:
candle = get_previous_4h_candle(symbol)

if candle is None:
return

resistance, support, candle_time = candle

price = get_last_price(symbol)

if price is None:
return

# Sadece iki cizginin ARASINDAYKEN alarm kontrol edilir.
# Disaridan destek veya dirence yaklasmada alarm verilmez.
if not (support < price < resistance):
return

state = alert_state.get(symbol)

if state is None or state["candle"] != candle_time:
state = {
"candle": candle_time,
"support": False,
"resistance": False,
}

alert_state[symbol] = state

# DESTEK:
# Fiyat destek cizgisinin ustunden asagi dogru yaklasiyor.
support_distance = (price - support) / support

if 0 <= support_distance <= ALERT_DISTANCE:
if not state["support"]:
telegram_send(
"🟢 4H DESTEK YAKLASIYOR\n\n"
f"{symbol}\n"
f"Anlik fiyat: {price}\n"
f"Onceki 4H destek: {support}\n"
f"Mesafe: %{support_distance * 100:.2f}"
)

state["support"] = True
else:
state["support"] = False

# DIRENC:
# Fiyat direnc cizgisinin altindan yukari dogru yaklasiyor.
resistance_distance = (resistance - price) / resistance

if 0 <= resistance_distance <= ALERT_DISTANCE:
if not state["resistance"]:
telegram_send(
"🔴 4H DIRENC YAKLASIYOR\n\n"
f"{symbol}\n"
f"Anlik fiyat: {price}\n"
f"Onceki 4H direnc: {resistance}\n"
f"Mesafe: %{resistance_distance * 100:.2f}"
)

state["resistance"] = True
else:
state["resistance"] = False

except Exception as e:
print(f"{symbol} hata: {e}")


def main():
telegram_send(
"✅ 4H Destek/Direnc Alarm Botu baslatildi.\n\n"
"Seviyeler: Onceki kapanmis 4H mum\n"
"Yaklasma mesafesi: %0.70\n"
"Sadece seviyelerin icinden yaklasim takip edilir."
)

while True:
try:
symbols = get_contracts()

print(f"Takip edilen kontrat sayisi: {len(symbols)}")

for symbol in symbols:
check_symbol(symbol)
time.sleep(0.15)

except Exception as e:
print("Ana dongu hatasi:", e)

time.sleep(CHECK_INTERVAL)


if name == "main":
main()
