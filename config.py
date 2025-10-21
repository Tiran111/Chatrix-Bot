import os

def get_required_env(var_name, default=None):
    """Безпечне отримання змінних середовища"""
    value = os.environ.get(var_name, default)
    if value is None:
        raise ValueError(f"❌ {var_name} не встановлено в змінних середовища")
    return value

def get_admin_id():
    """Безпечне отримання ADMIN_ID"""
    try:
        admin_id = int(os.environ.get('ADMIN_ID', 0))
        if admin_id == 0:
            raise ValueError("❌ ADMIN_ID не встановлено в змінних середовища")
        return admin_id
    except ValueError:
        raise ValueError("❌ ADMIN_ID має бути числовим значенням")

def get_bot_token():
    """Безпечне отримання токена бота"""
    token = os.environ.get('BOT_TOKEN')
    if not token or token == 'your_bot_token_here':
        raise ValueError("❌ BOT_TOKEN не встановлено або використовується тестовий токен")
    return token

# Глобальні змінні будуть встановлені пізніше
TOKEN = None
ADMIN_ID = None

def initialize_config():
    """Ініціалізація конфігурації (викликається після імпорту)"""
    global TOKEN, ADMIN_ID
    TOKEN = get_bot_token()
    ADMIN_ID = get_admin_id()
    print(f"✅ Конфігурація ініціалізована: TOKEN={TOKEN[:10]}..., ADMIN_ID={ADMIN_ID}")

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

# Автоматична ініціалізація при імпорті
try:
    initialize_config()
except Exception as e:
    print(f"⚠️ Помилка ініціалізації конфігурації: {e}")