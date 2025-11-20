#!/usr/bin/env python3
"""
Crypto Price Alert Bot
Sleduje ceny kryptoměn a posílá upozornění na Telegram při změně o nastavené procento.
Podporuje více uživatelů (každý má vlastní nastavení).
"""
import json
import os
import time
import requests
import asyncio
import atexit
import random
import psycopg2
from psycopg2 import OperationalError, Error as Psycopg2Error
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.error import Conflict, NetworkError, TimedOut

# Konfigurace
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# TELEGRAM_CHAT_ID už není globální konstanta pro posílání, ale použijeme ho jako default admina pro migraci
ADMIN_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') 

STATE_FILE = 'crypto_price_state.json'
CONFIG_FILE = 'crypto_config.json'
CHECK_INTERVAL = 60  # Kontrola každou minutu
CRYPTOCOMPARE_API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY', '7ffa2f0b80215a9e12406537b44f7dafc8deda54354efcfda93fac2eaaaeaf20')
DATABASE_URL = os.getenv('DATABASE_URL')

# Stavy konverzace
WAITING_TICKER, WAITING_THRESHOLD, WAITING_UPDATE_THRESHOLD = range(3)

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

def init_database():
    """Inicializuje databázové tabulky."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_config (
                id SERIAL PRIMARY KEY,
                data JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_state (
                id SERIAL PRIMARY KEY,
                data JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Chyba při inicializaci databáze: {e}")
        if conn: conn.close()
        return False

# --- Správa dat (Load/Save) s podporou více uživatelů ---
# Struktura dat: { "chat_id_string": { "SYMBOL": { ... } } }

def load_data(table_name, file_name):
    """Obecná funkce pro načtení JSON dat (config nebo state)."""
    conn = get_db_connection()
    data = {}
    
    # 1. Zkusíme DB
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT data FROM {table_name} ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row and row[0]:
                data = row[0]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️  Chyba DB load ({table_name}): {e}")
            if conn: conn.close()
    
    # 2. Fallback na soubor (pokud je DB prázdná nebo nedostupná a soubor existuje)
    if not data and os.path.exists(file_name):
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
        except:
            pass

    # 3. Migrace starého formátu (pokud root klíče nejsou čísla/chat_id, ale přímo tickery jako 'BTC')
    # Předpokládáme, že stará data patří adminovi (z env var)
    if data and ADMIN_CHAT_ID:
        # Získáme první klíč bezpečně
        try:
            first_key = next(iter(data))
        except StopIteration:
            first_key = None
            
        if first_key:
            # Pokud klíč vypadá jako ticker (krátký, písmena) a ne jako ID (čísla)
            if isinstance(first_key, str) and not first_key.isdigit() and len(first_key) < 10:
                print(f"🔄 Migrace dat pro uživatele {ADMIN_CHAT_ID}...")
                data = {str(ADMIN_CHAT_ID): data}
                # Okamžitě uložíme migrovanou verzi
                save_data(table_name, file_name, data)

    return data

def save_data(table_name, file_name, data):
    """Obecná funkce pro uložení JSON dat."""
    conn = get_db_connection()
    
    # 1. DB Save
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {table_name}")
            cur.execute(f"INSERT INTO {table_name} (data) VALUES (%s)", (json.dumps(data),))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️  Chyba DB save ({table_name}): {e}")
            if conn: conn.close()
    
    # 2. File Save (jako záloha nebo pro lokální běh)
    try:
        with open(file_name, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# Helpery pro přístup k datům konkrétního uživatele
def get_user_config(chat_id):
    full_config = load_data('crypto_config', CONFIG_FILE)
    # Zajistíme, že vracíme dict, i když je prázdný
    if str(chat_id) not in full_config:
        full_config[str(chat_id)] = {}
    return full_config[str(chat_id)], full_config

def save_user_config(chat_id, user_config, full_config):
    full_config[str(chat_id)] = user_config
    save_data('crypto_config', CONFIG_FILE, full_config)

def get_user_state(chat_id):
    full_state = load_data('crypto_state', STATE_FILE)
    if str(chat_id) not in full_state:
        full_state[str(chat_id)] = {}
    return full_state[str(chat_id)], full_state

def save_user_state(chat_id, user_state, full_state):
    full_state[str(chat_id)] = user_state
    save_data('crypto_state', STATE_FILE, full_state)

# --- API Funkce ---
def get_price_from_cryptocompare(symbol):
    """Získá cenu z CryptoCompare API."""
    url = f'https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'USD' in data:
            return float(data['USD']), 'CryptoCompare'
    except:
        pass
    return None, None

def get_price_from_binance(symbol):
    """Získá cenu z Binance API."""
    symbol_map = {
        'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'AAVE': 'AAVEUSDT',
        'ZEC': 'ZECUSDT', 'ICP': 'ICPUSDT', 'COW': 'COWUSDT',
        'GNO': 'GNOUSDT', 'LTC': 'LTCUSDT',
    }
    binance_symbol = symbol_map.get(symbol.upper())
    if not binance_symbol:
        return None, None
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'price' in data:
            return float(data['price']), 'Binance'
    except:
        pass
    return None, None

def get_crypto_price(symbol):
    """Získá aktuální cenu kryptoměny z náhodně vybraného API."""
    api_functions = [get_price_from_cryptocompare, get_price_from_binance]
    random.shuffle(api_functions)
    
    for api_func in api_functions:
        try:
            price, api_name = api_func(symbol)
            if price is not None:
                return price
        except:
            continue
    return None

def get_stock_price(symbol):
    """Získá aktuální cenu akcie z Yahoo Finance API."""
    # Yahoo Finance API - zkusíme více endpointů
    endpoints = [
        f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}',
        f'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol.upper()}?modules=price',
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
            if response.status_code == 200:
                try:
                    data = response.json()
                except:
                    continue
    
                # Zkusíme první endpoint (chart)
                if 'chart' in data and 'result' in data['chart']:
                    result = data['chart']['result']
                    if result and len(result) > 0:
                        if 'meta' in result[0]:
                            meta = result[0]['meta']
                            # Zkusíme různé možné klíče pro cenu
                            for price_key in ['regularMarketPrice', 'previousClose', 'currentPrice', 'chartPreviousClose']:
                                if price_key in meta and meta[price_key] is not None:
                                    price_val = meta[price_key]
                                    if isinstance(price_val, (int, float)):
                                        return float(price_val), 'Yahoo Finance'
                
                # Zkusíme druhý endpoint (quoteSummary)
                if 'quoteSummary' in data and 'result' in data['quoteSummary']:
                    result = data['quoteSummary']['result']
                    if result and len(result) > 0:
                        if 'price' in result[0]:
                            price_obj = result[0]['price']
                            # Zkusíme různé klíče
                            for price_key in ['regularMarketPrice', 'currentPrice']:
                                if price_key in price_obj:
                                    price_val = price_obj[price_key]
                                    if isinstance(price_val, dict) and 'raw' in price_val:
                                        return float(price_val['raw']), 'Yahoo Finance'
                                    elif isinstance(price_val, (int, float)):
                                        return float(price_val), 'Yahoo Finance'
        except Exception as e:
            continue
    
    # Fallback: Zkusíme jednodušší endpoint
    try:
        url = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol.upper()}'
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'quoteResponse' in data and 'result' in data['quoteResponse']:
                result = data['quoteResponse']['result']
                if result and len(result) > 0:
                    if 'regularMarketPrice' in result[0]:
                        return float(result[0]['regularMarketPrice']), 'Yahoo Finance'
    except:
        pass
    
    return None, None

def get_price(symbol):
    """Získá cenu kryptoměny nebo akcie - automaticky detekuje typ."""
    # Nejdřív zkusíme kryptoměnu
    price = get_crypto_price(symbol.upper())
    if price is not None:
        return price, 'crypto'
    
    # Pokud to není kryptoměna, zkusíme akcii
    price, api_name = get_stock_price(symbol.upper())
    if price is not None:
        return price, 'stock'
    
    return None, None

def validate_ticker(symbol):
    """Ověří ticker a vrátí typ (crypto/stock), název a cenu."""
    price, asset_type = get_price(symbol.upper())
    if price is not None:
        # Pro kryptoměny použijeme symbol jako název, pro akcie zkusíme získat název
        name = symbol.upper()
        if asset_type == 'stock':
            # Zkusíme získat název akcie z Yahoo Finance
            try:
                url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}'
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, timeout=5, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if 'chart' in data and 'result' in data['chart']:
                        result = data['chart']['result']
                        if result and len(result) > 0 and 'meta' in result[0]:
                            name = result[0]['meta'].get('longName', symbol.upper())
            except:
                pass
        return True, name, price
    return False, None, None

# --- Telegram Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 <b>CryptoWatch Pro</b>\n\n"
        "Profesionální sledování cen kryptoměn a akcií s automatickými upozorněními.\n\n"
        "📊 <b>Hlavní funkce:</b>\n"
        "• Sledování kryptoměn (BTC, ETH, atd.)\n"
        "• Sledování akcií (AAPL, TSLA, atd.)\n"
        "• Přizpůsobitelné prahové hodnoty\n"
        "• Okamžitá notifikace při změně ceny\n"
        "• Více uživatelů - každý má vlastní nastavení\n\n"
        "⚡ <b>Rychlý start:</b>\n"
        "/add BTC - Přidat kryptoměnu\n"
        "/add AAPL - Přidat akcii\n"
        "/list - Zobrazit sledované\n"
        "/update - Změnit prahovou hodnotu\n"
        "/help - Více informací\n\n"
        "💡 <i>Nastavte si vlastní alerty a nikdy nepromeškejte důležité pohyby cen!</i>",
            parse_mode='HTML'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>CryptoWatch Pro - Nápověda</b>\n\n"
        "🔹 <b>Příkazy:</b>\n\n"
        "<b>/start</b> - Úvodní zpráva\n"
        "<b>/add TICKER</b> - Přidat kryptoměnu nebo akcii\n"
        "   Kryptoměny: /add BTC, /add ETH, /add LTC\n"
        "   Akcie: /add AAPL, /add TSLA, /add MSFT\n"
        "   Bot se zeptá na prahovou hodnotu (např. 5 pro 5%)\n\n"
        "<b>/list</b> - Zobrazit všechny sledované symboly\n\n"
        "<b>/update [TICKER]</b> - Změnit prahovou hodnotu\n"
        "   Příklad: /update BTC nebo jen /update (vybere z menu)\n\n"
        "<b>/setall %</b> - Nastavit stejnou prahovou hodnotu pro všechny\n"
        "   Příklad: /setall 5 (nastaví 5% pro všechny)\n\n"
        "<b>/remove TICKER</b> - Odebrat symbol ze sledování\n"
        "   Příklad: /remove BTC nebo /remove AAPL\n\n"
        "<b>/help</b> - Zobrazit tuto nápovědu\n\n"
        "💡 <b>Tip:</b> Bot kontroluje ceny každou minutu a pošle upozornění, když cena změní o nastavené procento.\n\n"
        "📈 <b>Podporované:</b> Kryptoměny (BTC, ETH, atd.) a akcie (AAPL, TSLA, atd.)",
        parse_mode='HTML'
    )

async def add_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Použití: /add BTC")
        return ConversationHandler.END
    
    symbol = context.args[0].upper()
    await update.message.reply_text(f"🔍 Ověřuji {symbol}...")
    
    is_valid, name, price = validate_ticker(symbol)
    
    if not is_valid:
        await update.message.reply_text(f"❌ {symbol} nebyl nalezen.")
        return ConversationHandler.END
    
    # Uložíme do paměti konverzace
    context.user_data['pending_symbol'] = symbol
    context.user_data['pending_name'] = name
    context.user_data['pending_price'] = price
    
    await update.message.reply_text(
        f"✅ <b>{name}</b> (${price:,.2f})\n"
        "Zadejte procento pro alert (např. 5):",
        parse_mode='HTML'
    )
    return WAITING_THRESHOLD

async def handle_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().replace('%', '')
    
    try:
        threshold = float(text) / 100
        if threshold <= 0: raise ValueError
        
        symbol = context.user_data.get('pending_symbol')
        name = context.user_data.get('pending_name')
        
        if not symbol:
            await update.message.reply_text("❌ Chyba kontextu. Zkuste /add znovu.")
            return ConversationHandler.END
        
        # Načtení a úprava konfigurace uživatele
        user_config, full_config = get_user_config(chat_id)
        user_config[symbol] = {'name': name, 'threshold': threshold}
        save_user_config(chat_id, user_config, full_config)
        
        # Inicializace stavu
        user_state, full_state = get_user_state(chat_id)
        if symbol not in user_state:
            user_state[symbol] = {'last_notification_price': context.user_data.get('pending_price')}
        save_user_state(chat_id, user_state, full_state)
        
        await update.message.reply_text(f"✅ <b>{symbol}</b> uloženo s limitem {threshold*100}%", parse_mode='HTML')
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Zadejte číslo (např. 5).")
        return WAITING_THRESHOLD

async def list_cryptos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_config, _ = get_user_config(chat_id)
    user_state, _ = get_user_state(chat_id)
    
    if not user_config:
        await update.message.reply_text("📭 Nemáte nastavené žádné kryptoměny.")
        return
    
    msg = "📋 <b>Vaše kryptoměny:</b>\n\n"
    for symbol, conf in user_config.items():
        last_price = user_state.get(symbol, {}).get('last_notification_price', 0)
        # Pokud last_price neexistuje, je to chyba nebo první běh, zobrazíme 0 nebo ?
        price_display = f"${last_price:,.2f}" if last_price else "?"
        threshold = conf.get('threshold', 0.05) * 100
        msg += f"• <b>{symbol}</b> (Limit: {threshold}%)\n"
        msg += f"  Naposledy: {price_display}\n\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')

async def remove_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Použití: /remove BTC")
        return
    
    symbol = context.args[0].upper()
    chat_id = update.effective_chat.id
    
    user_config, full_config = get_user_config(chat_id)
    
    if symbol in user_config:
        del user_config[symbol]
        save_user_config(chat_id, user_config, full_config)
        await update.message.reply_text(f"🗑️ {symbol} odstraněno.")
    else:
        await update.message.reply_text(f"❌ {symbol} nesledujete.")

async def setall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Použití: /setall 5")
        return
    chat_id = update.effective_chat.id
    try:
        val = float(context.args[0]) / 100
        user_config, full_config = get_user_config(chat_id)
        for s in user_config:
            user_config[s]['threshold'] = val
        save_user_config(chat_id, user_config, full_config)
        await update.message.reply_text(f"✅ Vše nastaveno na {val*100}%")
    except:
        await update.message.reply_text("❌ Chyba formátu.")

async def update_threshold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_config, _ = get_user_config(chat_id)
    
    if not user_config:
        await update.message.reply_text("Nemáte co upravovat.")
        return ConversationHandler.END

    # Pokud uživatel zadal /update BTC
    if context.args:
        symbol = context.args[0].upper()
        if symbol in user_config:
            context.user_data['pending_symbol'] = symbol
            context.user_data['pending_name'] = symbol
            await update.message.reply_text(f"Zadejte nové % pro {symbol}:")
            return WAITING_UPDATE_THRESHOLD

    # Jinak tlačítka
    keyboard = [[InlineKeyboardButton(f"{s} ({c['threshold']*100}%)", callback_data=f"upd_{s}")] for s, c in user_config.items()]
    await update.message.reply_text("Vyberte:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END
        
async def update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.split('_')[1]
    
    context.user_data['pending_symbol'] = symbol
    context.user_data['pending_name'] = symbol
    
    await query.edit_message_text(f"Zadejte nové % pro {symbol}:")
    return WAITING_UPDATE_THRESHOLD

async def handle_update_val(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Využijeme stejnou logiku jako pro přidání
    return await handle_threshold(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Zrušeno.")
    return ConversationHandler.END

# --- Background Loop ---

async def price_check_loop(app, stop_event):
    print("🚀 Startuji kontrolu cen...")
    
    while not stop_event.is_set():
        try:
            # Načteme kompletní data všech uživatelů
            full_config = load_data('crypto_config', CONFIG_FILE)
            full_state = load_data('crypto_state', STATE_FILE)
            state_changed = False
            
            if not full_config:
                print("⚠️  Žádní uživatelé ke sledování")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            # Získáme seznam všech unikátních symbolů (kryptoměny + akcie) k dotazu (optimalizace API volání)
            all_symbols = set()
            for user_conf in full_config.values():
                all_symbols.update(user_conf.keys())
            
            if not all_symbols:
                print("⚠️  Žádné symboly ke sledování")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            print(f"📊 Kontroluji {len(all_symbols)} symbolů (kryptoměny + akcie) pro {len(full_config)} uživatelů")
            
            current_prices = {}
            for sym in all_symbols:
                p, asset_type = get_price(sym)
                if p: 
                    current_prices[sym] = p
                    asset_emoji = "₿" if asset_type == 'crypto' else "📈"
                    print(f"✅ [{sym}] {asset_emoji} ${p:,.2f}")
                else:
                    print(f"❌ [{sym}] Nepodařilo se získat cenu")
                await asyncio.sleep(0.5) # Throttle
            
            # Kontrola pro každého uživatele
            for chat_id_str, user_conf in full_config.items():
                if chat_id_str not in full_state: full_state[chat_id_str] = {}
                user_state = full_state[chat_id_str]
                
                for symbol, settings in user_conf.items():
                    if symbol not in current_prices: 
                        print(f"⚠️  [{chat_id_str}] {symbol}: Cena nedostupná")
                        continue
                    
                    curr_price = current_prices[symbol]
                    last_price = user_state.get(symbol, {}).get('last_notification_price')
                    threshold = settings.get('threshold', 0.05)
                    
                    if last_price is None:
                        # První běh
                        user_state[symbol] = {'last_notification_price': curr_price}
                        state_changed = True
                        print(f"💾 [{chat_id_str}] {symbol}: První cena uložena ${curr_price:,.2f}")
                        continue
                        
                    change_pct = abs((curr_price - last_price) / last_price)
                    
                    print(f"📊 [{chat_id_str}] {symbol}: ${curr_price:,.2f} | Změna: {change_pct*100:.2f}% (limit: {threshold*100}%)")
                    
                    if change_pct >= threshold:
                        # Alert
                        direction = "📈 VZESTUP" if curr_price > last_price else "📉 POKLES"
                        emoji = "🟢" if curr_price > last_price else "🔴"
                        
                        msg = f"""
{emoji} <b>{settings.get('name', symbol)} ({symbol})</b> {direction} <b>{change_pct*100:.1f}%</b>
💰 <b>${curr_price:,.2f}</b> (předtím: ${last_price:,.2f})
"""
                        try:
                            await app.bot.send_message(chat_id=int(chat_id_str), text=msg, parse_mode='HTML')
                            user_state[symbol]['last_notification_price'] = curr_price
                            state_changed = True
                            print(f"✅ Alert odeslán pro {chat_id_str}: {symbol} {direction} {change_pct*100:.1f}%")
                        except Exception as e:
                            print(f"❌ Chyba odeslání uživateli {chat_id_str}: {e}")

            if state_changed:
                save_data('crypto_state', STATE_FILE, full_state)
                print("💾 Stav uložen")
                
            # Čekání
            print()  # Prázdný řádek
            for _ in range(CHECK_INTERVAL):
                if stop_event.is_set(): break
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"❌ Error v loopu: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(30)

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Chybí TELEGRAM_BOT_TOKEN")
        return
    
    if DATABASE_URL:
        init_database()
        print("✅ DB Inicializována")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('list', list_cryptos))
    app.add_handler(CommandHandler('remove', remove_crypto))
    app.add_handler(CommandHandler('setall', setall))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_crypto)],
        states={WAITING_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_threshold)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_handler)
    
    upd_handler = ConversationHandler(
        entry_points=[CommandHandler('update', update_threshold_cmd), CallbackQueryHandler(update_callback, pattern='^upd_')],
        states={WAITING_UPDATE_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_update_val)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(upd_handler)

    # Background Task
    stop_event = asyncio.Event()
    
    async def post_init(app: Application):
        """Spustí background loop po inicializaci aplikace."""
        app.bg_task = asyncio.create_task(price_check_loop(app, stop_event))
        print("✅ Background price check loop spuštěn")
    
    app.post_init = post_init
    
    # Cleanup při ukončení
    def cleanup():
        print("🛑 Ukončuji aplikaci...")
        stop_event.set()
    
    atexit.register(cleanup)
    
    print("🤖 Bot běží...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
