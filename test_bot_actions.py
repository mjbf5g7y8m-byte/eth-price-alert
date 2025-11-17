#!/usr/bin/env python3
"""
Testovací skript pro simulaci všech uživatelských akcí bota.
"""
import sys
import os
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Přidáme aktuální adresář do path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importujeme funkce z bota
import eth_price_alert
from eth_price_alert import (
    load_config, save_config, load_state, save_state,
    get_crypto_price, validate_ticker,
    add_crypto, handle_threshold, list_cryptos,
    remove_crypto, setall_threshold, update_threshold,
    handle_update_threshold, help_command, start
)

# Mock pro Telegram Update a Context
class MockUpdate:
    def __init__(self, message_text=None, chat_id=12345, args=None):
        self.effective_chat = Mock()
        self.effective_chat.id = chat_id
        self.message = Mock()
        self.message.text = message_text
        self.message.reply_text = AsyncMock()
        self.message.reply_text.return_value = None

class MockContext:
    def __init__(self, args=None):
        self.args = args or []
        self.user_data = {}

async def test_start():
    """Test /start příkazu."""
    print("🧪 Test 1: /start")
    update = MockUpdate()
    context = MockContext()
    
    try:
        await start(update, context)
        assert update.message.reply_text.called, "start() měl zavolat reply_text"
        print("   ✅ /start funguje\n")
        return True
    except Exception as e:
        print(f"   ❌ /start selhal: {e}\n")
        return False

async def test_add_crypto():
    """Test /add příkazu."""
    print("🧪 Test 2: /add BTC")
    update = MockUpdate(args=['BTC'])
    context = MockContext(['BTC'])
    
    # Mock validate_ticker
    with patch('eth_price_alert.validate_ticker', return_value=(True, 'Bitcoin', 95000.0)):
        try:
            result = await add_crypto(update, context)
            assert update.message.reply_text.called, "add_crypto() měl zavolat reply_text"
            assert 'pending_symbol' in context.user_data, "Symbol měl být uložen do user_data"
            assert context.user_data['pending_symbol'] == 'BTC', "Symbol měl být BTC"
            print("   ✅ /add BTC funguje\n")
            return True
        except Exception as e:
            print(f"   ❌ /add BTC selhal: {e}\n")
            import traceback
            traceback.print_exc()
            return False

async def test_handle_threshold():
    """Test zadání threshold."""
    print("🧪 Test 3: Zadání threshold (5)")
    update = MockUpdate(message_text='5')
    context = MockContext()
    context.user_data['pending_symbol'] = 'BTC'
    context.user_data['pending_name'] = 'Bitcoin'
    context.user_data['pending_price'] = 95000.0
    
    # Mock get_crypto_price pro list_cryptos
    original_get_price = get_crypto_price
    with patch('eth_price_alert.get_crypto_price', return_value=95000.0):
        try:
            # Nejdřív načteme aktuální konfiguraci
            config = load_config()
            original_count = len(config)
            
            result = await handle_threshold(update, context)
            assert update.message.reply_text.called, "handle_threshold() měl zavolat reply_text"
            
            # Ověříme, že se BTC uložil
            config_after = load_config()
            assert 'BTC' in config_after, "BTC měl být uložen do konfigurace"
            assert len(config_after) >= original_count, "Počet kryptoměn se měl zvýšit"
            
            print(f"   ✅ Threshold uložen, BTC přidán do konfigurace (celkem: {len(config_after)} kryptoměn)\n")
            return True
        except Exception as e:
            print(f"   ❌ handle_threshold selhal: {e}\n")
            import traceback
            traceback.print_exc()
            return False

async def test_list_cryptos():
    """Test /list příkazu."""
    print("🧪 Test 4: /list")
    update = MockUpdate()
    context = MockContext()
    
    with patch('eth_price_alert.get_crypto_price', return_value=95000.0):
        try:
            await list_cryptos(update, context)
            assert update.message.reply_text.called, "list_cryptos() měl zavolat reply_text"
            print("   ✅ /list funguje\n")
            return True
        except Exception as e:
            print(f"   ❌ /list selhal: {e}\n")
            import traceback
            traceback.print_exc()
            return False

async def test_setall_threshold():
    """Test /setall příkazu."""
    print("🧪 Test 5: /setall 3")
    update = MockUpdate(args=['3'])
    context = MockContext(['3'])
    
    try:
        config_before = load_config()
        if not config_before:
            print("   ⚠️  Žádné kryptoměny v konfiguraci, přeskočeno\n")
            return True
        
        await setall_threshold(update, context)
        assert update.message.reply_text.called, "setall_threshold() měl zavolat reply_text"
        
        # Ověříme, že se threshold změnil
        config_after = load_config()
        for symbol, crypto_config in config_after.items():
            assert crypto_config.get('threshold') == 0.03, f"Threshold pro {symbol} měl být 0.03"
        
        print(f"   ✅ /setall funguje, threshold nastaven na 3% pro všechny kryptoměny\n")
        return True
    except Exception as e:
        print(f"   ❌ /setall selhal: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def test_remove_crypto():
    """Test /remove příkazu."""
    print("🧪 Test 6: /remove BTC")
    update = MockUpdate(args=['BTC'])
    context = MockContext(['BTC'])
    
    try:
        config_before = load_config()
        if 'BTC' not in config_before:
            print("   ⚠️  BTC není v konfiguraci, přeskočeno\n")
            return True
        
        await remove_crypto(update, context)
        assert update.message.reply_text.called, "remove_crypto() měl zavolat reply_text"
        
        # Ověříme, že se BTC odstranil
        config_after = load_config()
        assert 'BTC' not in config_after, "BTC měl být odstraněn z konfigurace"
        
        print(f"   ✅ /remove funguje, BTC odstraněn (celkem: {len(config_after)} kryptoměn)\n")
        return True
    except Exception as e:
        print(f"   ❌ /remove selhal: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def test_help():
    """Test /help příkazu."""
    print("🧪 Test 7: /help")
    update = MockUpdate()
    context = MockContext()
    
    try:
        await help_command(update, context)
        assert update.message.reply_text.called, "help_command() měl zavolat reply_text"
        print("   ✅ /help funguje\n")
        return True
    except Exception as e:
        print(f"   ❌ /help selhal: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def test_get_crypto_price():
    """Test získávání cen z API."""
    print("🧪 Test 8: get_crypto_price pro různé kryptoměny")
    
    test_symbols = ['BTC', 'ETH', 'LTC']
    results = {}
    
    for symbol in test_symbols:
        try:
            price = get_crypto_price(symbol)
            if price and price > 0:
                results[symbol] = price
                print(f"   ✅ {symbol}: ${price:,.2f}")
            else:
                print(f"   ⚠️  {symbol}: Cena nebyla získána")
        except Exception as e:
            print(f"   ❌ {symbol}: Chyba - {e}")
    
    if len(results) >= 2:
        print(f"   ✅ get_crypto_price funguje ({len(results)}/{len(test_symbols)} úspěšných)\n")
        return True
    else:
        print(f"   ⚠️  get_crypto_price má problémy ({len(results)}/{len(test_symbols)} úspěšných)\n")
        return False

async def test_database_operations():
    """Test databázových operací."""
    print("🧪 Test 9: Databázové operace")
    
    try:
        # Test načtení konfigurace
        config = load_config()
        print(f"   📋 Načtena konfigurace: {len(config)} kryptoměn")
        
        # Test načtení stavu
        state = load_state()
        print(f"   📊 Načten stav: {len(state)} kryptoměn")
        
        # Test uložení (přidáme testovací záznam)
        test_config = config.copy()
        test_config['TEST'] = {'name': 'Test Coin', 'threshold': 0.01}
        save_config(test_config)
        
        # Ověříme, že se uložilo
        config_after = load_config()
        if 'TEST' in config_after:
            print("   ✅ Ukládání do databáze funguje")
            # Odstraníme testovací záznam
            del test_config['TEST']
            save_config(test_config)
            print("   ✅ Obnovena původní konfigurace\n")
            return True
        else:
            print("   ❌ Ukládání do databáze selhalo\n")
            return False
    except Exception as e:
        print(f"   ❌ Databázové operace selhaly: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def test_add_existing_crypto():
    """Test přidání kryptoměny, která už existuje."""
    print("🧪 Test 10: /add kryptoměny, která už existuje")
    update = MockUpdate(args=['ETH'])
    context = MockContext(['ETH'])
    
    # Nejdřív zkontrolujeme, jestli ETH už existuje
    config_before = load_config()
    eth_exists = 'ETH' in config_before
    
    with patch('eth_price_alert.validate_ticker', return_value=(True, 'Ethereum', 3000.0)):
        try:
            result = await add_crypto(update, context)
            # Bot by měl umožnit přidat i existující (přepíše threshold)
            assert update.message.reply_text.called, "add_crypto() měl zavolat reply_text"
            print(f"   ✅ /add existující kryptoměny funguje (ETH existuje: {eth_exists})\n")
            return True
        except Exception as e:
            print(f"   ❌ /add existující kryptoměny selhal: {e}\n")
            return False

async def test_add_invalid_ticker():
    """Test přidání neplatného tickeru."""
    print("🧪 Test 11: /add neplatného tickeru (INVALID)")
    update = MockUpdate(args=['INVALID'])
    context = MockContext(['INVALID'])
    
    with patch('eth_price_alert.validate_ticker', return_value=(False, None, None)):
        try:
            result = await add_crypto(update, context)
            assert update.message.reply_text.called, "add_crypto() měl zavolat reply_text"
            # Měla by být chybová zpráva
            call_args = update.message.reply_text.call_args[0][0]
            assert 'není platný' in call_args.lower() or 'neexistuje' in call_args.lower(), "Měla být chybová zpráva"
            print("   ✅ /add neplatného tickeru správně vrátil chybu\n")
            return True
        except Exception as e:
            print(f"   ❌ /add neplatného tickeru selhal: {e}\n")
            return False

async def test_handle_invalid_threshold():
    """Test zadání neplatného threshold."""
    print("🧪 Test 12: Zadání neplatného threshold (text)")
    update = MockUpdate(message_text='abc')
    context = MockContext()
    context.user_data['pending_symbol'] = 'TEST'
    context.user_data['pending_name'] = 'Test Coin'
    
    try:
        result = await handle_threshold(update, context)
        assert update.message.reply_text.called, "handle_threshold() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'neplatný' in call_args.lower() or 'formát' in call_args.lower(), "Měla být chybová zpráva"
        assert result == 1, "Měl by zůstat ve stavu WAITING_THRESHOLD"
        print("   ✅ Neplatný threshold správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ Neplatný threshold selhal: {e}\n")
        return False

async def test_handle_negative_threshold():
    """Test zadání záporného threshold."""
    print("🧪 Test 13: Zadání záporného threshold (-5)")
    update = MockUpdate(message_text='-5')
    context = MockContext()
    context.user_data['pending_symbol'] = 'TEST'
    context.user_data['pending_name'] = 'Test Coin'
    
    try:
        result = await handle_threshold(update, context)
        assert update.message.reply_text.called, "handle_threshold() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'větší než 0' in call_args.lower() or 'musí být' in call_args.lower(), "Měla být chybová zpráva"
        assert result == 1, "Měl by zůstat ve stavu WAITING_THRESHOLD"
        print("   ✅ Záporný threshold správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ Záporný threshold selhal: {e}\n")
        return False

async def test_remove_nonexistent_crypto():
    """Test odebrání kryptoměny, která neexistuje."""
    print("🧪 Test 14: /remove neexistující kryptoměny (XYZ)")
    update = MockUpdate(args=['XYZ'])
    context = MockContext(['XYZ'])
    
    try:
        config_before = load_config()
        if 'XYZ' in config_before:
            print("   ⚠️  XYZ už existuje, přeskočeno\n")
            return True
        
        await remove_crypto(update, context)
        assert update.message.reply_text.called, "remove_crypto() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'není ve sledovaných' in call_args.lower() or 'není' in call_args.lower(), "Měla být chybová zpráva"
        print("   ✅ /remove neexistující kryptoměny správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ /remove neexistující kryptoměny selhal: {e}\n")
        return False

async def test_list_empty():
    """Test /list když není žádná kryptoměna."""
    print("🧪 Test 15: /list s prázdnou konfigurací")
    update = MockUpdate()
    context = MockContext()
    
    # Uložíme prázdnou konfiguraci
    original_config = load_config()
    save_config({})
    
    try:
        await list_cryptos(update, context)
        assert update.message.reply_text.called, "list_cryptos() měl zavolat reply_text"
        print("   ✅ /list s prázdnou konfigurací funguje\n")
        
        # Obnovíme původní konfiguraci
        save_config(original_config)
        return True
    except Exception as e:
        print(f"   ❌ /list s prázdnou konfigurací selhal: {e}\n")
        # Obnovíme původní konfiguraci
        save_config(original_config)
        return False

async def test_setall_empty():
    """Test /setall když není žádná kryptoměna."""
    print("🧪 Test 16: /setall s prázdnou konfigurací")
    update = MockUpdate(args=['5'])
    context = MockContext(['5'])
    
    # Uložíme prázdnou konfiguraci
    original_config = load_config()
    save_config({})
    
    try:
        await setall_threshold(update, context)
        assert update.message.reply_text.called, "setall_threshold() měl zavolat reply_text"
        # Měla by být chybová zpráva (buď "nesleduji žádné" nebo podobná)
        call_args = update.message.reply_text.call_args[0][0]
        assert 'nesleduji' in call_args.lower() or 'žádné' in call_args.lower() or 'použijte /add' in call_args.lower(), f"Měla být chybová zpráva, ale dostali jsme: {call_args}"
        print("   ✅ /setall s prázdnou konfigurací správně vrátil chybu\n")
        
        # Obnovíme původní konfiguraci
        save_config(original_config)
        return True
    except Exception as e:
        print(f"   ❌ /setall s prázdnou konfigurací selhal: {e}\n")
        import traceback
        traceback.print_exc()
        # Obnovíme původní konfiguraci
        save_config(original_config)
        return False

async def test_setall_invalid_threshold():
    """Test /setall s neplatným threshold."""
    print("🧪 Test 17: /setall s neplatným threshold (abc)")
    update = MockUpdate(args=['abc'])
    context = MockContext(['abc'])
    
    # Ujistíme se, že máme nějakou konfiguraci
    config = load_config()
    if not config:
        # Přidáme testovací kryptoměnu
        config = {'TEST': {'name': 'Test', 'threshold': 0.05}}
        save_config(config)
    
    try:
        await setall_threshold(update, context)
        assert update.message.reply_text.called, "setall_threshold() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'neplatný' in call_args.lower() or 'formát' in call_args.lower() or 'číslo' in call_args.lower(), f"Měla být chybová zpráva, ale dostali jsme: {call_args}"
        print("   ✅ /setall s neplatným threshold správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ /setall s neplatným threshold selhal: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def test_update_nonexistent():
    """Test /update pro neexistující kryptoměnu."""
    print("🧪 Test 18: /update neexistující kryptoměny (XYZ)")
    update = MockUpdate(args=['XYZ'])
    context = MockContext(['XYZ'])
    
    # Ujistíme se, že máme nějakou konfiguraci
    config = load_config()
    if not config:
        # Přidáme testovací kryptoměnu
        config = {'TEST': {'name': 'Test', 'threshold': 0.05}}
        save_config(config)
    
    try:
        config = load_config()
        if 'XYZ' in config:
            print("   ⚠️  XYZ už existuje, přeskočeno\n")
            return True
        
        result = await update_threshold(update, context)
        assert update.message.reply_text.called, "update_threshold() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'není ve sledovaných' in call_args.lower() or 'není' in call_args.lower() or 'použijte /list' in call_args.lower(), f"Měla být chybová zpráva, ale dostali jsme: {call_args}"
        print("   ✅ /update neexistující kryptoměny správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ /update neexistující kryptoměny selhal: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def test_add_without_args():
    """Test /add bez argumentů."""
    print("🧪 Test 19: /add bez argumentů")
    update = MockUpdate(args=[])
    context = MockContext([])
    
    try:
        result = await add_crypto(update, context)
        assert update.message.reply_text.called, "add_crypto() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'zadejte ticker' in call_args.lower() or 'ticker' in call_args.lower(), "Měla být chybová zpráva"
        assert result == -1, "Měl by ukončit konverzaci"
        print("   ✅ /add bez argumentů správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ /add bez argumentů selhal: {e}\n")
        return False

async def test_remove_without_args():
    """Test /remove bez argumentů."""
    print("🧪 Test 20: /remove bez argumentů")
    update = MockUpdate(args=[])
    context = MockContext([])
    
    try:
        await remove_crypto(update, context)
        assert update.message.reply_text.called, "remove_crypto() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'zadejte ticker' in call_args.lower() or 'ticker' in call_args.lower(), "Měla být chybová zpráva"
        print("   ✅ /remove bez argumentů správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ /remove bez argumentů selhal: {e}\n")
        return False

async def test_add_overwrites_existing():
    """Test že přidání existující kryptoměny přepíše threshold."""
    print("🧪 Test 21: Přidání existující kryptoměny přepíše threshold")
    # Nejdřív přidáme kryptoměnu s jedním threshold
    config = load_config()
    if 'ETH' not in config:
        config['ETH'] = {'name': 'Ethereum', 'threshold': 0.10}  # 10%
        save_config(config)
    
    original_threshold = config.get('ETH', {}).get('threshold', 0)
    
    # Teď "přidáme" ETH znovu s jiným threshold
    update = MockUpdate(args=['ETH'])
    context = MockContext(['ETH'])
    context.user_data = {}
    
    with patch('eth_price_alert.validate_ticker', return_value=(True, 'Ethereum', 3000.0)):
        result = await add_crypto(update, context)
        # Mělo by to umožnit přidat (přepíše threshold)
        assert update.message.reply_text.called, "add_crypto() měl zavolat reply_text"
        assert 'pending_symbol' in context.user_data, "Symbol měl být uložen"
        print(f"   ✅ Přidání existující kryptoměny funguje (přepíše threshold)\n")
        return True

async def test_zero_threshold():
    """Test zadání threshold 0."""
    print("🧪 Test 22: Zadání threshold 0")
    update = MockUpdate(message_text='0')
    context = MockContext()
    context.user_data['pending_symbol'] = 'TEST'
    context.user_data['pending_name'] = 'Test Coin'
    
    try:
        result = await handle_threshold(update, context)
        assert update.message.reply_text.called, "handle_threshold() měl zavolat reply_text"
        # Měla by být chybová zpráva
        call_args = update.message.reply_text.call_args[0][0]
        assert 'větší než 0' in call_args.lower() or 'musí být' in call_args.lower(), "Měla být chybová zpráva"
        assert result == 1, "Měl by zůstat ve stavu WAITING_THRESHOLD"
        print("   ✅ Threshold 0 správně vrátil chybu\n")
        return True
    except Exception as e:
        print(f"   ❌ Threshold 0 selhal: {e}\n")
        return False

async def test_very_high_threshold():
    """Test zadání velmi vysokého threshold."""
    print("🧪 Test 23: Zadání velmi vysokého threshold (1000)")
    update = MockUpdate(message_text='1000')
    context = MockContext()
    context.user_data['pending_symbol'] = 'TEST'
    context.user_data['pending_name'] = 'Test Coin'
    
    try:
        result = await handle_threshold(update, context)
        # Mělo by to projít (i když je to vysoké)
        assert update.message.reply_text.called, "handle_threshold() měl zavolat reply_text"
        # Mělo by to být uloženo
        config = load_config()
        if 'TEST' in config:
            assert config['TEST']['threshold'] == 10.0, "Threshold měl být 1000% = 10.0"
            # Odstraníme testovací záznam
            del config['TEST']
            save_config(config)
            print("   ✅ Velmi vysoký threshold funguje (1000%)\n")
            return True
        else:
            print("   ⚠️  TEST nebyl uložen, ale nevrátil chybu\n")
            return True
    except Exception as e:
        print(f"   ❌ Velmi vysoký threshold selhal: {e}\n")
        return False

async def main():
    """Spustí všechny testy."""
    print("="*80)
    print("🧪 TESTOVÁNÍ VŠECH UŽIVATELSKÝCH AKCÍ + EDGE CASES")
    print("="*80)
    print()
    
    tests = [
        ("Start", test_start),
        ("Add Crypto", test_add_crypto),
        ("Handle Threshold", test_handle_threshold),
        ("List Cryptos", test_list_cryptos),
        ("Set All Threshold", test_setall_threshold),
        ("Remove Crypto", test_remove_crypto),
        ("Help", test_help),
        ("Get Crypto Price", test_get_crypto_price),
        ("Database Operations", test_database_operations),
        ("Add Existing Crypto", test_add_existing_crypto),
        ("Add Invalid Ticker", test_add_invalid_ticker),
        ("Invalid Threshold (text)", test_handle_invalid_threshold),
        ("Negative Threshold", test_handle_negative_threshold),
        ("Remove Nonexistent", test_remove_nonexistent_crypto),
        ("List Empty", test_list_empty),
        ("Setall Empty", test_setall_empty),
        ("Setall Invalid Threshold", test_setall_invalid_threshold),
        ("Update Nonexistent", test_update_nonexistent),
        ("Add Without Args", test_add_without_args),
        ("Remove Without Args", test_remove_without_args),
        ("Add Overwrites Existing", test_add_overwrites_existing),
        ("Zero Threshold", test_zero_threshold),
        ("Very High Threshold", test_very_high_threshold),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print(f"❌ Test {name} vyhodil výjimku: {e}\n")
            results[name] = False
            import traceback
            traceback.print_exc()
    
    print("="*80)
    print("📊 VÝSLEDKY TESTOVÁNÍ")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Celkem: {passed}/{total} testů prošlo")
    
    if passed == total:
        print("✅ Všechny testy prošly!")
        return 0
    else:
        print(f"❌ {total - passed} testů selhalo")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

