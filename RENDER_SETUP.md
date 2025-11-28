# 🚀 Rychlý návod: Nastavení persistentního úložiště na Render.com

## Problém
Při každém redeploy (push do GitHubu) se na Render.com smažou všechna data uživatelů (sledované kryptoměny, thresholdy).

## Řešení: PostgreSQL databáze

### Krok 1: Vytvořte PostgreSQL databázi na Render

1. Jděte na [Render Dashboard](https://dashboard.render.com)
2. Klikněte na **"New +"** → **"PostgreSQL"**
3. Vyplňte:
   - **Name**: `crypto-price-alert-db` (nebo jakýkoliv název)
   - **Database**: `cryptodb`
   - **User**: `cryptouser`
   - **Region**: **Stejná jako váš service** (důležité!)
   - **Plan**: Free (pro začátek)
4. Klikněte na **"Create Database"**
5. Počkejte 1-2 minuty, až se databáze vytvoří

### Krok 2: Zkopírujte Internal Database URL

1. Jděte na vaši databázi (v seznamu služeb)
2. V sekci **"Connections"** najděte **"Internal Database URL"**
3. Klikněte na **"Copy"** a zkopírujte URL
   - Vypadá nějak takto: `postgresql://cryptouser:password@dpg-xxxxx-a/cryptodb`
   - ⚠️ **Důležité:** Použijte **Internal** URL, ne External!

### Krok 3: Přidejte DATABASE_URL do vašeho service

1. Jděte na váš **Web Service** (crypto price alert bot)
2. Klikněte na záložku **"Environment"**
3. Klikněte na **"Add Environment Variable"**
4. Přidejte:
   - **Key**: `DATABASE_URL`
   - **Value**: Vložte zkopírovanou Internal Database URL
5. Klikněte na **"Save Changes"**
6. Render automaticky restartuje service

### Krok 4: Ověření

1. Jděte na **"Logs"** vašeho service
2. Měli byste vidět:
   ```
   ✅ Databáze připravena - data budou persistentní a přežijí redeploy
   ```
3. Pokud vidíte varování, zkontrolujte, jestli je `DATABASE_URL` správně nastavený

## ✅ Hotovo!

Nyní se všechna data ukládají do databáze a **přežijí každý redeploy**.

### Co se ukládá do databáze:
- ✅ Sledované kryptoměny (přidáno přes `/add`)
- ✅ Thresholdy pro každou kryptoměnu
- ✅ Poslední ceny a časy notifikací

### Co se stane při redeploy:
- ✅ Data zůstanou v databázi
- ✅ Aplikace se automaticky připojí k databázi
- ✅ Všechna nastavení uživatelů zůstanou zachována

## 🔍 Troubleshooting

**Problém:** V logách vidím "⚠️ Varování: DATABASE_URL není nastaveno"
- **Řešení:** Zkontrolujte, jestli jste přidali environment variable `DATABASE_URL`

**Problém:** "❌ Chyba při připojení k databázi"
- **Řešení:** 
  - Zkontrolujte, jestli používáte **Internal Database URL** (ne External)
  - Zkontrolujte, jestli je databáze spuštěná (na Render dashboardu)
  - Zkontrolujte, jestli je databáze ve **stejné region** jako váš service

**Problém:** Data se stále mažou při redeploy
- **Řešení:** Ujistěte se, že v logách vidíte "✅ Databáze připravena". Pokud ne, databáze není správně nastavená.

## 📚 Více informací

Podrobnější návod najdete v [DATABASE_SETUP.md](DATABASE_SETUP.md)




