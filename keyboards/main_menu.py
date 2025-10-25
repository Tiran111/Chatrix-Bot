from telegram import ReplyKeyboardMarkup
from config import ADMIN_ID

def get_main_menu(user_id=None):
    """Головне меню без кнопки '👀 Хто переглядав'"""
    if user_id and user_id == ADMIN_ID:
        keyboard = [
            ['💕 Пошук анкет', '🏙️ По місту'],
            ['👤 Мій профіль', '📝 Редагувати'],
            ['❤️ Хто мене лайкнув', '💌 Мої матчі'],
            ['🏆 Топ', "👨‍💼 Зв'язок з адміном"],
            ['👑 Адмін панель']
        ]
    else:
        keyboard = [
            ['💕 Пошук анкет', '🏙️ По місту'],
            ['👤 Мій профіль', '📝 Редагувати'],
            ['❤️ Хто мене лайкнув', '💌 Мої матчі'],
            ['🏆 Топ', "👨‍💼 Зв'язок з адміном"]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_search_menu():
    """Меню пошуку"""
    keyboard = [
        ['❤️ Лайк', '➡️ Далі'],
        ['🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_menu():
    """Меню профілю"""
    keyboard = [
        ['📝 Редагувати профіль', '📷 Додати фото'],
        ['🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu():
    """Адмін меню"""
    keyboard = [
        ['📊 Статистика', '👥 Користувачі'],
        ['📢 Розсилка', '🔄 Оновити базу'],
        ['🚫 Блокування', '🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_to_menu_keyboard():
    """Клавіатура для повернення в меню"""
    keyboard = [['🔙 Меню']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    """Клавіатура для скасування"""
    keyboard = [['🔙 Скасувати']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)