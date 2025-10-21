from telegram import ReplyKeyboardMarkup
try:
    from database_postgres import db
except ImportError:
    from database.models import db
from config import ADMIN_ID

def get_main_menu(user_id):
    """Генерація головного меню"""
    try:
        user_id_int = int(user_id)
    except:
        user_id_int = user_id
    
    user_data, is_complete = db.get_user_profile(user_id)
    
    # Перевіряємо чи це адмін
    is_admin = (user_id_int == ADMIN_ID)
    
    if is_admin:
        # Меню для адміністратора
        keyboard = [
            ['💕 Пошук анкет', '🏙️ По місту'],
            ['👤 Мій профіль', '📝 Редагувати'],
            ['❤️ Хто мене лайкнув', '👀 Хто переглядав'],
            ['💌 Мої матчі', '🏆 Топ'],
            ["👨‍💼 Зв'язок з адміном"],
            ['👑 Адмін панель']
        ]
    elif not is_complete:
        # Якщо профіль не заповнений
        keyboard = [['📝 Заповнити профіль']]
    else:
        # Якщо профіль заповнений
        keyboard = [
            ['💕 Пошук анкет', '🏙️ По місту'],
            ['👤 Мій профіль', '📝 Редагувати'],
            ['❤️ Хто мене лайкнув', '👀 Хто переглядав'],
            ['💌 Мої матчі', '🏆 Топ'],
            ["👨‍💼 Зв'язок з адміном"]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    """Клавіатура скасування"""
    keyboard = [['🔙 Скасувати']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)