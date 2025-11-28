# 📢 Jak poslat zprávu o updatu všem uživatelům

## ✅ Jednoduchý způsob (DOPORUČENO)

Po deployi nové verze na server (Railway/Render):

1. **Otevřete Telegram**
2. **Napište botovi příkaz:**
   ```
   /broadcast
   ```

To je vše! 🎉

Bot automaticky:
- ✅ Nastaví COW, SAFE, RAIL jako crypto (při načtení konfigurace)
- ✅ Pošle zprávu o updatu všem uživatelům

## 📋 Co se stane

### 1. Automatická migrace (děje se automaticky při načtení)
```
🔄 Migrace: COW nastaven jako crypto (vynuceno)
🔄 Migrace: SAFE nastaven jako crypto (vynuceno)
🔄 Migrace: RAIL nastaven jako crypto (vynuceno)
```

### 2. Broadcast zpráva
```
📤 Posílám zprávu o updatu všem uživatelům...

✅ Zpráva odeslána!

📊 Statistika:
✅ Úspěšně: 5
❌ Chyba: 0
```

### 3. Všichni uživatelé dostanou:
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

📝 Jak to funguje:
Příkaz: /add BTC
Bot se zeptá: Je to kryptoměna nebo akcie?
Vyberete typ → Bot ověří cenu → Nastavíte alert

🎯 Výhody:
• Rychlejší načítání cen
• Přesnější detekce
• Žádné záměny mezi akciemi a kryptoměnami

Zkuste to: /add [TICKER]
```

## 🔒 Bezpečnost

- Příkaz `/broadcast` funguje **pouze pro admina**
- Admin chat_id se nastavuje přes `TELEGRAM_CHAT_ID` env var
- Ostatní uživatelé dostanou: "❌ Tento příkaz je pouze pro admina."

## 🔄 Automatická migrace

**Migrace COW, SAFE, RAIL probíhá automaticky:**
- Při každém načtení konfigurace (při startu bota, při přidání tickeru, atd.)
- Nemusíte dělat nic extra
- Pokud už někdo má COW jako "stock", automaticky se změní na "crypto"

## 🚀 Kompletní postup po deployi

```bash
# 1. Push změny na GitHub (už hotovo ✅)
git push origin main

# 2. Počkejte na auto-deploy (Railway/Render)
#    Nebo manuálně: railway up / render deploy

# 3. Otevřete Telegram a napište botovi:
/broadcast

# 4. ✅ Hotovo!
```

## 🧪 Testování

Můžete otestovat lokálně (bez posílání zpráv):
```bash
python3 eth_price_alert.py
# V jiném terminálu si pošlete zprávu přes Telegram
```

## 💡 Tip

Pokud chcete poslat zprávu jen sobě (test):
1. Odkomentujte řádek s `ADMIN_CHAT_ID` kontrolou
2. Pošlete `/broadcast`
3. Zpráva přijde jen vám

## ❓ FAQ

**Q: Musím spustit update_crypto_types.py?**
A: Ne! Použijte `/broadcast` - je to jednodušší.

**Q: Co když někdo přidá COW nově?**
A: Při přidávání si vybere typ, takže to není problém.

**Q: Migrace se spustí opakovaně?**
A: Ano, ale je to idempotentní - pokud už je nastaveno správně, nic se nezmění.

**Q: Mohu poslat vlastní zprávu?**
A: Ano, upravte text v `broadcast_update()` funkci před deployem.

