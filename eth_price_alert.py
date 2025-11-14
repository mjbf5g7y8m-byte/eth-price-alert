#!/usr/bin/env python3
"""
Crypto Price Alert Bot
Sleduje ceny kryptoměn a posílá upozornění na Telegram při změně o 0.1% od posledního upozornění.
"""

import json
import os
import time
import requests
from datetime import datetime

# Konfigurace
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
STATE_FILE = 'crypto_price_state.json'
CHECK_INTERVAL = 60  # Kontrola každou minutu (v sekundách)
CRYPTOCOMPARE_API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY', '7ffa2f0b80215a9e12406537b44f7dafc8deda54354efcfda93fac2eaaaeaf20')
PRICE_CHANGE_THRESHOLD = 0.001  # 0.1% změna

# Sledované kryptoměny (symbol, název)
CRYPTOS = [
    ('ETH', 'Ethereum'),
    ('BTC', 'Bitcoin'),
    ('AAVE', 'Aave'),
    ('ZEC', 'Zcash'),
    ('ICP', 'Internet Computer'),
    ('COW', 'CoW Protocol'),
    ('GNO', 'Gnosis'),
]


def load_state():
    """Načte poslední stav z souboru."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # Vytvoříme prázdný stav pro všechny kryptoměny
    state = {}
    for symbol, name in CRYPTOS:
        state[symbol] = {
            'last_notification_price': None,
            'last_notification_time': None
        }
    return state


def save_state(state):
    """Uloží stav do souboru."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_crypto_price(symbol):
    """Získá aktuální cenu kryptoměny z CryptoCompare API."""
    try:
        url = f'https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD&api_key={CRYPTOCOMPARE_API_KEY}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # CryptoCompare vrací {"USD": cena} nebo chybu
        if 'USD' in data:
            return float(data['USD'])
        elif 'Response' in data and data['Response'] == 'Error':
            print(f"Chyba CryptoCompare API pro {symbol}: {data.get('Message', 'Neznámá chyba')}")
            return None
        else:
            print(f"Neočekávaná odpověď API pro {symbol}: {data}")
            return None
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"Chyba při získávání ceny {symbol}: {e}")
        return None


def calculate_price_change(current_price, last_price):
    """Vypočítá procentuální změnu ceny."""
    if last_price is None:
        return None
    return abs((current_price - last_price) / last_price)


def send_telegram_notification(bot_token, chat_id, symbol, name, current_price, last_price, price_change_pct):
    """Pošle upozornění na Telegram."""
    direction = "📈 VZESTUP" if current_price > last_price else "📉 POKLES"
    change_emoji = "🟢" if current_price > last_price else "🔴"
    
    message = f"""
{change_emoji} <b>{name} ({symbol}) Price Alert</b> {change_emoji}

{direction} o <b>{price_change_pct:.2f}%</b>

💰 Aktuální cena: <b>${current_price:,.2f}</b>
📊 Předchozí cena: <b>${last_price:,.2f}</b>
📅 Čas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ Upozornění odesláno: {direction} o {price_change_pct:.2f}%")
        return True
    except requests.RequestException as e:
        print(f"❌ Chyba při odesílání na Telegram: {e}")
        return False


def normalize_chat_id(chat_id):
    """Normalizuje chat ID - přidá @ pokud je to username bez @."""
    if not chat_id:
        return None
    chat_id = str(chat_id).strip()
    # Pokud to není číslo a nezačíná @, přidáme @
    if not chat_id.lstrip('-').isdigit() and not chat_id.startswith('@'):
        return f'@{chat_id}'
    return chat_id


def main():
    """Hlavní smyčka aplikace."""
    # Debug: Zobrazíme, co aplikace vidí
    print("🔍 Debug - Kontrola environment variables:")
    print(f"   TELEGRAM_BOT_TOKEN: {'✅ Nastaveno' if TELEGRAM_BOT_TOKEN else '❌ Chybí'} ({'prázdné' if not TELEGRAM_BOT_TOKEN else 'má hodnotu'})")
    print(f"   TELEGRAM_CHAT_ID: {'✅ Nastaveno' if TELEGRAM_CHAT_ID else '❌ Chybí'} ({'prázdné' if not TELEGRAM_CHAT_ID else 'má hodnotu'})")
    
    # Ověření konfigurace
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n❌ Chyba: Nastavte proměnné prostředí TELEGRAM_BOT_TOKEN a TELEGRAM_CHAT_ID")
        print("\nJak získat:")
        print("1. Vytvořte bota přes @BotFather na Telegramu")
        print("2. Získejte chat ID (číslo) nebo username (např. @honzuvbot)")
        print("3. Nastavte proměnné:")
        print("   export TELEGRAM_BOT_TOKEN='váš_token'")
        print("   export TELEGRAM_CHAT_ID='váš_chat_id_nebo_username'")
        print("\n💡 Na Render: Settings → Environment → Add Environment Variable")
        return
    
    # Normalizace chat ID
    normalized_chat_id = normalize_chat_id(TELEGRAM_CHAT_ID)
    
    print("🚀 Crypto Price Alert Bot spuštěn")
    print(f"📊 Sleduji změny cen {len(CRYPTOS)} kryptoměn o {PRICE_CHANGE_THRESHOLD*100}%")
    print(f"💰 Kryptoměny: {', '.join([f'{name} ({symbol})' for symbol, name in CRYPTOS])}")
    print(f"⏱️  Kontrola každých {CHECK_INTERVAL} sekund\n")
    
    # Načtení stavu
    state = load_state()
    
    # Zobrazíme stav pro každou kryptoměnu
    for symbol, name in CRYPTOS:
        if symbol in state and state[symbol].get('last_notification_price'):
            price = state[symbol]['last_notification_price']
            time_str = state[symbol].get('last_notification_time', 'N/A')
            print(f"📌 {name} ({symbol}): ${price:,.2f} (čas: {time_str})")
    print()
    
    try:
        while True:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Projdeme všechny kryptoměny
            for symbol, name in CRYPTOS:
                # Získání aktuální ceny
                current_price = get_crypto_price(symbol)
                
                if current_price is None:
                    print(f"⏳ [{timestamp}] {symbol}: Chyba při získávání ceny")
                    continue
                
                # Zajištění, že stav pro tuto kryptoměnu existuje
                if symbol not in state:
                    state[symbol] = {
                        'last_notification_price': None,
                        'last_notification_time': None
                    }
                
                last_price = state[symbol].get('last_notification_price')
                
                # Pokud je to první spuštění, uložíme aktuální cenu
                if last_price is None:
                    state[symbol]['last_notification_price'] = current_price
                    state[symbol]['last_notification_time'] = datetime.now().isoformat()
                    save_state(state)
                    print(f"💾 [{timestamp}] {name} ({symbol}): První cena uložena: ${current_price:,.2f}")
                else:
                    # Výpočet změny
                    price_change = calculate_price_change(current_price, last_price)
                    
                    if price_change and price_change >= PRICE_CHANGE_THRESHOLD:
                        # Odeslání upozornění
                        if send_telegram_notification(
                            TELEGRAM_BOT_TOKEN,
                            normalized_chat_id,
                            symbol,
                            name,
                            current_price, 
                            last_price, 
                            price_change * 100
                        ):
                            # Aktualizace stavu
                            state[symbol]['last_notification_price'] = current_price
                            state[symbol]['last_notification_time'] = datetime.now().isoformat()
                            save_state(state)
                    else:
                        change_pct = (price_change * 100) if price_change else 0
                        print(f"📊 [{timestamp}] {name} ({symbol}): ${current_price:,.2f} | Změna: {change_pct:.2f}% (limit: {PRICE_CHANGE_THRESHOLD*100}%)")
                
                # Malá pauza mezi kryptoměnami, aby se nezatížilo API
                time.sleep(1)
            
            # Hlavní pauza před další kontrolou
            print()  # Prázdný řádek pro lepší čitelnost
            time.sleep(CHECK_INTERVAL - (len(CRYPTOS) * 1))
            
    except KeyboardInterrupt:
        print("\n\n👋 Bot ukončen uživatelem")
    except Exception as e:
        print(f"\n❌ Neočekávaná chyba: {e}")


if __name__ == '__main__':
    main()

