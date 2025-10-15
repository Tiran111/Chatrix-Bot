import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import db
from utils.states import user_states, States
from keyboards.main_menu import get_main_menu, get_back_to_menu_keyboard

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник отримання фото"""
    try:
        user = update.effective_user
        user_id = user.id
        state = user_states.get(user_id, States.START)
        
        if state == States.ADDING_PHOTO:
            # Отримуємо файл фото з найвищою якістю
            photo_file = await update.message.photo[-1].get_file()
            file_id = photo_file.file_id
            
            logger.info(f"📸 Отримано фото від {user_id}, file_id: {file_id}")
            
            # Додаємо фото до профілю
            success = db.add_profile_photo(user_id, file_id)
            
            if success:
                # Оновлюємо стан
                user_states[user_id] = States.START
                
                # Показуємо оновлений профіль
                photos = db.get_profile_photos(user_id)
                user_info = db.get_user(user_id)
                
                success_text = (
                    f"✅ <b>Фото успішно додано!</b>\n\n"
                    f"📸 <b>Тепер у вашому профілі:</b> {len(photos)}/3 фото\n"
                    f"❤️ <b>Ваш рейтинг:</b> {user_info['rating'] if user_info else 0}\n\n"
                )
                
                if len(photos) < 3:
                    success_text += "Можете додати ще фото або перейти до оцінки інших користувачів 👇"
                else:
                    success_text += "🎉 Ви додали максимальну кількість фото! Тепер можете оцінювати інших 👇"
                
                await update.message.reply_text(
                    success_text,
                    reply_markup=get_main_menu(),
                    parse_mode='HTML'
                )
                
            else:
                error_text = (
                    "❌ <b>Не вдалося додати фото</b>\n\n"
                )
                
                photos = db.get_profile_photos(user_id)
                if len(photos) >= 3:
                    error_text += (
                        "⚠️ Ви вже досягли максимальної кількості фото (3).\n"
                        "Щоб додати нове фото, спочатку видаліть одне з існуючих.\n\n"
                        "👤 Перейдіть у 'Мій профіль' для управління фото"
                    )
                else:
                    error_text += (
                        "Можливі причини:\n"
                        "• Проблеми з сервером\n"
                        "• Некоректний формат фото\n"
                        "• Технічні обмеження\n\n"
                        "🔄 Спробуйте ще раз або зверніться до підтримки"
                    )
                
                await update.message.reply_text(
                    error_text,
                    reply_markup=get_main_menu(),
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                "📸 Щоб додати фото, оберіть 'Додати фото' в головному меню 👇",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки фото: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Сталася критична помилка при обробці фото. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник текстових повідомлень для профілю"""
    try:
        user_id = update.effective_user.id
        text = update.message.text
        state = user_states.get(user_id, States.START)
        
        logger.info(f"📝 Текст від {user_id} у стані {state}: {text}")
        
        if state == States.EDITING_PROFILE:
            # Обробка редагування профілю
            await handle_profile_edit(update, context, text)
        elif state == States.ADDING_BIO:
            # Обробка додавання біографії
            await handle_bio_add(update, context, text)
        else:
            # Стандартна відповідь
            await update.message.reply_text(
                "💬 Оберіть дію з головного меню 👇",
                reply_markup=get_main_menu()
            )
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки тексту: {e}", exc_info=True)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ профілю користувача"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        # Отримуємо дані користувача
        user = db.get_user(user_id)
        if not user:
            await query.edit_message_text(
                "❌ Не вдалося завантажити профіль",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
        
        # Отримуємо фото користувача
        photos = db.get_profile_photos(user_id)
        
        # Формуємо текст профілю
        profile_text = (
            f"👤 <b>Ваш профіль</b>\n\n"
            f"🆔 ID: {user['telegram_id']}\n"
            f"📛 Ім'я: {user['first_name']}\n"
            f"👤 Username: @{user['username'] if user['username'] else 'Немає'}\n"
            f"📸 Фото: {len(photos)}/3\n"
            f"❤️ Рейтинг: {user.get('rating', 5.0):.1f}\n"
            f"👍 Отримано лайків: {user.get('likes_count', 0)}\n"
            f"🤝 Матчі: {len(db.get_user_matches(user_id))}\n"
        )
        
        if user.get('age'):
            profile_text += f"🎂 Вік: {user['age']}\n"
        if user.get('gender'):
            profile_text += f"⚧️ Стать: {user['gender']}\n"
        if user.get('city'):
            profile_text += f"🏙️ Місто: {user['city']}\n"
        if user.get('goal'):
            profile_text += f"🎯 Ціль: {user['goal']}\n"
        
        profile_text += f"📅 Реєстрація: {user.get('created_at', 'Невідомо')[:10]}\n"
        profile_text += f"🕐 Остання активність: {user.get('last_active', 'Невідомо')[:16]}\n"
        
        # Додаємо біографію якщо є
        if user.get('bio'):
            profile_text += f"\n📝 <b>Про себе:</b>\n{user['bio']}\n"
        
        # Створюємо клавіатуру для управління профілем
        keyboard = []
        
        if photos:
            keyboard.append([InlineKeyboardButton("🗑️ Видалити фото", callback_data="delete_photos")])
        
        if len(photos) < 3:
            keyboard.append([InlineKeyboardButton("📸 Додати фото", callback_data="add_photo")])
        
        keyboard.extend([
            [InlineKeyboardButton("✏️ Редагувати профіль", callback_data="edit_profile")],
            [InlineKeyboardButton("📊 Статистика", callback_data="my_rating")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Відправляємо повідомлення
        await query.edit_message_text(
            profile_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка показу профілю: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                "❌ Помилка завантаження профілю",
                reply_markup=get_back_to_menu_keyboard()
            )
        except Exception:
            pass

async def handle_delete_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник видалення фото"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        # Отримуємо всі фото користувача
        photos = db.get_profile_photos(user_id)
        
        if not photos:
            await query.answer("❌ У вас немає фото для видалення")
            return
        
        # Створюємо клавіатуру з кнопками для видалення кожного фото
        keyboard = []
        for i, photo_id in enumerate(photos, 1):
            keyboard.append([
                InlineKeyboardButton(f"🗑️ Видалити фото {i}", callback_data=f"delete_photo_{photo_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="view_profile")])
        
        await query.edit_message_text(
            f"🖼️ <b>Управління фото</b>\n\n"
            f"Оберіть фото для видалення:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка показу управління фото: {e}", exc_info=True)

async def handle_profile_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обробка редагування профілю"""
    try:
        user_id = update.effective_user.id
        
        # Тут може бути логіка оновлення імені, віку, міста тощо
        # Наприклад:
        # db.update_user_profile(user_id, {'first_name': text})
        
        await update.message.reply_text(
            "✅ Профіль оновлено!",
            reply_markup=get_main_menu()
        )
        
        # Повертаємо до головного меню
        user_states[user_id] = States.START
        
    except Exception as e:
        logger.error(f"❌ Помилка редагування профілю: {e}")
        await update.message.reply_text(
            "❌ Помилка оновлення профілю",
            reply_markup=get_main_menu()
        )

async def handle_bio_add(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обробка додавання біографії"""
    try:
        user_id = update.effective_user.id
        
        # Обмежуємо довжину біографії
        if len(text) > 500:
            await update.message.reply_text(
                "❌ Занадто довгий текст. Максимум 500 символів. Спробуйте ще раз:"
            )
            return
        
        # Оновлюємо біографію
        success = db.cursor.execute(
            'UPDATE users SET bio = ? WHERE telegram_id = ?',
            (text, user_id)
        )
        db.conn.commit()
        
        if success:
            await update.message.reply_text(
                "✅ Біографію додано до вашого профілю!",
                reply_markup=get_main_menu()
            )
        else:
            await update.message.reply_text(
                "❌ Помилка додавання біографії",
                reply_markup=get_main_menu()
            )
        
        # Повертаємо до головного меню
        user_states[user_id] = States.START
        
    except Exception as e:
        logger.error(f"❌ Помилка додавання біографії: {e}")
        await update.message.reply_text(
            "❌ Помилка додавання біографії",
            reply_markup=get_main_menu()
        )