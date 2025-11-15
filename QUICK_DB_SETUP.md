# ⚡ Rychlé vytvoření databáze na Render.com (3 minuty)

## Krok 1: Vytvořte databázi
👉 **Otevřete:** https://dashboard.render.com/web/new/postgres

Nebo:
1. Jděte na https://dashboard.render.com
2. Klikněte **"New +"** → **"PostgreSQL"**

## Krok 2: Vyplňte údaje
- **Name**: `crypto-price-alert-db`
- **Database**: `cryptodb`  
- **User**: `cryptouser`
- **Region**: **STEJNÁ jako váš Web Service** ⚠️ (důležité!)
- **Plan**: Free
- Klikněte **"Create Database"**

## Krok 3: Zkopírujte URL
1. Počkejte 1-2 minuty, až se databáze vytvoří
2. Jděte na databázi (v seznamu služeb)
3. V sekci **"Connections"** → **"Internal Database URL"**
4. Klikněte **"Copy"** a zkopírujte URL

## Krok 4: Přidejte do service
1. Jděte na váš **Web Service** (bot)
2. **"Environment"** → **"Add Environment Variable"**
3. **Key**: `DATABASE_URL`
4. **Value**: Vložte zkopírovanou URL
5. **"Save Changes"**

## ✅ Hotovo!
Render restartuje service a v logách uvidíte:
```
✅ Databáze připravena - data budou persistentní a přežijí redeploy
```

---

**Pomocný skript:** Spusťte `./create_render_db.sh` pro interaktivní průvodce

