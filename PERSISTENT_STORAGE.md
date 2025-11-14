# 💾 Persistentní úložiště dat

## Problém:
Při redeploy na Render se smažou soubory `crypto_config.json` a `crypto_price_state.json`, protože filesystem se resetuje.

## Řešení:
Aplikace nyní podporuje ukládání dat do **Environment Variables** na Render, které jsou persistentní a přežijí redeploy.

## Jak to nastavit:

### 1. Po prvním nastavení kryptoměn přes Telegram:

1. Jděte na Render Dashboard → Váš service
2. Klikněte na "Environment" tab
3. Zkontrolujte Render logs - uvidíte hodnoty pro `CRYPTO_CONFIG` a `CRYPTO_STATE`
4. Přidejte tyto environment variables:

   **CRYPTO_CONFIG** - obsahuje konfiguraci kryptoměn a thresholdů
   ```
   {"BTC":{"name":"Bitcoin","threshold":0.001},"ETH":{"name":"Ethereum","threshold":0.001}}
   ```

   **CRYPTO_STATE** - obsahuje stav (poslední ceny a časy)
   ```
   {"BTC":{"last_notification_price":null,"last_notification_time":null},"ETH":{"last_notification_price":null,"last_notification_time":null}}
   ```

### 2. Automatické získání hodnot:

Po přidání kryptoměny přes `/add`:
- Zkontrolujte Render logs
- Uvidíte výstup typu:
  ```
  💡 Pro persistentní uložení v cloudu nastavte environment variable CRYPTO_CONFIG na Render:
     {"BTC":{"name":"Bitcoin","threshold":0.001},"LTC":{"name":"Litecoin","threshold":0.001}}
  ```

### 3. Zkopírujte hodnoty:

1. Zkontrolujte Render logs
2. Najděte řádky s `💡 Pro persistentní uložení v cloudu...`
3. Zkopírujte JSON hodnoty
4. Vložte je do Render Environment Variables

### 4. Po nastavení:

- Data budou persistentní a přežijí redeploy
- Při každém přidání/změně kryptoměny si zkontrolujte logs a aktualizujte environment variables

---

## Alternativní řešení (pokud chcete automatizaci):

Můžeme přidat automatické ukládání do externího storage (např. GitHub Gist, nebo databáze), ale to vyžaduje další setup.

---

## 💡 Tip:

Pokud zapomenete nastavit environment variables, data se uloží do souborů, ale při redeploy se smažou. Environment variables jsou jediný způsob, jak zajistit persistentní uložení na Render.

