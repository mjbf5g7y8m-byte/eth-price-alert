# Instrukce pro Update Botu

## 🎯 Co tento update dělá

1. **Nastaví COW, SAFE a RAIL jako crypto** pro všechny existující uživatele
2. **Pošle zprávu všem uživatelům** o nových funkcích
3. **Aktualizuje databázi** s novými typy assetů

## 🚀 Jak spustit update v produkci

### Na Render.com (nebo jiném hosting):

1. **Připojte se k serveru přes SSH** (nebo použijte web shell)

2. **Nastavte environment variables**:
   ```bash
   export TELEGRAM_BOT_TOKEN="váš_token"
   export DATABASE_URL="váš_database_url"
   ```

3. **Spusťte update script**:
   ```bash
   python3 update_crypto_types.py
   ```

### Nebo použijte jednorázový příkaz:

```bash
TELEGRAM_BOT_TOKEN="xxx" DATABASE_URL="xxx" python3 update_crypto_types.py
```

## 📋 Co script udělá

### 1. Aktualizuje typy tickerů
```
✅ [chat_id] COW: stock → crypto
✅ [chat_id] SAFE: neznámý → crypto
✅ [chat_id] RAIL: stock → crypto
```

### 2. Pošle zprávu všem uživatelům
```
🔄 Aktualizace botu

✨ Co je nového:

1️⃣ Výběr typu assetu
   Při přidávání tickeru si nyní vyberete, zda jde o:
   🪙 Kryptoměnu
   📈 Akcii

2️⃣ Vylepšené načítání cen
   Přidány nové spolehlivé API zdroje:
   • Coinbase
   • Kraken
   • Vylepšený Binance

3️⃣ Automatická migrace
   Vaše existující tickery byly automaticky kategorizovány
```

## 🔍 Kontrola před spuštěním

Script nejdřív zkusí databázi, pokud není dostupná, použije lokální soubor.

**Výstup bude vypadat takto:**
```
🚀 Spouštím aktualizaci...
🎯 Tickery k aktualizaci: COW, SAFE, RAIL

🗄️  Používám databázi

=== Aktualizace typů ===
✅ [12345678] COW: stock → crypto
✅ [87654321] SAFE: neznámý → crypto

✅ Aktualizováno 2 tickerů pro 2 uživatelů
💾 Změny uloženy do databáze

=== Posílání zpráv 2 uživatelům ===
✅ Zpráva odeslána: 12345678
✅ Zpráva odeslána: 87654321

📊 Statistika odesílání:
   ✅ Úspěšně: 2
   ❌ Chyba: 0

✅ Hotovo!
```

## ⚠️ Poznámky

- Script je **idempotentní** - lze spustit vícekrát bez problémů
- Pokud ticker COW/SAFE/RAIL neexistuje u uživatele, prostě se přeskočí
- Zpráva se pošle **všem** uživatelům v databázi, ne jen těm s COW/SAFE/RAIL
- Script automaticky detekuje, jestli použít databázi nebo lokální soubor

## 🧪 Testování lokálně

Pro test lokálně (bez posílání zpráv):
```bash
python3 update_crypto_types.py
```

Output:
```
⚠️  TELEGRAM_BOT_TOKEN není nastaveno, přeskakuji posílání zpráv
```

## 📝 Po spuštění

Po úspěšném spuštění:
1. ✅ Všichni uživatelé dostanou notifikaci
2. ✅ COW, SAFE, RAIL budou nastaveny jako crypto
3. ✅ Nové přidávání tickerů bude používat výběr typu

**Restartovat bot není nutné** - změny se načtou automaticky!

