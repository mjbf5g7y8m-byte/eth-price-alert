#!/bin/bash

# Railway Deployment Script
# Automaticky nasadí ETH Price Alert Bot na Railway

set -e

echo "🚂 Railway Deployment Script"
echo "=============================="
echo ""

# Kontrola Railway CLI
if ! command -v railway &> /dev/null; then
    echo "📦 Instaluji Railway CLI..."
    curl -fsSL https://railway.app/install.sh | sh
    echo "✅ Railway CLI nainstalován"
    echo ""
fi

# Kontrola, jestli jsme v správném adresáři
if [ ! -f "eth_price_alert.py" ]; then
    echo "❌ Chyba: Spusťte skript z adresáře s eth_price_alert.py"
    exit 1
fi

echo "🔐 Přihlášení do Railway..."
echo "💡 Pokud nejste přihlášeni, otevře se prohlížeč pro přihlášení"
railway login

echo ""
echo "📦 Vytvářím nový projekt na Railway..."
PROJECT_NAME="eth-price-alert-$(date +%s)"
railway init --name "$PROJECT_NAME"

echo ""
echo "🔧 Nastavuji environment variables..."
railway variables set TELEGRAM_BOT_TOKEN=8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8
railway variables set TELEGRAM_CHAT_ID=351517996

echo ""
echo "🚀 Nasazuji aplikaci..."
railway up

echo ""
echo "✅ Hotovo! Aplikace je nasazena na Railway"
echo "📊 Zkontrolujte status na: https://railway.app"
echo ""
echo "💡 Pro zobrazení logů: railway logs"
echo "💡 Pro restart: railway restart"

