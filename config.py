import os

# Токен бота з змінної середовища
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не встановлено в змінних середовища")

# ID адміністратора
try:
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
    if ADMIN_ID == 0:
        raise ValueError("❌ ADMIN_ID не встановлено в змінних середовища")
except ValueError:
    raise ValueError("❌ ADMIN_ID має бути числовим значенням")

# Налаштування бази даних
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bot_database.db')

# Налаштування для Render
RENDER = True
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"

# Налаштування keep-alive
KEEP_ALIVE_INTERVAL = 300  # 5 хвилин

# Ліміти
MAX_PROFILE_LENGTH = 500
MAX_BIO_LENGTH = 1000
SEARCH_LIMIT = 50