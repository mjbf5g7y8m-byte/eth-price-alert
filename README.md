# ETH Price Alert Bot

Aplikace, která sleduje cenu Ethereum (ETH) a posílá upozornění na Telegram při změně ceny o 10% od posledního upozornění.

## Funkce

- ✅ Sleduje cenu ETH v reálném čase
- ✅ Posílá upozornění na Telegram při změně o 10% (nahoru nebo dolů)
- ✅ Ukládá poslední cenu upozornění (nezávisle na čase)
- ✅ Kontroluje cenu každou minutu

## Instalace

1. **Nainstalujte Python závislosti:**
```bash
pip install -r requirements.txt
```

2. **Vytvořte Telegram bota:**
   - Otevřete Telegram a najděte [@BotFather](https://t.me/BotFather)
   - Pošlete příkaz `/newbot` a postupujte podle instrukcí
   - Zkopírujte token, který vám BotFather poskytne

3. **Získejte Chat ID nebo Username:**
   - **Možnost 1 (Username):** Použijte vaše Telegram username (např. `honzuvbot` nebo `@honzuvbot`)
   - **Možnost 2 (Chat ID):** Najděte [@userinfobot](https://t.me/userinfobot) na Telegramu, pošlete mu zprávu a zkopírujte vaše Chat ID (číslo)

4. **Nastavte proměnné prostředí:**
```bash
export TELEGRAM_BOT_TOKEN='váš_bot_token'
export TELEGRAM_CHAT_ID='honzuvbot'  # nebo číselné ID, nebo @honzuvbot
```

**Poznámka:** Pokud použijete username bez `@`, aplikace ho automaticky přidá.

## Spuštění

```bash
python eth_price_alert.py
```

Aplikace poběží kontinuálně a bude kontrolovat cenu ETH každou minutu. Při změně o 10% od posledního upozornění vám pošle zprávu na Telegram.

## Ukončení

Stiskněte `Ctrl+C` pro ukončení aplikace.

## Jak to funguje

1. Aplikace načte poslední cenu, při které bylo odesláno upozornění (z `eth_price_state.json`)
2. Pokud je to první spuštění, uloží aktuální cenu jako referenční
3. Každou minutu kontroluje aktuální cenu ETH
4. Pokud se cena změní o 10% nebo více od posledního upozornění, pošle upozornění na Telegram
5. Po odeslání upozornění aktualizuje referenční cenu

**Důležité:** Aplikace sleduje změnu od posledního upozornění, ne od určitého časového bodu. Pokud cena klesne o 5% a pak stoupne o 5%, žádné upozornění se nepošle (celková změna je 0%). Ale pokud klesne o 10%, pošle se upozornění a nová referenční cena bude ta nižší.

## Nasazení do cloudu

Chcete, aby aplikace běžela 24/7 v cloudu? Podívejte se na **[DEPLOY.md](DEPLOY.md)** pro kompletní návod.

**Rychlý start s Railway (doporučeno):**
1. Vytvořte účet na [Railway.app](https://railway.app)
2. Vytvořte nový projekt a připojte GitHub repo
3. Nastavte environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Deploy se spustí automaticky!

## Poznámky

- Aplikace používá bezplatné CoinGecko API (bez API klíče)
- Pro produkční použití doporučuji přidat rate limiting a error handling
- Soubor `eth_price_state.json` se vytvoří automaticky při prvním spuštění

