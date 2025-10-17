import os
import logging

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Змінні середовища
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bot_database.db')

# Налаштування бота
BOT_USERNAME = None
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.environ.get('PORT', 5000))

# Налаштування профілю
MIN_AGE = 18
MAX_AGE = 100
GENDERS = ['Чоловік', 'Жінка']
SEEKING_GENDERS = ['Чоловіків', 'Жінок', 'Всіх']
GOALS = ['Серйозні стосунки', 'Дружба', 'Сповіщення', 'Флірт']

# Налаштування пошуку
SEARCH_LIMIT = 100
DAILY_LIKES_LIMIT = 50

# Налаштування адміністрації
ADMIN_COMMANDS = [
    '/stats - Статистика бота',
    '/users - Список користувачів', 
    '/broadcast - Розсилка повідомлень',
    '/ban - Заблокувати користувача',
    '/unban - Розблокувати користувача'
]

def initialize_config():
    """Ініціалізація конфігурації"""
    global BOT_USERNAME
    
    if not TOKEN or TOKEN == 'your_bot_token_here':
        raise ValueError("❌ BOT_TOKEN не встановлено або встановлено тестове значення")
    
    if ADMIN_ID == 0:
        raise ValueError("❌ ADMIN_ID не встановлено")
    
    # Спрощена ініціалізація - без отримання інформації про бота
    # Це буде зроблено пізніше в асинхронному контексті
    BOT_USERNAME = "chatrix_bot"  # Тимчасове значення
    
    logger.info("✅ Конфігурація успішно ініціалізована")
    logger.info(f"🔧 ADMIN_ID: {ADMIN_ID}")
    logger.info(f"🔧 DATABASE_URL: {DATABASE_URL}")
    logger.info(f"🔧 WEBHOOK_URL: {WEBHOOK_URL}")

async def initialize_bot_info(application):
    """Асинхронна ініціалізація інформації про бота"""
    global BOT_USERNAME
    try:
        bot_info = await application.bot.get_me()
        BOT_USERNAME = bot_info.username
        logger.info(f"✅ Бот @{BOT_USERNAME} успішно ініціалізовано")
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бота: {e}")
        BOT_USERNAME = "chatrix_bot"

def validate_environment():
    """Перевірка змінних середовища"""
    required_vars = ['BOT_TOKEN', 'ADMIN_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"❌ Відсутні обов'язкові змінні середовища: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not TOKEN or TOKEN == 'your_bot_token_here':
        error_msg = "❌ Ви використовуєте тестовий токен. Встановіть реальний токен бота."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        admin_id = int(os.environ.get('ADMIN_ID', 0))
        if admin_id == 0:
            raise ValueError("ADMIN_ID не встановлено")
    except ValueError:
        raise ValueError("❌ ADMIN_ID має бути числовим значенням")
    
    logger.info("✅ Змінні середовища перевірені успішно")

# Функції для роботи з конфігурацією
def get_bot_username():
    """Отримати username бота"""
    return BOT_USERNAME

def get_admin_id():
    """Отримати ID адміністратора"""
    return ADMIN_ID

def get_webhook_url():
    """Отримати URL вебхука"""
    return WEBHOOK_URL

def get_database_url():
    """Отримати URL бази даних"""
    return DATABASE_URL

# Перевірка конфігурації при імпорті
try:
    validate_environment()
except Exception as e:
    logger.warning(f"⚠️ Попередження конфігурації: {e}")