from telegram import ReplyKeyboardMarkup, KeyboardButton

def get_profile_age_keyboard():
    """Клавіатура для введення віку"""
    keyboard = [
        [KeyboardButton("🔙 Скасувати")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_gender_keyboard():
    """Клавіатура для вибору статі"""
    keyboard = [
        [KeyboardButton("👨"), KeyboardButton("👩")],
        [KeyboardButton("🔙 Скасувати")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_seeking_gender_keyboard():
    """Клавіатура для вибору кого шукає"""
    keyboard = [
        [KeyboardButton("👩 Дівчину"), KeyboardButton("👨 Хлопця")],
        [KeyboardButton("👫 Всіх")],
        [KeyboardButton("🔙 Скасувати")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_goal_keyboard():
    """Клавіатура для вибору цілі знайомства"""
    keyboard = [
        [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
        [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
        [KeyboardButton("🔙 Скасувати")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_bio_keyboard():
    """Клавіатура для введення біо"""
    keyboard = [
        [KeyboardButton("🔙 Скасувати")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_photo_keyboard():
    """Клавіатура для додавання фото"""
    keyboard = [
        [KeyboardButton("🔙 Завершити")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)