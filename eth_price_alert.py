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
WAITING_TICKER, WAITING_THRESHOLD, WAITING_UPDATE_THRESHOLD, WAITING_ASSET_TYPE = range(4)

# Globální cache pro seznam kryptoměn z CoinGecko a CoinMarketCap
KNOWN_CRYPTO = set()
CRYPTO_COIN_IDS = {}  # Mapování symbol -> coin_id pro CoinGecko
CRYPTO_LIST_LOADED = False

# Specifické mapování pro tokeny, které mají více variant se stejným symbolem
# Mapuje symbol -> coin_id (preferujeme hlavní/populárnější token)
SPECIFIC_COIN_IDS = {
    'SAFE': 'safe',  # Safe (https://www.coingecko.com/en/coins/safe)
    'COW': 'cow-protocol',  # CoW Protocol (https://www.coingecko.com/en/coins/cow-protocol)
    'RAIL': 'railgun',  # Railgun (https://www.coingecko.com/en/coins/railgun)
}

# Blacklist známých akcií - tyto tickery NIKDY nebudou považovány za kryptoměny, i když jsou na CoinGecko
STOCK_BLACKLIST = {
    'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'NFLX', 'DIS',
    'BABA', 'V', 'JPM', 'WMT', 'MA', 'PG', 'JNJ', 'UNH', 'HD', 'PYPL',
    'BAC', 'ADBE', 'CRM', 'NKE', 'XOM', 'CVX', 'ABBV', 'COST', 'AVGO', 'PEP',
    'TMO', 'CSCO', 'ABT', 'DHR', 'ACN', 'VZ', 'CMCSA', 'NEE', 'LIN', 'WFC',
    'ORCL', 'PM', 'TXN', 'RTX', 'UPS', 'QCOM', 'DE', 'BMY', 'HON', 'LOW',
    'SPGI', 'INTU', 'AMGN', 'C', 'BLK', 'AMT', 'TJX', 'AXP', 'BKNG', 'GS',
    'ADP', 'SYK', 'ZTS', 'ISRG', 'GILD', 'ADI', 'REGN', 'CDNS', 'SNPS', 'KLAC',
    'MCHP', 'NXPI', 'FTNT', 'ANSS', 'CTSH', 'PAYX', 'CTAS', 'FAST', 'NDAQ', 'CPRT'
}

def load_crypto_list_from_coingecko():
    """Načte seznam všech kryptoměn z CoinGecko API a CoinMarketCap API."""
    global KNOWN_CRYPTO, CRYPTO_COIN_IDS, CRYPTO_LIST_LOADED
    
    if CRYPTO_LIST_LOADED:
        return KNOWN_CRYPTO
    
    crypto_symbols = set()
    coin_ids_map = {}
    
    # 1. Načteme z CoinGecko
    try:
        print("📡 Načítám seznam kryptoměn z CoinGecko...")
        url = 'https://api.coingecko.com/api/v3/coins/list'
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            for coin in data:
                symbol = coin.get('symbol', '').upper()
                coin_id = coin.get('id', '')
                if symbol and symbol not in STOCK_BLACKLIST:
                    crypto_symbols.add(symbol)
                    # Uložíme coin_id pro symbol (pokud má symbol více coin_id, vezmeme první/největší market cap)
                    if symbol not in coin_ids_map:
                        coin_ids_map[symbol] = coin_id
            print(f"✅ Načteno {len(crypto_symbols)} kryptoměn z CoinGecko")
        else:
            print(f"⚠️  Chyba při načítání z CoinGecko: Status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Chyba při načítání z CoinGecko: {e}")
    
    # 2. Načteme z CoinMarketCap (pokud je dostupný API klíč)
    # CoinMarketCap má rate limit, takže to použijeme jen jako doplněk
    # Pro teď použijeme jen CoinGecko
    
    KNOWN_CRYPTO = crypto_symbols
    CRYPTO_COIN_IDS = coin_ids_map
    CRYPTO_LIST_LOADED = True
    print(f"✅ Celkem {len(KNOWN_CRYPTO)} kryptoměn v seznamu")
    return KNOWN_CRYPTO

def is_crypto_ticker(symbol):
    """Zkontroluje, jestli je ticker kryptoměna podle CoinGecko/CoinMarketCap."""
    symbol_upper = symbol.upper()
    
    # Pokud je v blacklistu akcií, není to crypto
    if symbol_upper in STOCK_BLACKLIST:
        return False
    
    if not CRYPTO_LIST_LOADED:
        load_crypto_list_from_coingecko()
    return symbol_upper in KNOWN_CRYPTO

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
    
    # Migrace: doplníme asset_type pro tickery, které ho nemají
    user_config = full_config[str(chat_id)]
    config_changed = False
    
    # Specifické crypto tokeny, které mají být vždy nastaveny jako crypto
    FORCE_CRYPTO = ['COW', 'SAFE', 'RAIL']
    
    for symbol, settings in user_config.items():
        if 'asset_type' not in settings:
            # Vynucené crypto tokeny
            if symbol.upper() in FORCE_CRYPTO:
                settings['asset_type'] = 'crypto'
                print(f"🔄 Migrace: {symbol} nastaven jako crypto (vynuceno)")
                config_changed = True
            # Pokud ticker je v seznamu kryptoměn z CoinGecko, nastavíme crypto
            elif is_crypto_ticker(symbol):
                settings['asset_type'] = 'crypto'
                print(f"🔄 Migrace: {symbol} nastaven jako crypto")
                config_changed = True
            else:
                # Pro ostatní tickery nastavíme stock (pravděpodobně akcie)
                settings['asset_type'] = 'stock'
                print(f"🔄 Migrace: {symbol} nastaven jako stock")
                config_changed = True
        elif symbol.upper() in FORCE_CRYPTO and settings.get('asset_type') != 'crypto':
            # Pokud už má asset_type, ale je to v FORCE_CRYPTO a není to crypto, opravíme to
            settings['asset_type'] = 'crypto'
            print(f"🔄 Migrace: {symbol} opraven na crypto (z {settings.get('asset_type')})")
            config_changed = True
    
    # Pokud jsme něco změnili, uložíme to
    if config_changed:
        save_data('crypto_config', CONFIG_FILE, full_config)
        print(f"💾 Migrace uložena pro uživatele {chat_id}")
    
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
    url = f'https://min-api.cryptocompare.com/data/price?fsym={symbol.upper()}&tsyms=USD'
    headers = {}
    if CRYPTOCOMPARE_API_KEY:
        headers['authorization'] = f'Apikey {CRYPTOCOMPARE_API_KEY}'
    
    try:
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'USD' in data and data['USD'] is not None:
                return float(data['USD']), 'CryptoCompare'
            elif 'Response' in data and data['Response'] == 'Error':
                # API vrátilo chybu
                pass
    except Exception as e:
        pass
    return None, None

def get_price_from_binance(symbol):
    """Získá cenu z Binance API."""
    # Zkusíme symbol přímo s USDT párem
    binance_symbol = f"{symbol.upper()}USDT"
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
        if 'price' in data:
            return float(data['price']), 'Binance'
    except:
        pass
    return None, None

def get_price_from_coinbase(symbol):
    """Získá cenu z Coinbase API."""
    try:
        url = f'https://api.coinbase.com/v2/prices/{symbol.upper()}-USD/spot'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'amount' in data['data']:
                price = float(data['data']['amount'])
                print(f"✅ Coinbase: {symbol} = ${price:,.2f}")
                return price, 'Coinbase'
    except Exception as e:
        print(f"⚠️  Coinbase API error for {symbol}: {e}")
    return None, None

def get_price_from_kraken(symbol):
    """Získá cenu z Kraken API."""
    # Kraken používá specifické páry symbolů
    kraken_pairs = {
        'BTC': 'XXBTZUSD',
        'ETH': 'XETHZUSD',
        'XRP': 'XXRPZUSD',
        'LTC': 'XLTCZUSD',
        'BCH': 'BCHUSDT',
        'ADA': 'ADAUSD',
        'DOT': 'DOTUSD',
        'LINK': 'LINKUSD',
        'UNI': 'UNIUSD',
        'SOL': 'SOLUSD',
    }
    
    symbol_upper = symbol.upper()
    pair = kraken_pairs.get(symbol_upper, f'{symbol_upper}USD')
    
    try:
        url = f'https://api.kraken.com/0/public/Ticker?pair={pair}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and data['result']:
                # Získáme první pár z výsledku
                pair_data = next(iter(data['result'].values()))
                if 'c' in pair_data and len(pair_data['c']) > 0:
                    price = float(pair_data['c'][0])  # 'c' je last trade price
                    print(f"✅ Kraken: {symbol} = ${price:,.2f}")
                    return price, 'Kraken'
    except Exception as e:
        print(f"⚠️  Kraken API error for {symbol}: {e}")
    return None, None

def get_price_from_coingecko(symbol):
    """Získá cenu z CoinGecko API pomocí symbolu."""
    # Použijeme cache coin_id, pokud je k dispozici
    symbol_upper = symbol.upper()
    
    # Nejdřív zkontrolujeme specifické mapování (má prioritu)
    if symbol_upper in SPECIFIC_COIN_IDS:
        coin_id = SPECIFIC_COIN_IDS[symbol_upper]
        try:
            price_url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd'
            price_response = requests.get(price_url, timeout=10)
            
            if price_response.status_code == 429:
                # Rate limit - počkáme chvíli a zkusíme znovu
                print(f"⚠️  CoinGecko rate limit pro {symbol}, čekám...")
                time.sleep(2)
                price_response = requests.get(price_url, timeout=10)
            
            if price_response.status_code == 200:
                price_data = price_response.json()
                if coin_id in price_data and 'usd' in price_data[coin_id]:
                    price_val = price_data[coin_id]['usd']
                    if price_val is not None:
                        # Uložíme do cache
                        CRYPTO_COIN_IDS[symbol_upper] = coin_id
                        print(f"✅ CoinGecko (specific): {symbol} = ${price_val:,.2f}")
                        return float(price_val), 'CoinGecko'
        except Exception as e:
            print(f"⚠️  CoinGecko API error (specific) for {symbol}: {e}")
    
    # Pak zkusíme použít cache coin_id
    if CRYPTO_LIST_LOADED and symbol_upper in CRYPTO_COIN_IDS:
        coin_id = CRYPTO_COIN_IDS[symbol_upper]
        try:
            price_url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd'
            price_response = requests.get(price_url, timeout=10)
            
            if price_response.status_code == 429:
                print(f"⚠️  CoinGecko rate limit pro {symbol}, čekám...")
                time.sleep(2)
                price_response = requests.get(price_url, timeout=10)
            
            if price_response.status_code == 200:
                price_data = price_response.json()
                if coin_id in price_data and 'usd' in price_data[coin_id]:
                    price_val = price_data[coin_id]['usd']
                    if price_val is not None:
                        print(f"✅ CoinGecko (cache): {symbol} = ${price_val:,.2f}")
                        return float(price_val), 'CoinGecko'
        except Exception as e:
            print(f"⚠️  CoinGecko API error (cache) for {symbol}: {e}")
    
    # Fallback: použijeme search API (pomalejší, ale funguje pro všechny)
    try:
        search_url = f'https://api.coingecko.com/api/v3/search?query={symbol_upper}'
        search_response = requests.get(search_url, timeout=10)
        
        if search_response.status_code == 429:
            print(f"⚠️  CoinGecko rate limit pro {symbol}, čekám...")
            time.sleep(2)
            search_response = requests.get(search_url, timeout=10)
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            if 'coins' in search_data and len(search_data['coins']) > 0:
                # Najdeme všechny coiny se shodným symbolem
                matching_coins = []
                for coin in search_data['coins']:
                    coin_symbol = coin.get('symbol', '').upper()
                    if coin_symbol == symbol_upper:
                        matching_coins.append(coin)
                
                # Pokud máme více coinů, preferujeme ten s nižším market_cap_rank (vyšší market cap)
                # nebo pokud není rank, vezmeme první
                if matching_coins:
                    # Seřadíme podle market_cap_rank (nižší = lepší), None na konec
                    matching_coins.sort(key=lambda x: (x.get('market_cap_rank') is None, x.get('market_cap_rank', 999999)))
                    
                    # Zkusíme každý coin dokud nenajdeme validní cenu
                    for coin in matching_coins:
                        coin_id = coin['id']
                        # Získáme cenu pomocí coin ID
                        price_url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd'
                        price_response = requests.get(price_url, timeout=10)
                        
                        if price_response.status_code == 429:
                            print(f"⚠️  CoinGecko rate limit pro {symbol}, čekám...")
                            time.sleep(2)
                            price_response = requests.get(price_url, timeout=10)
                        
                        if price_response.status_code == 200:
                            price_data = price_response.json()
                            if coin_id in price_data and 'usd' in price_data[coin_id]:
                                price_val = price_data[coin_id]['usd']
                                if price_val is not None:
                                    # Uložíme coin_id do cache pro příště
                                    CRYPTO_COIN_IDS[symbol_upper] = coin_id
                                    print(f"✅ CoinGecko (search): {symbol} = ${price_val:,.2f}")
                                    return float(price_val), 'CoinGecko'
                        # Pokud tento coin nevrátil cenu, zkusíme další
    except Exception as e:
        print(f"⚠️  CoinGecko API error (search) for {symbol}: {e}")
    
    return None, None

def get_crypto_price(symbol):
    """Získá aktuální cenu kryptoměny z náhodně vybraného API s retry mechanikou."""
    # Prioritizujeme API podle spolehlivosti
    api_functions = [
        get_price_from_binance,      # Nejrychlejší a nejspolehlivější
        get_price_from_coinbase,     # Velmi spolehlivé
        get_price_from_cryptocompare, # Dobré
        get_price_from_kraken,       # Pro specifické tokeny
        get_price_from_coingecko,    # Má rate limit, ale nejvíce tokenů
    ]
    
    # Náhodně promícháme první 3 API pro load balancing
    first_three = api_functions[:3]
    random.shuffle(first_three)
    api_functions = first_three + api_functions[3:]
    
    last_error = None
    for api_func in api_functions:
        try:
            price, api_name = api_func(symbol)
            if price is not None:
                print(f"✅ [{symbol}] Cena získána z {api_name}: ${price:,.2f}")
                return price
            else:
                print(f"⚠️  [{symbol}] {api_func.__name__} nevrátil cenu")
        except Exception as e:
            last_error = e
            print(f"⚠️  Chyba v {api_func.__name__} pro {symbol}: {e}")
            continue
    
    print(f"❌ [{symbol}] Všechna crypto API selhala. Poslední chyba: {last_error}")
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
            print(f"📡 Zkouším endpoint: {url}")
            response = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
            print(f"📊 Status code: {response.status_code}")
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

def get_price(symbol, asset_type=None):
    """Získá cenu kryptoměny nebo akcie. Pokud je zadán asset_type, použije ho. Jinak detekuje automaticky."""
    symbol_upper = symbol.upper()
    
    # Pokud je ticker v seznamu kryptoměn z CoinGecko, zkusíme jen kryptoměnu
    if is_crypto_ticker(symbol_upper):
        print(f"🔍 [{symbol_upper}] Je kryptoměna (CoinGecko), zkouším jen crypto API")
        price = get_crypto_price(symbol_upper)
        if price is not None:
            print(f"✅ Nalezena kryptoměna: {symbol_upper} = ${price}")
            return price, 'crypto'
        print(f"❌ Kryptoměna {symbol_upper} nebyla nalezena v crypto API")
        return None, None
    
    # Pokud je zadán typ, použijeme ho
    if asset_type == 'crypto':
        print(f"🔍 [{symbol_upper}] Typ je crypto (z konfigurace), zkouším crypto API")
        price = get_crypto_price(symbol_upper)
        if price is not None:
            return price, 'crypto'
        return None, None
    elif asset_type == 'stock':
        print(f"🔍 [{symbol_upper}] Typ je stock (z konfigurace), zkouším stock API")
        price, api_name = get_stock_price(symbol_upper)
        if price is not None:
            return price, 'stock'
        return None, None
    
    # Automatická detekce - nejdřív kryptoměna, pak akcie
    print(f"🔍 [{symbol_upper}] Automatická detekce - zkouším kryptoměnu")
    price = get_crypto_price(symbol_upper)
    if price is not None:
        print(f"✅ Nalezena kryptoměna: {symbol_upper} = ${price}")
        return price, 'crypto'
    
    print(f"🔍 [{symbol_upper}] Není kryptoměna, zkouším akcii")
    price, api_name = get_stock_price(symbol_upper)
    if price is not None:
        print(f"✅ Nalezena akcie: {symbol_upper} = ${price} z {api_name}")
        return price, 'stock'
    
    print(f"❌ {symbol_upper} nebyl nalezen ani jako kryptoměna, ani jako akcie")
    return None, None

def validate_ticker_with_type(symbol, asset_type):
    """Ověří ticker s daným typem a vrátí (is_valid, name, price, asset_type)."""
    print(f"🔍 Validuji ticker: {symbol} jako {asset_type}")
    price, detected_type = get_price(symbol.upper(), asset_type=asset_type)
    print(f"📊 Výsledek get_price: price={price}, detected_type={detected_type}")
    
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
            except Exception as e:
                print(f"⚠️  Chyba při získávání názvu akcie: {e}")
        return True, name, price, asset_type
    print(f"❌ Ticker {symbol} nebyl nalezen jako {asset_type}")
    return False, None, None, None

def validate_ticker(symbol):
    """Ověří ticker a vrátí (is_valid, name, price, asset_type). Používá automatickou detekci."""
    print(f"🔍 Validuji ticker: {symbol}")
    price, asset_type = get_price(symbol.upper())
    print(f"📊 Výsledek get_price: price={price}, asset_type={asset_type}")
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
            except Exception as e:
                print(f"⚠️  Chyba při získávání názvu akcie: {e}")
        return True, name, price, asset_type
    print(f"❌ Ticker {symbol} nebyl nalezen")
    return False, None, None, None

# --- Telegram Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 <b>CryptoWatch Pro</b>\n\n"
        "Automatické upozornění na významné změny cen kryptoměn a akcií.\n\n"
        "⚡ <b>Jak to funguje:</b>\n"
        "Nastavíte si prahovou hodnotu (např. 5%). Bot vás upozorní <b>POUZE když</b> cena překročí tento limit <b>nahoru nebo dolů</b>.\n\n"
        "✅ <b>Výhody:</b>\n"
        "• <b>Nemusíte sledovat denní/měsíční změny</b>\n"
        "• Dostanete upozornění jen na <b>reálné významné pohyby</b>\n"
        "• <b>Mnohem efektivnější</b> než neustálé sledování cen\n"
        "• Žádné zbytečné notifikace - jen když to opravdu stojí za to\n\n"
        "📊 <b>Podporuje:</b> Kryptoměny (BTC, ETH) a akcie (AAPL, TSLA)\n\n"
        "⚡ <b>Rychlý start:</b>\n"
        "/add BTC - Přidat kryptoměnu\n"
        "/add AAPL - Přidat akcii\n"
        "/list - Zobrazit sledované\n"
        "/help - Více informací",
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>CryptoWatch Pro - Nápověda</b>\n\n"
        "⚡ <b>Jak to funguje:</b>\n"
        "Bot kontroluje ceny každou minutu. <b>Upozornění dostanete pouze když</b> cena překročí váš nastavený práh <b>nahoru nebo dolů</b>.\n\n"
        "✅ <b>Výhoda:</b> Nemusíte sledovat denní/měsíční změny - dostanete upozornění jen na reálné významné pohyby. Mnohem efektivnější!\n\n"
        "🔹 <b>Příkazy:</b>\n\n"
        "<b>/add TICKER</b> - Přidat kryptoměnu nebo akcii\n"
        "   /add BTC, /add AAPL\n"
        "   Bot se zeptá na prahovou hodnotu (např. 5 pro 5%)\n\n"
        "<b>/list</b> - Zobrazit všechny sledované\n\n"
        "<b>/update [TICKER]</b> - Změnit prahovou hodnotu\n\n"
        "<b>/setall %</b> - Nastavit stejnou hodnotu pro všechny\n"
        "   Příklad: /setall 5\n\n"
        "<b>/remove TICKER</b> - Odebrat ze sledování\n\n"
        "<b>/help</b> - Tato nápověda",
        parse_mode='HTML'
    )

async def add_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Použití: /add BTC")
        return ConversationHandler.END
    
    symbol = context.args[0].upper()
    
    # Uložíme symbol do kontextu
    context.user_data['pending_symbol'] = symbol
    
    # Zeptáme se uživatele na typ assetu
    keyboard = [
        [InlineKeyboardButton("🪙 Kryptoměna", callback_data=f"asset_crypto_{symbol}")],
        [InlineKeyboardButton("📈 Akcie", callback_data=f"asset_stock_{symbol}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔍 <b>{symbol}</b>\n\n"
        "Je to kryptoměna nebo akcie?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return WAITING_ASSET_TYPE

async def handle_asset_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro výběr typu assetu (crypto/stock)."""
    query = update.callback_query
    await query.answer()
    
    # Parsujeme callback data: asset_crypto_BTC nebo asset_stock_AAPL
    data_parts = query.data.split('_')
    asset_type = data_parts[1]  # 'crypto' nebo 'stock'
    symbol = data_parts[2]  # ticker symbol
    
    await query.edit_message_text(f"🔍 Ověřuji {symbol} jako {asset_type}...")
    
    # Validujeme ticker s daným typem
    is_valid, name, price, detected_type = validate_ticker_with_type(symbol, asset_type)
    
    if not is_valid:
        asset_name = "kryptoměna" if asset_type == "crypto" else "akcie"
        await query.message.reply_text(f"❌ {symbol} nebyl nalezen jako {asset_name}.")
        return ConversationHandler.END
    
    # Uložíme do paměti konverzace
    context.user_data['pending_symbol'] = symbol
    context.user_data['pending_name'] = name
    context.user_data['pending_price'] = price
    context.user_data['pending_asset_type'] = asset_type
    
    asset_emoji = "🪙" if asset_type == "crypto" else "📈"
    await query.message.reply_text(
        f"✅ {asset_emoji} <b>{name}</b> (${price:,.2f})\n\n"
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
        asset_type = context.user_data.get('pending_asset_type', 'crypto')  # Default crypto pro zpětnou kompatibilitu
        
        if not symbol:
            await update.message.reply_text("❌ Chyba kontextu. Zkuste /add znovu.")
            return ConversationHandler.END
        
        # Načtení a úprava konfigurace uživatele
        user_config, full_config = get_user_config(chat_id)
        user_config[symbol] = {'name': name, 'threshold': threshold, 'asset_type': asset_type}
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

async def broadcast_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pošle zprávu o updatu všem uživatelům (pouze pro admina)."""
    chat_id = update.effective_chat.id
    
    # Kontrola, jestli je to admin
    if ADMIN_CHAT_ID and str(chat_id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("❌ Tento příkaz je pouze pro admina.")
        return
    
    await update.message.reply_text("📤 Posílám zprávu o updatu všem uživatelům...")
    
    # Načteme všechny uživatele
    full_config = load_data('crypto_config', CONFIG_FILE)
    
    if not full_config:
        await update.message.reply_text("❌ Žádní uživatelé v databázi.")
        return
    
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
    
    for user_chat_id in full_config.keys():
        try:
            await context.bot.send_message(
                chat_id=int(user_chat_id),
                text=message,
                parse_mode='HTML'
            )
            success_count += 1
            await asyncio.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"❌ Chyba při odesílání uživateli {user_chat_id}: {e}")
            fail_count += 1
    
    summary = f"✅ Zpráva odeslána!\n\n📊 Statistika:\n✅ Úspěšně: {success_count}\n❌ Chyba: {fail_count}"
    await update.message.reply_text(summary)

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
            
            # Získáme seznam všech unikátních symbolů s jejich typy (kryptoměny + akcie) k dotazu (optimalizace API volání)
            symbol_types = {}  # {symbol: asset_type}
            for user_conf in full_config.values():
                for sym, settings in user_conf.items():
                    # Pokud symbol ještě není v mapě, přidáme ho s typem z konfigurace
                    if sym not in symbol_types:
                        # Zkusíme získat typ z konfigurace, pokud není, použijeme CoinGecko seznam nebo None
                        asset_type = settings.get('asset_type')
                        if not asset_type:
                            # Pokud není v konfiguraci, zkontrolujeme CoinGecko seznam
                            asset_type = 'crypto' if is_crypto_ticker(sym) else None
                        symbol_types[sym] = asset_type
            
            if not symbol_types:
                print("⚠️  Žádné symboly ke sledování")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            print(f"📊 Kontroluji {len(symbol_types)} symbolů (kryptoměny + akcie) pro {len(full_config)} uživatelů")
            
            current_prices = {}
            for sym, asset_type in symbol_types.items():
                p, detected_type = get_price(sym, asset_type=asset_type)
                if p: 
                    current_prices[sym] = p
                    asset_emoji = "₿" if detected_type == 'crypto' else "📈"
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
    
    # Načteme seznam kryptoměn z CoinGecko při startu
    load_crypto_list_from_coingecko()
    
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
    app.add_handler(CommandHandler('broadcast', broadcast_update))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_crypto)],
        states={
            WAITING_ASSET_TYPE: [CallbackQueryHandler(handle_asset_type_selection, pattern='^asset_(crypto|stock)_')],
            WAITING_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_threshold)]
        },
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
