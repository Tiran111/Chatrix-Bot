from telegram import ReplyKeyboardMarkup

def get_search_navigation():
    """Навігація пошуку"""
    keyboard = [
        ['❤️ Лайк', '➡️ Далі'],
        ['🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_city_search_keyboard():
    """Клавіатура для пошуку за містом"""
    keyboard = [
        ['🔙 Скасувати']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_top_selection_keyboard():
    """Клавіатура для вибору топу"""
    keyboard = [
        ['👨 Топ чоловіків', '👩 Топ жінок'],
        ['🏆 Загальний топ', '🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)