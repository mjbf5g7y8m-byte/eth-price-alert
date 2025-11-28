#!/usr/bin/env python3
"""
Skript pro stahování logů z Render.com pomocí Render API.
"""
import os
import requests
import json
from datetime import datetime, timedelta

RENDER_API_KEY = os.getenv('RENDER_API_KEY')
RENDER_SERVICE_ID = os.getenv('RENDER_SERVICE_ID')  # ID vašeho service na Render

def get_render_logs(service_id=None, limit=100):
    """Získá logy z Render.com pomocí API."""
    if not RENDER_API_KEY:
        print("❌ RENDER_API_KEY není nastaveno")
        print("   Získejte API klíč na: https://dashboard.render.com/account/api-keys")
        return None
    
    if not service_id:
        service_id = RENDER_SERVICE_ID
    
    if not service_id:
        print("❌ RENDER_SERVICE_ID není nastaveno")
        print("   Najděte Service ID v URL vašeho service na Render dashboardu")
        print("   Nebo použijte: python fetch_render_logs.py --service-id YOUR_SERVICE_ID")
        return None
    
    headers = {
        'Authorization': f'Bearer {RENDER_API_KEY}',
        'Accept': 'application/json'
    }
    
    # Zkusíme získat logy přes Render API
    # Poznámka: Render API může mít různé endpointy pro logy
    base_url = 'https://api.render.com'
    
    # Zkusíme různé endpointy
    endpoints = [
        f'/v1/services/{service_id}/logs',
        f'/v1/services/{service_id}/events',
        f'/v1/services/{service_id}/deploys',
    ]
    
    for endpoint in endpoints:
        try:
            url = f'{base_url}{endpoint}'
            print(f"🔍 Zkouším: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Úspěšně získány data z {endpoint}")
                return data
            elif response.status_code == 404:
                print(f"⚠️  Endpoint {endpoint} neexistuje")
                continue
            else:
                print(f"⚠️  Status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Chyba při volání {endpoint}: {e}")
            continue
    
    # Pokud API nefunguje, zkusíme získat seznam services
    try:
        print("\n🔍 Zkouším získat seznam services...")
        url = f'{base_url}/v1/services'
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            services = response.json()
            print(f"✅ Nalezeno {len(services)} services")
            for service in services[:5]:  # Zobrazíme prvních 5
                print(f"   - {service.get('name', 'N/A')} (ID: {service.get('id', 'N/A')})")
            return services
    except Exception as e:
        print(f"❌ Chyba při získávání services: {e}")
    
    return None

def parse_logs(logs_data):
    """Parsuje logy a zobrazí relevantní chyby."""
    if not logs_data:
        return
    
    print("\n" + "="*80)
    print("📋 ANALÝZA LOGŮ")
    print("="*80 + "\n")
    
    # Zkusíme najít error logy
    errors = []
    warnings = []
    
    if isinstance(logs_data, list):
        for log_entry in logs_data:
            log_str = str(log_entry).lower()
            if 'error' in log_str or '❌' in str(log_entry):
                errors.append(log_entry)
            elif 'warning' in log_str or '⚠️' in str(log_entry):
                warnings.append(log_entry)
    elif isinstance(logs_data, dict):
        # Procházíme různé možné struktury
        for key, value in logs_data.items():
            if 'log' in key.lower() or 'message' in key.lower():
                if isinstance(value, list):
                    for entry in value:
                        if 'error' in str(entry).lower() or '❌' in str(entry):
                            errors.append(entry)
    
    if errors:
        print(f"❌ Nalezeno {len(errors)} chyb:")
        for error in errors[-10:]:  # Posledních 10 chyb
            print(f"   {error}")
    else:
        print("✅ Žádné chyby nenalezeny")
    
    if warnings:
        print(f"\n⚠️  Nalezeno {len(warnings)} varování:")
        for warning in warnings[-5:]:  # Posledních 5 varování
            print(f"   {warning}")

if __name__ == '__main__':
    import sys
    
    service_id = None
    if len(sys.argv) > 1:
        if '--service-id' in sys.argv:
            idx = sys.argv.index('--service-id')
            if idx + 1 < len(sys.argv):
                service_id = sys.argv[idx + 1]
        elif sys.argv[1].startswith('--'):
            print("Použití: python fetch_render_logs.py [--service-id SERVICE_ID]")
            sys.exit(1)
        else:
            service_id = sys.argv[1]
    
    print("🚀 Stahování logů z Render.com...\n")
    logs = get_render_logs(service_id)
    
    if logs:
        parse_logs(logs)
        
        # Uložíme do souboru
        output_file = f'render_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump(logs, f, indent=2, default=str)
        print(f"\n💾 Logy uloženy do: {output_file}")
    else:
        print("\n❌ Nepodařilo se získat logy")
        print("\n💡 Alternativní řešení:")
        print("   1. Zkontrolujte logy přímo na Render dashboardu")
        print("   2. Získejte API klíč na: https://dashboard.render.com/account/api-keys")
        print("   3. Najděte Service ID v URL vašeho service na Render dashboardu")




