#!/usr/bin/env python3
"""
Automatické nasazení na Railway pomocí GraphQL API
"""
import requests
import json
import os
import time

# Konfigurace
RAILWAY_API_TOKEN = os.getenv('RAILWAY_API_TOKEN', 'aeaca3c9-ebca-4534-9a3a-50cad796cc7d')
TELEGRAM_BOT_TOKEN = '8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8'
TELEGRAM_CHAT_ID = '351517996'

RAILWAY_GRAPHQL_URL = 'https://backboard.railway.app/graphql/v1'

def get_headers():
    return {
        'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
        'Content-Type': 'application/json'
    }

def graphql_query(query, variables=None):
    """Provede GraphQL dotaz"""
    payload = {'query': query}
    if variables:
        payload['variables'] = variables
    
    response = requests.post(RAILWAY_GRAPHQL_URL, headers=get_headers(), json=payload)
    response.raise_for_status()
    return response.json()

def get_user_id():
    """Získá ID uživatele"""
    print("👤 Získávám informace o uživateli...")
    query = """
    query {
        me {
            id
            name
            email
        }
    }
    """
    result = graphql_query(query)
    if 'errors' in result:
        print(f"❌ Chyba: {result['errors']}")
        return None
    user = result['data']['me']
    print(f"✅ Přihlášen jako: {user.get('name', 'N/A')} ({user.get('email', 'N/A')})")
    return user['id']

def create_project():
    """Vytvoří nový projekt"""
    print("📦 Vytvářím nový projekt...")
    query = """
    mutation($name: String!) {
        projectCreate(name: $name) {
            id
            name
        }
    }
    """
    variables = {
        'name': f'eth-price-alert-{int(time.time())}'
    }
    
    result = graphql_query(query, variables)
    if 'errors' in result:
        print(f"❌ Chyba: {result['errors']}")
        return None
    
    project = result['data']['projectCreate']
    print(f"✅ Projekt vytvořen: {project['name']} (ID: {project['id']})")
    return project

def create_service(project_id):
    """Vytvoří službu v projektu"""
    print("🔧 Vytvářím službu...")
    query = """
    mutation($projectId: String!, $name: String!) {
        serviceCreate(projectId: $projectId, name: $name) {
            id
            name
        }
    }
    """
    variables = {
        'projectId': project_id,
        'name': 'eth-price-alert'
    }
    
    result = graphql_query(query, variables)
    if 'errors' in result:
        print(f"❌ Chyba: {result['errors']}")
        return None
    
    service = result['data']['serviceCreate']
    print(f"✅ Služba vytvořena: {service['name']} (ID: {service['id']})")
    return service

def set_variables(project_id, service_id):
    """Nastaví environment variables"""
    print("🔐 Nastavuji environment variables...")
    
    variables = [
        {'name': 'TELEGRAM_BOT_TOKEN', 'value': TELEGRAM_BOT_TOKEN},
        {'name': 'TELEGRAM_CHAT_ID', 'value': TELEGRAM_CHAT_ID}
    ]
    
    for var in variables:
        query = """
        mutation($projectId: String!, $serviceId: String!, $name: String!, $value: String!) {
            variableUpsert(projectId: $projectId, serviceId: $serviceId, name: $name, value: $value) {
                id
            }
        }
        """
        variables_gql = {
            'projectId': project_id,
            'serviceId': service_id,
            'name': var['name'],
            'value': var['value']
        }
        
        result = graphql_query(query, variables_gql)
        if 'errors' in result:
            print(f"⚠️  Varování: Nepodařilo se nastavit {var['name']}: {result['errors']}")
        else:
            print(f"✅ Nastaveno: {var['name']}")

def main():
    if not RAILWAY_API_TOKEN:
        print("❌ Chyba: Railway API token není nastaven")
        return
    
    try:
        # Ověření tokenu
        user_id = get_user_id()
        if not user_id:
            print("❌ Nepodařilo se ověřit token")
            return
        
        # Vytvoření projektu
        project = create_project()
        if not project:
            return
        
        # Vytvoření služby
        service = create_service(project['id'])
        if not service:
            return
        
        # Nastavení proměnných
        set_variables(project['id'], service['id'])
        
        print("\n✅ Hotovo! Projekt je vytvořen na Railway")
        print(f"📊 Zkontrolujte na: https://railway.app/project/{project['id']}")
        print(f"\n📝 Projekt ID: {project['id']}")
        print(f"📝 Služba ID: {service['id']}")
        print("\n💡 Další kroky:")
        print("   1. Nahrajte kód přes GitHub nebo Railway CLI")
        print("   2. Nebo použijte: railway link --project " + project['id'])
        print("   3. Pak: railway up")
        
    except requests.RequestException as e:
        print(f"❌ Chyba při komunikaci s Railway API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"   Detaily: {e.response.text}")
            except:
                pass
    except Exception as e:
        print(f"❌ Neočekávaná chyba: {e}")

if __name__ == '__main__':
    main()

