#!/usr/bin/env python3
"""
Script pro aktualizaci typu asset (crypto/stock) pro specifické tickery
a poslání notifikace všem uživatelům.
"""
import json
import os
import sys
import psycopg2
import asyncio
from telegram import Bot

# Konfigurace
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
CONFIG_FILE = 'crypto_config.json'

# Tickery které chceme nastavit jako crypto
CRYPTO_TICKERS = ['COW', 'SAFE', 'RAIL']

def get_db_connection():
    """Vytvoří připojení k databázi."""
    if not DATABASE_URL:
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)
        return conn
    except Exception as e:
        print(f"⚠️  Chyba při připojení k databázi: {e}")
        return None

def load_config_from_db():
    """Načte konfiguraci z databáze."""
    conn = get_db_connection()
    if not conn:
        return None, None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT data FROM crypto_config ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            return row[0], conn
        return None, conn
    except Exception as e:
        print(f"❌ Chyba při načítání z DB: {e}")
        if conn:
            conn.close()
        return None, None

def save_config_to_db(config, conn):
    """Uloží konfiguraci do databáze."""
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM crypto_config")
        cur.execute("INSERT INTO crypto_config (data) VALUES (%s)", (json.dumps(config),))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"❌ Chyba při ukládání do DB: {e}")
        return False

def load_config_from_file():
    """Načte konfiguraci ze souboru."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config_to_file(config):
    """Uloží konfiguraci do souboru."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def update_ticker_types(config):
    """Aktualizuje typ pro specifické tickery."""
    updated_users = []
    updated_count = 0
    
    for chat_id, user_config in config.items():
        if not isinstance(user_config, dict):
            continue
            
        user_updated = False
        for ticker in CRYPTO_TICKERS:
            if ticker in user_config:
                old_type = user_config[ticker].get('asset_type', 'neznámý')
                user_config[ticker]['asset_type'] = 'crypto'
                print(f"✅ [{chat_id}] {ticker}: {old_type} → crypto")
                updated_count += 1
                user_updated = True
        
        if user_updated:
            updated_users.append(chat_id)
    
    return updated_users, updated_count

async def send_update_message(chat_ids):
    """Pošle zprávu o updatu všem uživatelům."""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️  TELEGRAM_BOT_TOKEN není nastaveno, přeskakuji posílání zpráv")
        return
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    message = (
        "🔄 <b>Aktualizace botu</b>\n\n"
        "✨ <b>Co je nového:</b>\n\n"
        "1️⃣ <b>Výběr typu assetu</b>\n"
        "   Při přidávání tickeru si nyní vyberete, zda jde o:\n"
        "   🪙 Kryptoměnu\n"
        "   📈 Akcii\n\n"
        "2️⃣ <b>Vylepšené načítání cen</b>\n"
        "   Přidány nové spolehlivé API zdroje:\n"
        "   • Coinbase\n"
        "   • Kraken\n"
        "   • Vylepšený Binance\n\n"
        "3️⃣ <b>Automatická migrace</b>\n"
        "   Vaše existující tickery byly automaticky kategorizovány\n\n"
        "📝 <b>Jak to funguje:</b>\n"
        "Příkaz: /add BTC\n"
        "Bot se zeptá: Je to kryptoměna nebo akcie?\n"
        "Vyberete typ → Bot ověří cenu → Nastavíte alert\n\n"
        "🎯 <b>Výhody:</b>\n"
        "• Rychlejší načítání cen\n"
        "• Přesnější detekce\n"
        "• Žádné záměny mezi akciemi a kryptoměnami\n\n"
        "Zkuste to: /add [TICKER]"
    )
    
    success_count = 0
    fail_count = 0
    
    for chat_id in chat_ids:
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text=message,
                parse_mode='HTML'
            )
            print(f"✅ Zpráva odeslána: {chat_id}")
            success_count += 1
            await asyncio.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"❌ Chyba při odesílání uživateli {chat_id}: {e}")
            fail_count += 1
    
    print(f"\n📊 Statistika odesílání:")
    print(f"   ✅ Úspěšně: {success_count}")
    print(f"   ❌ Chyba: {fail_count}")

async def main():
    print("🚀 Spouštím aktualizaci...")
    print(f"🎯 Tickery k aktualizaci: {', '.join(CRYPTO_TICKERS)}\n")
    
    # Zkusíme načíst z databáze
    config, conn = load_config_from_db()
    using_db = config is not None
    
    if not using_db:
        print("📁 Používám lokální soubor")
        config = load_config_from_file()
        if not config:
            print("❌ Žádná konfigurace nenalezena")
            return
    else:
        print("🗄️  Používám databázi")
    
    # Aktualizujeme typy
    print("\n=== Aktualizace typů ===")
    updated_users, updated_count = update_ticker_types(config)
    
    if updated_count == 0:
        print("\n✨ Žádné tickery k aktualizaci nebyly nalezeny")
    else:
        print(f"\n✅ Aktualizováno {updated_count} tickerů pro {len(updated_users)} uživatelů")
        
        # Uložíme změny
        if using_db:
            if save_config_to_db(config, conn):
                print("💾 Změny uloženy do databáze")
            conn.close()
        else:
            save_config_to_file(config)
            print("💾 Změny uloženy do souboru")
    
    # Získáme všechny chat_id pro poslání zprávy
    all_chat_ids = list(config.keys())
    
    if not all_chat_ids:
        print("\n⚠️  Žádní uživatelé v databázi")
        return
    
    print(f"\n=== Posílání zpráv {len(all_chat_ids)} uživatelům ===")
    await send_update_message(all_chat_ids)
    
    print("\n✅ Hotovo!")

if __name__ == '__main__':
    asyncio.run(main())

