# 📱 Telegram příkazy - Interaktivní nastavení

Aplikace nyní podporuje interaktivní nastavení přes Telegram!

## 🚀 Jak používat:

### 1. Přidání kryptoměny ke sledování

**Příkaz:** `/add BTC`

1. Napište: `/add BTC` (nebo jakýkoliv ticker)
2. Bot odpoví:
   ```
   ✅ Bitcoin (BTC) je platný ticker!
   💰 Aktuální cena: $94,290.19
   📊 Zadejte threshold v procentech (např. 0.1 pro 0.1%, nebo 5 pro 5%):
   ```
3. Zadejte threshold (např. `0.1` pro 0.1% nebo `5` pro 5%)
4. Bot potvrdí:
   ```
   ✅ Bitcoin (BTC) přidáno ke sledování!
   📊 Threshold: 0.1%
   💰 Aktuální cena: $94,290.19
   Bot bude posílat upozornění při změně o nastavené procento.
   ```

### 2. Zobrazení sledovaných kryptoměn

**Příkaz:** `/list`

Zobrazí seznam všech sledovaných kryptoměn s jejich thresholdy a posledními cenami.

### 3. Odebrání kryptoměny

**Příkaz:** `/remove BTC`

Odebere kryptoměnu ze sledování.

### 4. Nápověda

**Příkaz:** `/help`

Zobrazí nápovědu s dostupnými příkazy.

### 5. Start

**Příkaz:** `/start`

Zobrazí úvodní zprávu s instrukcemi.

---

## 📋 Příklady:

```
/add SOL
→ Bot: ✅ Solana (SOL) je platný ticker!
→ Bot: 💰 Aktuální cena: $XXX.XX
→ Bot: 📊 Zadejte threshold v procentech...
→ Vy: 0.5
→ Bot: ✅ Solana (SOL) přidáno ke sledování!
```

```
/add DOGE
→ Bot: ✅ Dogecoin (DOGE) je platný ticker!
→ Bot: 💰 Aktuální cena: $0.XX
→ Bot: 📊 Zadejte threshold v procentech...
→ Vy: 10
→ Bot: ✅ Dogecoin (DOGE) přidáno ke sledování! (threshold: 10%)
```

---

## ✅ Výchozí kryptoměny:

Pokud nic nenastavíte, aplikace automaticky sleduje:
- ETH, BTC, AAVE, ZEC, ICP, COW, GNO (s thresholdem 0.1%)

Můžete je odebrat pomocí `/remove` a přidat vlastní.

---

## 💡 Tipy:

- Ticker můžete zadat malými nebo velkými písmeny (BTC = btc)
- Threshold můžete zadat jako desetinné číslo (0.1) nebo celé číslo (5)
- Můžete sledovat libovolný počet kryptoměn
- Každá kryptoměna může mít jiný threshold

