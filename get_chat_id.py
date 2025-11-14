#!/usr/bin/env python3
"""
Skript pro získání vašeho chat ID.
Pošlete jakoukoliv zprávu botovi a pak spusťte tento skript.
"""
import requests
import time

BOT_TOKEN = '8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8'

print("📱 Získávám poslední zprávy od bota...")
print("💡 Tip: Pošlete botovi zprávu '/start' nebo jakoukoliv jinou zprávu\n")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

try:
    # Zkusíme získat updates s timeoutem
    params = {'timeout': 1}
    response = requests.get(url, params=params, timeout=15)
    data = response.json()
    
    print(f"📊 Celkem updates: {len(data.get('result', []))}")
    
    if data.get('ok') and data.get('result'):
        updates = data['result']
        if updates:
            print(f"\n✅ Nalezeno {len(updates)} update(s):\n")
            # Zobrazíme všechny updates
            for i, update in enumerate(updates, 1):
                if 'message' in update:
                    chat = update['message']['chat']
                    chat_id = chat.get('id')
                    username = chat.get('username', 'N/A')
                    first_name = chat.get('first_name', 'N/A')
                    text = update['message'].get('text', 'N/A')
                    
                    print(f"Update #{i}:")
                    print(f"  📋 Chat ID: {chat_id}")
                    print(f"  👤 Username: @{username}" if username != 'N/A' else f"  👤 Jméno: {first_name}")
                    print(f"  💬 Text: {text}")
                    print()
            
            # Získáme poslední update
            last_update = updates[-1]
            if 'message' in last_update:
                chat = last_update['message']['chat']
                chat_id = chat.get('id')
                username = chat.get('username', 'N/A')
                first_name = chat.get('first_name', 'N/A')
                
                print(f"✅ Použijte toto chat ID z poslední zprávy:")
                print(f"export TELEGRAM_CHAT_ID='{chat_id}'")
        else:
            print("❌ Žádné zprávy nenalezeny.")
            print("\n💡 Postup:")
            print("1. Najděte bota @Honzuvbot na Telegramu")
            print("2. Pošlete mu zprávu '/start' nebo jakoukoliv jinou zprávu")
            print("3. Počkejte pár vteřin a spusťte tento skript znovu")
    else:
        print(f"❌ Chyba: {data}")
        
except Exception as e:
    print(f"❌ Chyba: {e}")

