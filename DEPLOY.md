# Nasazení ETH Price Alert Bot do cloudu

Tento návod ukazuje, jak nasadit aplikaci do cloudu, aby běžela 24/7.

## Možnosti nasazení

### 1. 🚀 Render (Doporučeno - Nejjednodušší)

**Výhody:**
- ✅ Zdarma (free tier)
- ✅ Velmi jednoduché nasazení
- ✅ Automatické restartování při chybě
- ✅ Webové rozhraní

**Postup:**

1. **Vytvořte účet na [Render.com](https://render.com)**

2. **Vytvořte nový Web Service:**
   - Klikněte na "New +" → "Web Service"
   - Připojte váš GitHub repo (nebo použijte tento adresář)
   - Nebo použijte "Public Git repository" a zadejte URL

3. **Nastavení:**
   - **Name:** `eth-price-alert` (nebo jakékoliv jméno)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python eth_price_alert.py`

4. **Nastavte Environment Variables:**
   - `TELEGRAM_BOT_TOKEN` = `8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8`
   - `TELEGRAM_CHAT_ID` = `351517996`

5. **Klikněte na "Create Web Service"**

6. **Poznámka:** Render free tier má limit - služba se "uspí" po 15 minutách nečinnosti. Pro nepřetržitý provoz použijte **Background Worker** místo Web Service (ale to vyžaduje placený plán).

---

### 2. 🚂 Railway (Doporučeno - Free tier s kredity)

**Výhody:**
- ✅ $5 zdarma kreditů měsíčně
- ✅ Jednoduché nasazení
- ✅ Nepřetržitý provoz

**Postup:**

1. **Vytvořte účet na [Railway.app](https://railway.app)**

2. **Vytvořte nový projekt:**
   - Klikněte na "New Project"
   - Vyberte "Deploy from GitHub repo" nebo "Empty Project"

3. **Pokud používáte Empty Project:**
   - Klikněte na "+ New" → "GitHub Repo"
   - Nebo použijte "Empty Project" a nahrajte soubory

4. **Nastavení:**
   - Railway automaticky detekuje Python
   - Vytvořte soubor `Procfile` (viz níže)

5. **Nastavte Environment Variables:**
   - V sekci "Variables" přidejte:
     - `TELEGRAM_BOT_TOKEN` = `8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8`
     - `TELEGRAM_CHAT_ID` = `351517996`

6. **Deploy se spustí automaticky**

---

### 3. ☁️ PythonAnywhere (Free tier)

**Výhody:**
- ✅ Zdarma (free tier)
- ✅ Jednoduché pro Python aplikace
- ⚠️ Omezení: aplikace se zastaví po 3 měsících nečinnosti

**Postup:**

1. **Vytvořte účet na [PythonAnywhere.com](https://www.pythonanywhere.com)**

2. **Nahrajte soubory:**
   - V "Files" sekci nahrajte všechny soubory z projektu

3. **Vytvořte Scheduled Task:**
   - Jděte do "Tasks" → "Always-on task"
   - Zadejte: `python3.9 /home/vaše_username/eth_price_alert.py`
   - Nebo použijte "Schedule" pro periodické spouštění

4. **Nastavte Environment Variables:**
   - V "Files" → "env" nebo přímo v kódu (ne ideální)

---

### 4. 🐳 Docker + VPS (Nejvíce kontroly)

**Výhody:**
- ✅ Plná kontrola
- ✅ Nepřetržitý provoz
- ⚠️ Vyžaduje placený VPS (cca $5-10/měsíc)

**Doporučené VPS poskytovatelé:**
- DigitalOcean ($6/měsíc)
- Linode ($5/měsíc)
- Vultr ($6/měsíc)
- Hetzner (€4/měsíc)

**Postup:**

1. **Vytvořte VPS** u některého poskytovatele

2. **Připojte se přes SSH:**
   ```bash
   ssh root@vaše_ip
   ```

3. **Nainstalujte Python a závislosti:**
   ```bash
   apt update
   apt install python3 python3-pip git -y
   ```

4. **Nahrajte soubory:**
   ```bash
   git clone váš_repo
   # nebo použijte scp
   ```

5. **Nastavte systemd service** (viz níže)

---

## Pomocné soubory pro nasazení

### Procfile (pro Railway/Heroku)
```
worker: python eth_price_alert.py
```

### Dockerfile (volitelné)
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eth_price_alert.py .

CMD ["python", "eth_price_alert.py"]
```

### systemd service (pro VPS)
Vytvořte soubor `/etc/systemd/system/eth-price-alert.service`:

```ini
[Unit]
Description=ETH Price Alert Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/eth_price_alert
Environment="TELEGRAM_BOT_TOKEN=8340628343:AAE3-khZ5GtvaLp96O3n4_D3qyamhnU8rB8"
Environment="TELEGRAM_CHAT_ID=351517996"
ExecStart=/usr/bin/python3 /root/eth_price_alert/eth_price_alert.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Pak spusťte:
```bash
systemctl daemon-reload
systemctl enable eth-price-alert
systemctl start eth-price-alert
systemctl status eth-price-alert
```

---

## Doporučení

**Pro začátek:** Použijte **Railway** - je to nejjednodušší a má free tier s kredity, které stačí pro tuto aplikaci.

**Pro dlouhodobý provoz:** Pokud potřebujete 100% uptime, použijte **VPS** s systemd service.

---

## Bezpečnostní poznámka

⚠️ **Důležité:** V produkčním prostředí NIKDY neukládejte citlivé údaje (bot token, chat ID) přímo do kódu. Vždy používejte environment variables!

