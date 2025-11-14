#!/usr/bin/env python3
"""
Automatické nasazení na Railway pomocí API
"""
import requests
import json
import os
import time

# Konfigurace
RAILWAY_API_TOKEN = os.getenv('RAILWAY_API_TOKEN')
TELEGRAM_BOT_TOKEN = '8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8'
TELEGRAM_CHAT_ID = '351517996'

RAILWAY_API_URL = 'https://api.railway.app/v1'

def get_headers():
    return {
        'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
        'Content-Type': 'application/json'
    }

def create_project():
    """Vytvoří nový projekt na Railway"""
    print("📦 Vytvářím nový projekt...")
    url = f"{RAILWAY_API_URL}/projects"
    payload = {
        'name': f'eth-price-alert-{int(time.time())}'
    }
    
    response = requests.post(url, headers=get_headers(), json=payload)
    response.raise_for_status()
    project = response.json()
    print(f"✅ Projekt vytvořen: {project['name']} (ID: {project['id']})")
    return project

def create_service(project_id):
    """Vytvoří novou službu v projektu"""
    print("🔧 Vytvářím službu...")
    url = f"{RAILWAY_API_URL}/projects/{project_id}/services"
    payload = {
        'name': 'eth-price-alert'
    }
    
    response = requests.post(url, headers=get_headers(), json=payload)
    response.raise_for_status()
    service = response.json()
    print(f"✅ Služba vytvořena: {service['name']} (ID: {service['id']})")
    return service

def set_variables(project_id, service_id):
    """Nastaví environment variables"""
    print("🔐 Nastavuji environment variables...")
    url = f"{RAILWAY_API_URL}/projects/{project_id}/services/{service_id}/variables"
    
    variables = {
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    
    for key, value in variables.items():
        payload = {
            'name': key,
            'value': value
        }
        response = requests.post(url, headers=get_headers(), json=payload)
        if response.status_code not in [200, 201]:
            print(f"⚠️  Varování: Nepodařilo se nastavit {key}: {response.text}")
        else:
            print(f"✅ Nastaveno: {key}")

def main():
    if not RAILWAY_API_TOKEN:
        print("❌ Chyba: Nastavte RAILWAY_API_TOKEN")
        print("\nJak získat token:")
        print("1. Jděte na https://railway.app/account")
        print("2. V sekci 'API' vytvořte nový token")
        print("3. Spusťte: export RAILWAY_API_TOKEN='váš_token'")
        print("4. Pak spusťte tento skript znovu")
        return
    
    try:
        project = create_project()
        service = create_service(project['id'])
        set_variables(project['id'], service['id'])
        
        print("\n✅ Hotovo! Projekt je vytvořen na Railway")
        print(f"📊 Zkontrolujte na: https://railway.app/project/{project['id']}")
        print("\n💡 Poznámka: Musíte ještě nahrát kód (přes GitHub nebo Railway CLI)")
        print("   Nebo použijte: railway link --project " + project['id'])
        print("   Pak: railway up")
        
    except requests.RequestException as e:
        print(f"❌ Chyba při komunikaci s Railway API: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Detaily: {e.response.text}")

if __name__ == '__main__':
    main()

