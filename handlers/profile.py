from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States, user_profiles
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)

async def start_profile_creation(update: Update, context: CallbackContext):
    """Початок створення профілю"""
    user = update.effective_user
    
    # Перевіряємо чи користувач заблокований
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_banned'):
        await update.message.reply_text("🚫 Ваш акаунт заблоковано.")
        return
    
    # Ініціалізуємо профіль
    user_states[user.id] = States.PROFILE_AGE
    user_profiles[user.id] = {}
    
    # Очищаємо попередні дані
    context.user_data.pop('profile_data', None)
    
    logger.info(f"🔧 [PROFILE START] Користувач {user.id} почав створення профілю")
    
    await update.message.reply_text(
        "📝 *Створення профілю*\n\nВведіть ваш вік (18-100):",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_profile_message(update: Update, context: CallbackContext):
    """Обробка повідомлень під час створення профілю"""
    user = update.effective_user
    text = update.message.text
    state = user_states.get(user.id)

    logger.info(f"🔧 [PROFILE] {user.first_name}: '{text}', стан: {state}")

    if text == "🔙 Скасувати":
        user_states[user.id] = States.START
        user_profiles.pop(user.id, None)
        await update.message.reply_text("❌ Скасовано", reply_markup=get_main_menu(user.id))
        return

    # Перевіряємо чи існує профіль для користувача
    if user.id not in user_profiles:
        user_profiles[user.id] = {}
        logger.info(f"🔧 [PROFILE] Створено новий тимчасовий профіль для {user.id}")

    if state == States.PROFILE_AGE:
        try:
            age = int(text)
            if age < 18 or age > 100:
                await update.message.reply_text("❌ Вік має бути від 18 до 100 років")
                return
            
            user_profiles[user.id]['age'] = age
            user_states[user.id] = States.PROFILE_GENDER
            
            logger.info(f"🔧 [PROFILE] Користувач {user.id} встановив вік: {age}")
            
            keyboard = [[KeyboardButton("👨"), KeyboardButton("👩")], [KeyboardButton("🔙 Скасувати")]]
            await update.message.reply_text(
                f"✅ Вік: {age} років\n\nОберіть стать:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        except ValueError:
            await update.message.reply_text("❌ Введіть коректний вік (число)")

    elif state == States.PROFILE_GENDER:
        if text == "👨":
            user_profiles[user.id]['gender'] = 'male'
            user_states[user.id] = States.PROFILE_CITY
            logger.info(f"🔧 [PROFILE] Користувач {user.id} обрав стать: male")
            await update.message.reply_text(
                "✅ Стать: 👨 Чоловік\n\nВведіть ваше місто:",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        elif text == "👩":
            user_profiles[user.id]['gender'] = 'female'
            user_states[user.id] = States.PROFILE_CITY
            logger.info(f"🔧 [PROFILE] Користувач {user.id} обрав стать: female")
            await update.message.reply_text(
                "✅ Стать: 👩 Жінка\n\nВведіть ваше місто:",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Оберіть стать з кнопок")

    elif state == States.PROFILE_CITY:
        if len(text) >= 2:
            user_profiles[user.id]['city'] = text
            user_states[user.id] = States.PROFILE_SEEKING_GENDER
            
            logger.info(f"🔧 [PROFILE] Користувач {user.id} встановив місто: {text}")
            
            keyboard = [
                [KeyboardButton("👩 Дівчину"), KeyboardButton("👨 Хлопця")],
                [KeyboardButton("👫 Всіх")],
                [KeyboardButton("🔙 Скасувати")]
            ]
            await update.message.reply_text(
                f"✅ Місто: {text}\n\nКого шукаєте?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Назва міста закоротка. Спробуйте ще раз:")

    elif state == States.PROFILE_SEEKING_GENDER:
        if text == "👩 Дівчину":
            user_profiles[user.id]['seeking_gender'] = 'female'
            user_states[user.id] = States.PROFILE_GOAL
            logger.info(f"🔧 [PROFILE] Користувач {user.id} шукає: female")
        elif text == "👨 Хлопця":
            user_profiles[user.id]['seeking_gender'] = 'male'
            user_states[user.id] = States.PROFILE_GOAL
            logger.info(f"🔧 [PROFILE] Користувач {user.id} шукає: male")
        elif text == "👫 Всіх":
            user_profiles[user.id]['seeking_gender'] = 'all'
            user_states[user.id] = States.PROFILE_GOAL
            logger.info(f"🔧 [PROFILE] Користувач {user.id} шукає: all")
        else:
            await update.message.reply_text("❌ Оберіть варіант з кнопок")
            return
        
        # Показуємо вибір цілі
        keyboard = [
            [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
            [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
            [KeyboardButton("🔙 Скасувати")]
        ]
        seeking_text = {
            'female': '👩 Дівчину',
            'male': '👨 Хлопця', 
            'all': '👫 Всіх'
        }.get(user_profiles[user.id]['seeking_gender'])
        
        await update.message.reply_text(
            f"✅ Шукаю: {seeking_text}\n\nОберіть ціль знайомства:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    elif state == States.PROFILE_GOAL:
        goal_map = {
            '💞 Серйозні стосунки': 'Серйозні стосунки',
            '👥 Дружба': 'Дружба',
            '🎉 Разові зустрічі': 'Разові зустрічі',
            '🏃 Активний відпочинок': 'Активний відпочинок'
        }
        
        if text in goal_map:
            user_profiles[user.id]['goal'] = goal_map[text]
            user_states[user.id] = States.PROFILE_BIO
            
            logger.info(f"🔧 [PROFILE] Користувач {user.id} обрав ціль: {goal_map[text]}")
            
            await update.message.reply_text(
                f"✅ Ціль: {text}\n\nНапишіть про себе (мінімум 10 символів):",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Оберіть ціль з кнопок")

    elif state == States.PROFILE_BIO:
        if len(text) >= 10:
            user_profiles[user.id]['bio'] = text
            
            logger.info(f"🔧 [PROFILE] Користувач {user.id} заповнив біо")
            logger.info(f"🔧 [PROFILE DATA] Повні дані профілю: {user_profiles[user.id]}")
            
            # Зберігаємо профіль
            success = db.update_user_profile(
                telegram_id=user.id,
                age=user_profiles[user.id]['age'],
                gender=user_profiles[user.id]['gender'],
                city=user_profiles[user.id]['city'],
                seeking_gender=user_profiles[user.id].get('seeking_gender', 'all'),
                goal=user_profiles[user.id]['goal'],
                bio=user_profiles[user.id]['bio']
            )
            
            if success:
                user_states[user.id] = States.ADD_MAIN_PHOTO
                
                # Перевіряємо збережені дані
                saved_user = db.get_user(user.id)
                logger.info(f"🔧 [PROFILE SAVED] Збережені дані: {saved_user}")
                
                await update.message.reply_text(
                    "🎉 *Профіль створено!*\n\nТепер додайте фото для профілю (максимум 3 фото):",
                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Завершити")]], resize_keyboard=True),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Помилка збереження профілю")
        else:
            await update.message.reply_text("❌ Опис закороткий. Мінімум 10 символів.")

async def handle_main_photo(update: Update, context: CallbackContext):
    """Обробка додавання фото"""
    user = update.effective_user
    
    if user_states.get(user.id) == States.ADD_MAIN_PHOTO and update.message.photo:
        photo = update.message.photo[-1]
        
        logger.info(f"🔧 [PHOTO] Користувач {user.id} додає фото")
        
        # Додаємо фото
        success = db.add_profile_photo(user.id, photo.file_id)
        
        if success:
            photos = db.get_profile_photos(user.id)
            if len(photos) < 3:
                await update.message.reply_text(
                    f"✅ Фото додано! У вас {len(photos)}/3 фото\nНадішліть ще фото або натисніть '🔙 Завершити'",
                    reply_markup=ReplyKeyboardMarkup([['🔙 Завершити']], resize_keyboard=True)
                )
            else:
                user_states[user.id] = States.START
                user_profiles.pop(user.id, None)  # Очищаємо тимчасові дані
                await update.message.reply_text(
                    "✅ Ви додали максимальну кількість фото (3 фото)\nПрофіль готовий!",
                    reply_markup=get_main_menu(user.id)
                )
        else:
            await update.message.reply_text("❌ Помилка додавання фото")
    
    elif user_states.get(user.id) == States.ADD_MAIN_PHOTO and update.message.text == "🔙 Завершити":
        user_states[user.id] = States.START
        user_profiles.pop(user.id, None)  # Очищаємо тимчасові дані
        photos_count = len(db.get_profile_photos(user.id))
        await update.message.reply_text(
            f"🎉 Профіль створено! Додано {photos_count} фото",
            reply_markup=get_main_menu(user.id)
        )
    
    elif user_states.get(user.id) == States.ADD_MAIN_PHOTO:
        await update.message.reply_text("📷 Будь ласка, надішліть фото:")

async def show_my_profile(update: Update, context: CallbackContext):
    """Показати профіль користувача"""
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if not user_data or not user_data.get('age'):
        await update.message.reply_text("❌ У вас ще немає профілю", reply_markup=get_main_menu(user.id))
        return
    
    photos = db.get_profile_photos(user.id)
    
    # Детальне логування для дебагу
    logger.info(f"🔧 [SHOW PROFILE] Дані користувача {user.id}: {user_data}")
    
    # Форматування профілю
    gender_display = "👨 Чоловік" if user_data['gender'] == 'male' else "👩 Жінка"
    
    seeking_display = {
        'female': '👩 Дівчину',
        'male': '👨 Хлопця',
        'all': '👫 Всіх'
    }.get(user_data.get('seeking_gender', 'all'), '👫 Всіх')
    
    goal_display = {
        'Серйозні стосунки': '💞 Серйозні стосунки',
        'Дружба': '👥 Дружба',
        'Разові зустрічі': '🎉 Разові зустрічі',
        'Активний відпочинок': '🏃 Активний відпочинок'
    }.get(user_data['goal'], user_data['goal'])
    
    profile_text = f"""👤 *Ваш профіль*

*Ім'я:* {user.first_name}
*Вік:* {user_data['age']} років
*Стать:* {gender_display}
*Місто:* {user_data['city']}
*Шукаю:* {seeking_display}  
*Ціль:* {goal_display}

*Про себе:*
{user_data['bio']}

*Фото:* {len(photos)}/3
❤️ *Лайків:* {user_data.get('likes_count', 0)}"""
    
    # Відправляємо фото з описом
    if photos:
        await update.message.reply_photo(
            photo=photos[0], 
            caption=profile_text,
            reply_markup=get_main_menu(user.id),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            profile_text,
            reply_markup=get_main_menu(user.id),
            parse_mode='Markdown'
        )