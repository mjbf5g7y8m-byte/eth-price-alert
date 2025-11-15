#!/bin/bash
# Jednoduchý skript pro kontrolu stavu na Render.com

echo "🔍 Kontrola stavu deploymentu na Render.com"
echo ""
echo "Pro získání logů potřebujete:"
echo "1. Render API Key: https://dashboard.render.com/account/api-keys"
echo "2. Service ID (najdete v URL vašeho service)"
echo ""
echo "Pak můžete použít:"
echo "  export RENDER_API_KEY='váš_klíč'"
echo "  export RENDER_SERVICE_ID='váš_service_id'"
echo "  python3 fetch_render_logs.py"
echo ""
echo "Nebo zkontrolujte logy přímo na:"
echo "  https://dashboard.render.com → Váš service → Logs"
