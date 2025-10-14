import os

# Токен бота з змінної середовища
TOKEN = os.environ.get('TELEGRAM_TOKEN', 'your_bot_token_here')

# ID адміністратора
ADMIN_ID = int(os.environ.get('ADMIN_ID', 123456789))

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