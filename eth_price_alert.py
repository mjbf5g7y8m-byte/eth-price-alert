#!/usr/bin/env python3
"""
Crypto Price Alert Bot
Sleduje ceny kryptoměn a posílá upozornění na Telegram při změně o nastavené procento.
Umožňuje interaktivní nastavení přes Telegram.
"""
import json
import os
import time
import requests
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# Konfigurace
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
STATE_FILE = 'crypto_price_state.json'
CONFIG_FILE = 'crypto_config.json'
CHECK_INTERVAL = 60  # Kontrola každou minutu (v sekundách)
CRYPTOCOMPARE_API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY', '7ffa2f0b80215a9e12406537b44f7dafc8deda54354efcfda93fac2eaaaeaf20')

# Stavy konverzace
WAITING_TICKER, WAITING_THRESHOLD, WAITING_UPDATE_THRESHOLD = range(3)

# Výchozí kryptoměny (pokud uživatel nic nenastaví)
DEFAULT_CRYPTOS = [
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
    return {}


def save_state(state):
    """Uloží stav do souboru."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_config():
    """Načte konfiguraci uživatele (sledované kryptoměny a thresholdy)."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # Výchozí konfigurace
    config = {}
    for symbol, name in DEFAULT_CRYPTOS:
        config[symbol] = {
            'name': name,
            'threshold': 0.001  # 0.1% default
        }
    save_config(config)
    return config


def save_config(config):
    """Uloží konfiguraci."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_crypto_price(symbol):
    """Získá aktuální cenu kryptoměny z CryptoCompare API."""
    try:
        url = f'https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD&api_key={CRYPTOCOMPARE_API_KEY}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'USD' in data:
            return float(data['USD'])
        elif 'Response' in data and data['Response'] == 'Error':
            return None
        else:
            return None
    except (requests.RequestException, KeyError, ValueError):
        return None


def validate_ticker(symbol):
    """Ověří, jestli je ticker platný."""
    price = get_crypto_price(symbol.upper())
    if price is not None:
        # Zkusíme získat název kryptoměny
        try:
            url = f'https://min-api.cryptocompare.com/data/coin/generalinfo?fsyms={symbol.upper()}&tsym=USD&api_key={CRYPTOCOMPARE_API_KEY}'
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'Data' in data and len(data['Data']) > 0:
                    name = data['Data'][0].get('CoinInfo', {}).get('FullName', symbol.upper())
                    return True, name, price
        except:
            pass
        return True, symbol.upper(), price
    return False, None, None


def calculate_price_change(current_price, last_price):
    """Vypočítá procentuální změnu ceny."""
    if last_price is None:
        return None
    return abs((current_price - last_price) / last_price)


async def send_telegram_notification(bot, symbol, name, current_price, last_price, price_change_pct):
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
    
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='HTML'
        )
        print(f"✅ Upozornění odesláno: {name} ({symbol}) {direction} o {price_change_pct:.2f}%")
        return True
    except Exception as e:
        print(f"❌ Chyba při odesílání na Telegram: {e}")
        return False


# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro /start příkaz."""
    chat_id = update.effective_chat.id
    print(f"📱 Příkaz /start od chat_id: {chat_id}")
    
    await update.message.reply_text(
        "🚀 <b>Crypto Price Alert Bot</b>\n\n"
        "Použití:\n"
        "/add TICKER - Přidá kryptoměnu ke sledování\n"
        "/list - Zobrazí seznam sledovaných kryptoměn\n"
        "/update - Změní threshold pro sledovanou kryptoměnu\n"
        "/remove TICKER - Odebere kryptoměnu ze sledování\n"
        "/help - Zobrazí nápovědu\n\n"
        "Příklad: /add BTC",
        parse_mode='HTML'
    )


async def add_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro /add příkaz."""
    print(f"📱 Příkaz /add od chat_id: {update.effective_chat.id}, args: {context.args}")
    
    if not context.args:
        await update.message.reply_text(
            "❌ Zadejte ticker kryptoměny\n"
            "Příklad: /add BTC"
        )
        return ConversationHandler.END
    
    symbol = context.args[0].upper()
    print(f"🔍 Kontroluji ticker: {symbol}")
    
    # Ověříme ticker
    is_valid, name, price = validate_ticker(symbol)
    print(f"🔍 Výsledek validace: is_valid={is_valid}, name={name}, price={price}")
    
    if not is_valid:
        await update.message.reply_text(
            f"❌ Ticker <b>{symbol}</b> není platný nebo kryptoměna neexistuje.\n\n"
            "Zkuste jiný ticker (např. BTC, ETH, SOL).",
            parse_mode='HTML'
        )
        return
    
    # Zobrazíme informace a zeptáme se na threshold
    await update.message.reply_text(
        f"✅ <b>{name} ({symbol})</b> je platný ticker!\n\n"
        f"💰 Aktuální cena: <b>${price:,.2f}</b>\n\n"
        "📊 Zadejte threshold v procentech (např. 0.1 pro 0.1%, nebo 5 pro 5%):",
        parse_mode='HTML'
    )
    
    # Uložíme do kontextu pro další krok
    context.user_data['pending_symbol'] = symbol
    context.user_data['pending_name'] = name
    context.user_data['pending_price'] = price
    
    return WAITING_THRESHOLD


async def handle_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro zadání thresholdu."""
    try:
        threshold_input = update.message.text.strip()
        threshold = float(threshold_input) / 100  # Převod z procent na desetinné číslo
        
        if threshold <= 0:
            await update.message.reply_text(
                "❌ Threshold musí být větší než 0.\n"
                "Zadejte znovu (např. 0.1 pro 0.1%):"
            )
            return WAITING_THRESHOLD
        
        symbol = context.user_data.get('pending_symbol')
        name = context.user_data.get('pending_name')
        
        if not symbol:
            await update.message.reply_text("❌ Chyba: Ztracen kontext. Začněte znovu příkazem /add")
            return ConversationHandler.END
        
        # Načteme a aktualizujeme konfiguraci
        config = load_config()
        config[symbol] = {
            'name': name,
            'threshold': threshold
        }
        save_config(config)
        print(f"💾 Uloženo do konfigurace: {symbol} = {config[symbol]}")
        
        # Načteme a aktualizujeme stav
        state = load_state()
        if symbol not in state:
            state[symbol] = {
                'last_notification_price': None,
                'last_notification_time': None
            }
        save_state(state)
        print(f"💾 Uloženo do stavu: {symbol}")
        
        # Ověříme, že se to skutečně uložilo
        verify_config = load_config()
        if symbol in verify_config:
            print(f"✅ Ověření: {symbol} je v konfiguraci: {verify_config[symbol]}")
        else:
            print(f"❌ CHYBA: {symbol} NENÍ v konfiguraci po uložení!")
        
        await update.message.reply_text(
            f"✅ <b>{name} ({symbol})</b> přidáno ke sledování!\n\n"
            f"📊 Threshold: <b>{threshold*100}%</b>\n"
            f"💰 Aktuální cena: <b>${context.user_data.get('pending_price', 0):,.2f}</b>\n\n"
            "Bot bude posílat upozornění při změně o nastavené procento.",
            parse_mode='HTML'
        )
        
        # Vyčistíme kontext
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Neplatný formát. Zadejte číslo (např. 0.1 pro 0.1% nebo 5 pro 5%):"
        )
        return WAITING_THRESHOLD


async def list_cryptos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro /list příkaz."""
    config = load_config()
    state = load_state()
    
    if not config:
        await update.message.reply_text("📋 Žádné kryptoměny nejsou sledovány.")
        return
    
    message = "📋 <b>Sledované kryptoměny:</b>\n\n"
    for symbol, crypto_config in config.items():
        name = crypto_config.get('name', symbol)
        threshold = crypto_config.get('threshold', 0.001) * 100
        last_price = state.get(symbol, {}).get('last_notification_price')
        
        if last_price:
            message += f"• <b>{name} ({symbol})</b>\n"
            message += f"  Threshold: {threshold:.2f}%\n"
            message += f"  Poslední cena: ${last_price:,.2f}\n\n"
        else:
            message += f"• <b>{name} ({symbol})</b>\n"
            message += f"  Threshold: {threshold:.2f}%\n"
            message += f"  Status: Čeká na první kontrolu\n\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def remove_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro /remove příkaz."""
    if not context.args:
        await update.message.reply_text(
            "❌ Zadejte ticker kryptoměny\n"
            "Příklad: /remove BTC"
        )
        return
    
    symbol = context.args[0].upper()
    config = load_config()
    
    if symbol not in config:
        await update.message.reply_text(
            f"❌ <b>{symbol}</b> není ve sledovaných kryptoměnách.",
            parse_mode='HTML'
        )
        return
    
    name = config[symbol].get('name', symbol)
    del config[symbol]
    save_config(config)
    
    # Odstraníme i ze stavu
    state = load_state()
    if symbol in state:
        del state[symbol]
        save_state(state)
    
    await update.message.reply_text(
        f"✅ <b>{name} ({symbol})</b> odebráno ze sledování.",
        parse_mode='HTML'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro /help příkaz."""
    chat_id = update.effective_chat.id
    print(f"📱 Příkaz /help od chat_id: {chat_id}")
    
    await update.message.reply_text(
        "📖 <b>Nápověda</b>\n\n"
        "<b>Příkazy:</b>\n"
        "/start - Zobrazí úvodní zprávu\n"
        "/add TICKER - Přidá kryptoměnu ke sledování\n"
        "/list - Zobrazí seznam sledovaných kryptoměn\n"
        "/update - Změní threshold pro sledovanou kryptoměnu\n"
        "/remove TICKER - Odebere kryptoměnu ze sledování\n"
        "/help - Zobrazí tuto nápovědu\n\n"
        "<b>Příklad:</b>\n"
        "/add BTC\n"
        "Bot se zeptá na threshold (např. 0.1 pro 0.1%)\n\n"
        "/update\n"
        "Vyberete kryptoměnu a zadáte nový threshold\n\n"
        "Bot pak bude posílat upozornění při změně ceny o nastavené procento.",
        parse_mode='HTML'
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro zrušení konverzace."""
    context.user_data.clear()
    await update.message.reply_text("❌ Operace zrušena.")
    return ConversationHandler.END


async def update_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro /update příkaz - změna thresholdu existující kryptoměny."""
    config = load_config()
    if not config:
        await update.message.reply_text(
            "❌ Momentálně nesleduji žádné kryptoměny. Použijte /add pro přidání.",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    if not context.args:
        # Zobrazíme seznam kryptoměn s inline tlačítky
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = []
        for symbol, data in config.items():
            name = data.get('name', symbol)
            threshold = data.get('threshold', 0)
            keyboard.append([InlineKeyboardButton(
                f"{name} ({symbol}) - {threshold*100}%",
                callback_data=f"update_{symbol}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Vyberte kryptoměnu, u které chcete změnit threshold:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    # Pokud je zadán symbol jako argument
    symbol = context.args[0].upper()
    if symbol not in config:
        await update.message.reply_text(
            f"❌ <b>{symbol}</b> není ve sledovaných kryptoměnách.\n"
            "Použijte /list pro zobrazení seznamu.",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    name = config[symbol].get('name', symbol)
    current_threshold = config[symbol].get('threshold', 0)
    
    context.user_data['pending_symbol'] = symbol
    context.user_data['pending_name'] = name
    
    await update.message.reply_text(
        f"📊 <b>{name} ({symbol})</b>\n"
        f"Aktuální threshold: <b>{current_threshold*100}%</b>\n\n"
        "Zadejte nový threshold (např. 0.1 pro 0.1%, 5 pro 5%):",
        parse_mode='HTML'
    )
    
    return WAITING_UPDATE_THRESHOLD


async def handle_update_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro zadání nového thresholdu."""
    try:
        threshold_input = update.message.text.strip()
        threshold = float(threshold_input) / 100  # Převod z procent na desetinné číslo
        
        if threshold <= 0:
            await update.message.reply_text(
                "❌ Threshold musí být větší než 0.\n"
                "Zadejte znovu (např. 0.1 pro 0.1%):"
            )
            return WAITING_UPDATE_THRESHOLD
        
        symbol = context.user_data.get('pending_symbol')
        name = context.user_data.get('pending_name')
        
        if not symbol:
            await update.message.reply_text("❌ Chyba: Ztracen kontext. Začněte znovu příkazem /update")
            return ConversationHandler.END
        
        # Načteme a aktualizujeme konfiguraci
        config = load_config()
        if symbol in config:
            old_threshold = config[symbol].get('threshold', 0)
            config[symbol]['threshold'] = threshold
            save_config(config)
            
            await update.message.reply_text(
                f"✅ <b>{name} ({symbol})</b> - threshold aktualizován!\n\n"
                f"📊 Starý threshold: <b>{old_threshold*100}%</b>\n"
                f"📊 Nový threshold: <b>{threshold*100}%</b>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ Kryptoměna {symbol} nebyla nalezena ve sledovaných."
            )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Neplatný formát thresholdu. Zadejte číslo (např. 0.1 pro 0.1%):"
        )
        return WAITING_UPDATE_THRESHOLD


async def update_threshold_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pro callback z inline tlačítka pro změnu thresholdu."""
    query = update.callback_query
    await query.answer()
    
    symbol = query.data.replace("update_", "")
    config = load_config()
    
    if symbol not in config:
        await query.edit_message_text(f"❌ Kryptoměna {symbol} nebyla nalezena.")
        return
    
    name = config[symbol].get('name', symbol)
    current_threshold = config[symbol].get('threshold', 0)
    
    # Uložíme do kontextu
    context.user_data['pending_symbol'] = symbol
    context.user_data['pending_name'] = name
    
    await query.edit_message_text(
        f"📊 <b>{name} ({symbol})</b>\n"
        f"Aktuální threshold: <b>{current_threshold*100}%</b>\n\n"
        "Zadejte nový threshold (např. 0.1 pro 0.1%, 5 pro 5%):",
        parse_mode='HTML'
    )
    
    # Vrátíme stav pro ConversationHandler
    return WAITING_UPDATE_THRESHOLD


async def price_check_loop(application: Application):
    """Hlavní smyčka pro kontrolu cen."""
    print("🚀 Crypto Price Alert Bot spuštěn")
    print(f"⏱️  Kontrola každých {CHECK_INTERVAL} sekund\n")
    
    while True:
        try:
            config = load_config()
            state = load_state()
            
            if not config:
                print("⚠️  Žádné kryptoměny ke sledování. Přidejte je přes /add")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            for symbol, crypto_config in config.items():
                name = crypto_config.get('name', symbol)
                threshold = crypto_config.get('threshold', 0.001)
                
                # Získání aktuální ceny
                current_price = get_crypto_price(symbol)
                
                if current_price is None:
                    print(f"⏳ [{timestamp}] {symbol}: Chyba při získávání ceny")
                    continue
                
                # Zajištění, že stav existuje
                if symbol not in state:
                    state[symbol] = {
                        'last_notification_price': None,
                        'last_notification_time': None
                    }
                
                last_price = state[symbol].get('last_notification_price')
                
                # Pokud je to první kontrola, uložíme cenu
                if last_price is None:
                    state[symbol]['last_notification_price'] = current_price
                    state[symbol]['last_notification_time'] = datetime.now().isoformat()
                    save_state(state)
                    print(f"💾 [{timestamp}] {name} ({symbol}): První cena uložena: ${current_price:,.2f}")
                else:
                    # Výpočet změny
                    price_change = calculate_price_change(current_price, last_price)
                    
                    if price_change and price_change >= threshold:
                        # Odeslání upozornění
                        price_change_pct = price_change * 100
                        if await send_telegram_notification(
                            application.bot,
                            symbol,
                            name,
                            current_price,
                            last_price,
                            price_change_pct
                        ):
                            # Aktualizace stavu
                            state[symbol]['last_notification_price'] = current_price
                            state[symbol]['last_notification_time'] = datetime.now().isoformat()
                            save_state(state)
                    else:
                        change_pct = (price_change * 100) if price_change else 0
                        print(f"📊 [{timestamp}] {name} ({symbol}): ${current_price:,.2f} | Změna: {change_pct:.2f}% (limit: {threshold*100}%)")
                
                # Pauza mezi kryptoměnami
                await asyncio.sleep(1)
            
            # Hlavní pauza před další kontrolou
            print()  # Prázdný řádek
            remaining_time = max(0, CHECK_INTERVAL - (len(config) * 1))
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)
                
        except Exception as e:
            print(f"❌ Chyba v price check loop: {e}")
            await asyncio.sleep(CHECK_INTERVAL)


def main():
    """Hlavní funkce."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Chyba: Nastavte proměnnou prostředí TELEGRAM_BOT_TOKEN")
        return
    
    print("🔍 Debug - Kontrola environment variables:")
    print(f"   TELEGRAM_BOT_TOKEN: {'✅ Nastaveno' if TELEGRAM_BOT_TOKEN else '❌ Chybí'}")
    print(f"   TELEGRAM_CHAT_ID: {'✅ Nastaveno' if TELEGRAM_CHAT_ID else '⚠️  Volitelné (bot odpovídá všem)'}")
    print()
    
    # Vytvoření aplikace
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Conversation handler pro přidávání kryptoměn
    add_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_crypto)],
        states={
            WAITING_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_threshold)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Handler pro zpracování zprávy po callback (když uživatel zadá threshold)
    async def handle_threshold_after_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler pro zpracování threshold po callback."""
        if context.user_data.get('waiting_for_threshold'):
            return await handle_update_threshold(update, context)
        return None
    
    # Conversation handler pro změnu thresholdu
    update_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('update', update_threshold)],
        states={
            WAITING_UPDATE_THRESHOLD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_update_threshold)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Handler pro zpracování zprávy po callback (když uživatel klikne na tlačítko a pak zadá threshold)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_threshold_after_callback
    ))
    
    # Handler pro callback z inline tlačítka (update threshold)
    async def update_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapper pro callback, který nastaví kontext a pokračuje v konverzaci."""
        query = update.callback_query
        await query.answer()
        
        symbol = query.data.replace("update_", "")
        config = load_config()
        
        if symbol not in config:
            await query.edit_message_text(f"❌ Kryptoměna {symbol} nebyla nalezena.")
            return
        
        name = config[symbol].get('name', symbol)
        current_threshold = config[symbol].get('threshold', 0)
        
        # Uložíme do kontextu
        context.user_data['pending_symbol'] = symbol
        context.user_data['pending_name'] = name
        context.user_data['waiting_for_threshold'] = True
        
        await query.edit_message_text(
            f"📊 <b>{name} ({symbol})</b>\n"
            f"Aktuální threshold: <b>{current_threshold*100}%</b>\n\n"
            "Zadejte nový threshold (např. 0.1 pro 0.1%, 5 pro 5%):",
            parse_mode='HTML'
        )
    
    # Registrace handlerů
    application.add_handler(CommandHandler('start', start))
    application.add_handler(add_conv_handler)
    application.add_handler(update_conv_handler)
    application.add_handler(CallbackQueryHandler(update_callback_wrapper, pattern=r'^update_'))
    application.add_handler(CommandHandler('list', list_cryptos))
    application.add_handler(CommandHandler('remove', remove_crypto))
    application.add_handler(CommandHandler('help', help_command))
    
    # Spuštění price check loop jako background task
    async def post_init(app: Application):
        asyncio.create_task(price_check_loop(app))
    
    application.post_init = post_init
    
    print("🤖 Telegram bot připraven")
    print("📱 Posílejte příkazy na Telegram (/start, /add, /list, atd.)")
    
    # Spuštění bota (run_polling má vlastní event loop management)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
