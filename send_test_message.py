#!/usr/bin/env python3
import requests
import json

# Konfigurace
BOT_TOKEN = '8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8'
CHAT_ID = '351517996'  # Číselné chat ID

# Získání aktuální ceny
try:
    response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd', timeout=10)
    data = response.json()
    current_price = data['ethereum']['usd']
except Exception as e:
    print(f"Chyba při získávání ceny: {e}")
    current_price = None

# Vytvoření zprávy
if current_price:
    message = f"""🧪 <b>Testovací zpráva</b> 🧪

💰 Aktuální cena ETH: <b>${current_price:,.2f}</b>

✅ Aplikace funguje správně!
📊 Sleduji změny o 10% od posledního upozornění.
"""
else:
    message = """🧪 <b>Testovací zpráva</b> 🧪

✅ Aplikace funguje správně!
📊 Sleduji změny o 10% od posledního upozornění.
"""

# Odeslání zprávy
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    'chat_id': CHAT_ID,
    'text': message,
    'parse_mode': 'HTML'
}

try:
    response = requests.post(url, json=payload, timeout=10)
    result = response.json()
    if result.get('ok'):
        print("✅ Testovací zpráva úspěšně odeslána!")
    else:
        print(f"❌ Chyba: {result}")
        print(f"Status code: {response.status_code}")
except Exception as e:
    print(f"❌ Chyba při odesílání: {e}")
    try:
        result = response.json()
        print(f"Detail chyby: {result}")
    except:
        pass

