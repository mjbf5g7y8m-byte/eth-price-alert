# 🚀 Rychlé nasazení na Railway - Manuální postup

Pokud máte účet na Railway, můžete nasadit aplikaci za 2 minuty:

## Možnost 1: Railway CLI (Nejrychlejší)

1. **Nainstalujte Railway CLI:**
   ```bash
   curl -fsSL https://railway.app/install.sh | sh
   ```

2. **Spusťte deploy skript:**
   ```bash
   cd /tmp/eth_price_alert
   ./deploy_railway.sh
   ```

   Skript automaticky:
   - Přihlásí vás do Railway
   - Vytvoří nový projekt
   - Nastaví environment variables
   - Nasadí aplikaci

## Možnost 2: Webové rozhraní (Bez CLI)

1. **Vytvořte GitHub repo:**
   ```bash
   cd /tmp/eth_price_alert
   git init
   git add .
   git commit -m "Initial commit"
   # Nahrajte na GitHub (přes web nebo git push)
   ```

2. **V Railway:**
   - Jděte na [railway.app](https://railway.app)
   - Klikněte "New Project"
   - Vyberte "Deploy from GitHub repo"
   - Vyberte váš repo
   - Railway automaticky detekuje Python a začne build

3. **Nastavte Variables:**
   - V projektu klikněte na službu
   - Jděte do "Variables"
   - Přidejte:
     - `TELEGRAM_BOT_TOKEN` = `8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8`
     - `TELEGRAM_CHAT_ID` = `351517996`

4. **Hotovo!** Aplikace se automaticky redeploy s novými proměnnými

## Možnost 3: Railway API Token (Pro automatizaci)

Pokud chcete, abych to nasadil za vás, potřebuji:

1. **Railway API Token:**
   - Jděte na [railway.app/account](https://railway.app/account)
   - V sekci "API" vytvořte nový token
   - Pošlete mi token

2. Nebo **GitHub repo URL** kam můžu pushnout kód

Pošlete mi buď Railway token nebo GitHub repo URL a já to nasadím za vás!

