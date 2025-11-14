# 🚂 Rychlý start: Nasazení na Railway

Railway je nejjednodušší způsob, jak spustit aplikaci v cloudu. Má $5 zdarma kreditů měsíčně, což stačí pro tuto aplikaci.

## Krok 1: Vytvořte účet

1. Jděte na [railway.app](https://railway.app)
2. Klikněte na "Start a New Project"
3. Přihlaste se pomocí GitHub (nejjednodušší)

## Krok 2: Vytvořte GitHub repo (pokud ještě nemáte)

1. Vytvořte nový repo na GitHubu
2. Nahrajte všechny soubory z `/tmp/eth_price_alert/`:
   ```bash
   cd /tmp/eth_price_alert
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/vaše_username/eth-price-alert.git
   git push -u origin main
   ```

## Krok 3: Nasazení na Railway

1. V Railway dashboardu klikněte na "New Project"
2. Vyberte "Deploy from GitHub repo"
3. Vyberte váš repo `eth-price-alert`
4. Railway automaticky detekuje Python a začne build

## Krok 4: Nastavte Environment Variables

1. V Railway projektu klikněte na vaši službu
2. Jděte do sekce "Variables"
3. Přidejte dvě proměnné:
   - **Key:** `TELEGRAM_BOT_TOKEN`
     **Value:** `8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8`
   
   - **Key:** `TELEGRAM_CHAT_ID`
     **Value:** `351517996`

4. Railway automaticky restartuje aplikaci s novými proměnnými

## Krok 5: Ověření

1. Počkejte, až se deploy dokončí (zelená ikona)
2. Klikněte na "View Logs" a zkontrolujte, že aplikace běží
3. Měli byste vidět: `🚀 ETH Price Alert Bot spuštěn`

## Hotovo! 🎉

Aplikace nyní běží 24/7 v cloudu a bude vám posílat upozornění na Telegram při změně ceny ETH o 10%.

## Monitorování

- **Logy:** Klikněte na "View Logs" v Railway dashboardu
- **Status:** Zelená ikona = běží, červená = chyba
- **Restart:** Klikněte na "Restart" pokud potřebujete aplikaci restartovat

## Náklady

- **Free tier:** $5 kreditů měsíčně
- **Tato aplikace:** Spotřebuje cca $0.50-1/měsíc (záleží na využití CPU)
- **Zůstává zdarma!** ✅

## Poznámky

- Railway automaticky restartuje aplikaci při chybě
- Pokud potřebujete aktualizovat kód, pushněte změny na GitHub a Railway automaticky redeploy
- Environment variables můžete změnit kdykoliv v Railway dashboardu

