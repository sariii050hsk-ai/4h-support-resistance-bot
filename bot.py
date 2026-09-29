import os
import time
import requests

# =========================
# AYARLAR
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Çizgiye %0.70 kala uyar
ALERT_DISTANCE = 0.007

# Kaç saniyede bir kontrol edilsin
CHECK_INTERVAL = 20

# Aynı seviyede sürekli mesaj atmaması için
alert_state = {}

# Gate.io USDT perpetual futures
BASE_URL = "https://api.gateio.ws/api/v4"


def telegram_send(message):
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
print("Telegram ayarlari eksik.")
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
print("Telegram hatasi:", e)


def get_contracts():
"""
Gate.io USDT perpetual futures kontratlarini alir.
"""
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
"""
Son kapanmis 4 saatlik mumun:
high ve low degerlerini getirir.

Calisan 4H mum kullanilmaz.
"""
url = f"{BASE_URL}/futures/usdt/candlesticks"

params = {
"contract": symbol,
"interval": "4h",
"limit": 2
}

response = requests.get(url, params=params, timeout=15)
response.raise_for_status()

candles = response.json()

if len(candles) < 2:
return None

# Son eleman calisan mum,
# bir onceki eleman kapanmis mum
candle = candles[-2]

# Gate futures candle:
# t, v, c, h, l, o
high = float(candle["h"])
low = float(candle["l"])
candle_time = int(candle["t"])

return high, low, candle_time


def get_last_price(symbol):
url = f"{BASE_URL}/futures/usdt/tickers"

params = {
"contract": symbol
}

response = requests.get(url, params=params, timeout=15)
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

# Fiyat mutlaka destek ile direnç arasında olmalı.
# Böylece çizgilere dışarıdan yaklaşınca alarm gelmez.
inside_range = support < price < resistance

if not inside_range:
alert_state[symbol] = {
"support": False,
"resistance": False,
"candle": candle_time
}
return

state = alert_state.get(symbol)

# Yeni kapanmis 4H mum geldiyse alarm durumlarini sifirla
if state is None or state.get("candle") != candle_time:
state = {
"support": False,
"resistance": False,
"candle": candle_time
}

alert_state[symbol] = state

# =========================
# DESTEK
# =========================
# Fiyat desteğin USTUNDE.
# Destek çizgisine yukaridan %0.70 veya daha fazla yaklasti.
support_distance = (price - support) / support

if 0 <= support_distance <= ALERT_DISTANCE:

if not state["support"]:

telegram_send(
f"🟢 4H DESTEK YAKLASIYOR\n\n"
f"{symbol}\n"
f"Fiyat: {price}\n"
f"Onceki 4H destek: {support}\n"
f"Mesafe: %{support_distance * 100:.2f}"
)

state["support"] = True

else:
# Fiyat tekrar %0.70 bolgesinden uzaklasirsa
# ileride yeniden yaklastiginda tekrar uyari verebilir.
state["support"] = False

# =========================
# DIRENC
# =========================
# Fiyat direncin ALTINDA.
# Direnc çizgisine asagidan %0.70 veya daha fazla yaklasti.
resistance_distance = (resistance - price) / resistance

if 0 <= resistance_distance <= ALERT_DISTANCE:

if not state["resistance"]:

telegram_send(
f"🔴 4H DIRENC YAKLASIYOR\n\n"
f"{symbol}\n"
f"Fiyat: {price}\n"
f"Onceki 4H direnc: {resistance}\n"
f"Mesafe: %{resistance_distance * 100:.2f}"
)

state["resistance"] = True

else:
state["resistance"] = False

except Exception as e:
print(symbol, "hata:", e)


def main():

telegram_send(
"✅ 4H destek/direnc takip botu baslatildi.\n"
"Alarm mesafesi: %0.70\n"
"Seviyeler: onceki kapanmis 4H mum."
)

while True:

try:
symbols = get_contracts()

print("Takip edilen kontrat:", len(symbols))

for symbol in symbols:
check_symbol(symbol)

# API'yi cok hizli sorgulamamak icin
time.sleep(0.15)

except Exception as e:
print("Ana dongu hatasi:", e)

time.sleep(CHECK_INTERVAL)


if name == "main":
main()
