# 🤖 Telegram Keyword Bot — Setup Guide

## What it does
- Admin adds keywords + replies via commands
- User types a keyword in the group → bot automatically replies
- Keywords saved in MongoDB → **survive VPS restarts and server changes**

---

## 📁 File Structure
```
telegram_keyword_bot/
├── bot.py             # Main bot logic
├── database.py        # MongoDB handler
├── requirements.txt   # Python packages
├── .env.example       # Environment variables template
└── telegram-bot.service  # Systemd service (auto-restart on VPS)
```

---

## 🚀 VPS Setup (Step by Step)

### 1. Upload files to VPS
```bash
scp -r telegram_keyword_bot/ root@YOUR_VPS_IP:/root/
```

### 2. SSH into your VPS
```bash
ssh root@YOUR_VPS_IP
cd /root/telegram_keyword_bot
```

### 3. Install Python & MongoDB
```bash
apt update && apt install -y python3 python3-venv python3-pip

# Install MongoDB
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list
apt update && apt install -y mongodb-org
systemctl start mongod && systemctl enable mongod
```

### 4. Setup Python environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Configure environment
```bash
cp .env.example .env
nano .env
# Fill in: BOT_TOKEN, ADMIN_IDS, MONGO_URI
```

### 6. Test the bot
```bash
source venv/bin/activate
python bot.py
# Press Ctrl+C when confirmed working
```

### 7. Install as systemd service (auto-restart)
```bash
cp telegram-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable telegram-bot
systemctl start telegram-bot

# Check status
systemctl status telegram-bot

# View logs
journalctl -u telegram-bot -f
```

---

## ⚙️ Admin Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/addkeyword keyword \| reply` | Add a keyword | `/addkeyword daredevil born again \| Daredevil: Born Again (2025-)` |
| `/listkeywords` | Show all keywords | `/listkeywords` |
| `/deletekeyword keyword` | Remove a keyword | `/deletekeyword daredevil born again` |

---

## 🎨 Customizing the Reply Format

In `/addkeyword`, the reply text supports:
- `{name}` → replaced with the user's first name
- `{keyword}` → replaced with what they typed
- HTML tags: `<b>bold</b>`, `<i>italic</i>`, `<code>code</code>`

**Example:**
```
/addkeyword daredevil | 👋 හෙලෝ {name},\n\nඔයා හෙයාන <b>Daredevil: Born Again</b> මෙතන තියනවා!
```

---

## 🗄️ MongoDB Data

Keywords are saved in collection `keywords` in database `telegram_bot`:
```json
{
  "keyword": "daredevil born again",
  "reply": "Daredevil: Born Again (2025-)",
  "buttons": []
}
```

Data **persists forever** — VPS restarts, reinstalls, server changes won't lose keywords as long as MongoDB is running or you use MongoDB Atlas.

---

## ☁️ Using MongoDB Atlas (Recommended for reliability)

1. Go to [mongodb.com/atlas](https://mongodb.com/atlas) → Free tier
2. Create cluster → Get connection string
3. In `.env` set: `MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/`

---

## 🔧 Useful Commands

```bash
# Restart bot
systemctl restart telegram-bot

# Stop bot
systemctl stop telegram-bot

# Live logs
journalctl -u telegram-bot -f

# Check MongoDB
mongosh --eval "use telegram_bot; db.keywords.find()"
```
