# 🗄️ Nastavení databáze pro persistentní úložiště

## Proč databáze?
Data se nyní ukládají automaticky do PostgreSQL databáze, která je persistentní a přežije redeploy. Nemusíte řešit environment variables!

## Jak nastavit:

### 1. Vytvořte PostgreSQL databázi na Render:

1. Jděte na Render Dashboard
2. Klikněte na "New +" → "PostgreSQL"
3. Vyplňte:
   - **Name**: `crypto-price-alert-db` (nebo jakýkoliv název)
   - **Database**: `cryptodb` (nebo jakýkoliv název)
   - **User**: `cryptouser` (nebo jakýkoliv název)
   - **Region**: Vyberte stejnou region jako váš service
   - **Plan**: Free (pro začátek)
4. Klikněte na "Create Database"
5. Počkejte, až se databáze vytvoří (1-2 minuty)

### 2. Zkopírujte Internal Database URL:

1. Jděte na vaši databázi na Render
2. V sekci "Connections" najdete "Internal Database URL"
3. Zkopírujte URL (vypadá nějak takto):
   ```
   postgresql://cryptouser:password@dpg-xxxxx-a/cryptodb
   ```

### 3. Přidejte DATABASE_URL do vašeho service:

1. Jděte na váš service (crypto price alert bot)
2. Klikněte na "Environment" tab
3. Klikněte na "Add Environment Variable"
4. Přidejte:
   - **Key**: `DATABASE_URL`
   - **Value**: Vložte zkopírovanou Internal Database URL
5. Klikněte na "Save Changes"
6. Restartujte service (Render to udělá automaticky)

### 4. Hotovo! 🎉

- Data se nyní ukládají automaticky do databáze
- Přežijí redeploy
- Nemusíte řešit environment variables

---

## Co se stane po nastavení:

1. **Při prvním spuštění** se automaticky vytvoří tabulky v databázi (aplikace to udělá sama)
2. **Při přidání kryptoměny** přes `/add` se data uloží do databáze
3. **Při změně threshold** přes `/update` se data aktualizují v databázi
4. **Data přežijí redeploy** - při každém push do GitHubu a redeploy na Render se data zachovají
5. **Při restartu** service se data načtou z databáze

---

## Fallback:

Pokud `DATABASE_URL` není nastavený, aplikace použije souborové úložiště (pro lokální vývoj). Ale v cloudu doporučujeme použít databázi.

---

## 💡 Tip:

Pokud máte problém s připojením k databázi, zkontrolujte:
- Jestli je `DATABASE_URL` správně nastavený
- Jestli je databáze spuštěná (na Render dashboardu)
- Jestli používáte **Internal Database URL** (ne External)
- V Render logs uvidíte zprávu "✅ Databáze připravena" pokud je vše v pořádku
- Pokud vidíte "⚠️ Varování: DATABASE_URL není nastaveno", přidejte environment variable

## ⚠️ Důležité:

**Bez databáze se data při každém redeploy smažou!** 

Pokud nemáte nastavenou `DATABASE_URL`, aplikace sice funguje, ale:
- Data se ukládají do souborů `crypto_config.json` a `crypto_price_state.json`
- Při redeploy na Render.com se tyto soubory smažou
- Všechna nastavení uživatelů (sledované kryptoměny, thresholdy) se ztratí

**Řešení:** Nastavte PostgreSQL databázi podle návodu výše.

