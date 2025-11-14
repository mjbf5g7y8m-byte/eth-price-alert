#!/usr/bin/env python3
"""
ETH Price Alert Bot
Sleduje cenu ETH a posílá upozornění na Telegram při změně o 5% od posledního upozornění.
"""

import json
import os
import time
import requests
from datetime import datetime

# Konfigurace
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
STATE_FILE = 'eth_price_state.json'
CHECK_INTERVAL = 60  # Kontrola každou minutu (v sekundách)
PRICE_API_URL = 'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd'
PRICE_CHANGE_THRESHOLD = 0.05  # 5% změna


def load_state():
    """Načte poslední stav z souboru."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {'last_notification_price': None, 'last_notification_time': None}


def save_state(state):
    """Uloží stav do souboru."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_eth_price():
    """Získá aktuální cenu ETH z CoinGecko API."""
    try:
        response = requests.get(PRICE_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['ethereum']['usd']
    except (requests.RequestException, KeyError) as e:
        print(f"Chyba při získávání ceny: {e}")
        return None


def calculate_price_change(current_price, last_price):
    """Vypočítá procentuální změnu ceny."""
    if last_price is None:
        return None
    return abs((current_price - last_price) / last_price)


def send_telegram_notification(bot_token, chat_id, current_price, last_price, price_change_pct):
    """Pošle upozornění na Telegram."""
    direction = "📈 VZESTUP" if current_price > last_price else "📉 POKLES"
    change_emoji = "🟢" if current_price > last_price else "🔴"
    
    message = f"""
{change_emoji} <b>ETH Price Alert</b> {change_emoji}

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
    # Ověření konfigurace
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Chyba: Nastavte proměnné prostředí TELEGRAM_BOT_TOKEN a TELEGRAM_CHAT_ID")
        print("\nJak získat:")
        print("1. Vytvořte bota přes @BotFather na Telegramu")
        print("2. Získejte chat ID (číslo) nebo username (např. @honzuvbot)")
        print("3. Nastavte proměnné:")
        print("   export TELEGRAM_BOT_TOKEN='váš_token'")
        print("   export TELEGRAM_CHAT_ID='váš_chat_id_nebo_username'")
        return
    
    # Normalizace chat ID
    normalized_chat_id = normalize_chat_id(TELEGRAM_CHAT_ID)
    
    print("🚀 ETH Price Alert Bot spuštěn")
    print(f"📊 Sleduji změny ceny ETH o {PRICE_CHANGE_THRESHOLD*100}%")
    print(f"⏱️  Kontrola každých {CHECK_INTERVAL} sekund\n")
    
    # Načtení stavu
    state = load_state()
    if state['last_notification_price']:
        print(f"📌 Poslední upozornění: ${state['last_notification_price']:,.2f}")
        print(f"🕐 Čas: {state['last_notification_time']}\n")
    else:
        print("📌 První spuštění - čekám na první změnu o 10%\n")
    
    try:
        while True:
            # Získání aktuální ceny
            current_price = get_eth_price()
            
            if current_price is None:
                print(f"⏳ [{datetime.now().strftime('%H:%M:%S')}] Čekám na další pokus...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            last_price = state['last_notification_price']
            
            # Pokud je to první spuštění, uložíme aktuální cenu
            if last_price is None:
                state['last_notification_price'] = current_price
                state['last_notification_time'] = datetime.now().isoformat()
                save_state(state)
                print(f"💾 [{datetime.now().strftime('%H:%M:%S')}] První cena uložena: ${current_price:,.2f}")
            else:
                # Výpočet změny
                price_change = calculate_price_change(current_price, last_price)
                
                if price_change and price_change >= PRICE_CHANGE_THRESHOLD:
                    # Odeslání upozornění
                    if send_telegram_notification(
                        TELEGRAM_BOT_TOKEN,
                        normalized_chat_id, 
                        current_price, 
                        last_price, 
                        price_change * 100
                    ):
                        # Aktualizace stavu
                        state['last_notification_price'] = current_price
                        state['last_notification_time'] = datetime.now().isoformat()
                        save_state(state)
                else:
                    change_pct = (price_change * 100) if price_change else 0
                    print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] ETH: ${current_price:,.2f} | Změna: {change_pct:.2f}% (limit: {PRICE_CHANGE_THRESHOLD*100}%)")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Bot ukončen uživatelem")
    except Exception as e:
        print(f"\n❌ Neočekávaná chyba: {e}")


if __name__ == '__main__':
    main()

