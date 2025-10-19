from telegram import ReplyKeyboardMarkup
try:
    from database_postgres import db
except ImportError:
    from database.models import db
from config import ADMIN_ID

def get_main_menu(user_id):
    """Генерація головного меню"""
    user_data, is_complete = db.get_user_profile(user_id)
    
    if user_id == ADMIN_ID:
        # Меню для адміністратора
        keyboard = [
            ['💕 Пошук анкет', '🏙️ По місту'],
            ['👤 Мій профіль', '❤️ Хто мене лайкнув'],
            ['💌 Мої матчі', '🏆 Топ'],
            ["👨‍💼 Зв'язок з адміном", '👑 Адмін панель']
        ]
    elif not is_complete:
        # Якщо профіль не заповнений
        keyboard = [['📝 Заповнити профіль']]
    else:
        # Якщо профіль заповнений
        keyboard = [
            ['💕 Пошук анкет', '🏙️ По місту'],
            ['👤 Мій профіль', '❤️ Хто мене лайкнув'],
            ['💌 Мої матчі', '🏆 Топ'],
            ["👨‍💼 Зв'язок з адміном"]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu():
    """Меню адміністратора"""
    keyboard = [
        ['📊 Статистика', '👥 Користувачі'],
        ['📢 Розсилка', '🔄 Оновити базу'],
        ['🚫 Блокування', '📈 Детальна статистика'],
        ['🔙 Головне меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_search_navigation():
    """Навігація пошуку"""
    keyboard = [
        ['❤️ Лайк', '➡️ Далі'],
        ['🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    """Клавіатура скасування"""
    keyboard = [['🔙 Скасувати']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)