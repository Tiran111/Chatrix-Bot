from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from models import db
from handlers.notifications import notification_system
from handlers.search import show_user_profile
from keyboards.main_menu import get_main_menu
import logging

logger = logging.getLogger(__name__)

async def handle_like_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка лайку з callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        callback_data = query.data
        
        logger.info(f"🔍 [LIKE CALLBACK] Отримано callback: {callback_data} від {user.id}")
        
        # Отримуємо ID користувача з callback_data
        target_user_id = int(callback_data.split('_')[1])
        
        logger.info(f"🔍 [LIKE] Користувач {user.id} лайкає {target_user_id}")
        
        # Додаємо лайк з перевіркою обмежень
        success, message = db.add_like(user.id, target_user_id)
        
        logger.info(f"🔍 [LIKE RESULT] Успіх: {success}, Повідомлення: {message}")
        
        if success:
            # Перевіряємо чи це взаємний лайк (матч)
            is_mutual = db.has_liked(target_user_id, user.id)
            logger.info(f"🔍 [LIKE MUTUAL] Взаємний: {is_mutual}")
            
            if is_mutual:
                # Відправляємо сповіщення про матч
                await notification_system.notify_new_match(context, user.id, target_user_id)
                
                # Отримуємо дані користувача для кнопки переходу в Telegram
                matched_user = db.get_user(target_user_id)
                if matched_user:
                    username = matched_user.get('username')
                    if username:
                        # Створюємо кнопку для переходу в Telegram
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{username}")]
                        ])
                        await query.edit_message_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            "💬 *Тепер ви можете почати спілкування!*",
                            reply_markup=keyboard,
                            parse_mode='Markdown'
                        )
                    else:
                        await query.edit_message_text(
                            "💕 У вас матч! Ви вподобали один одного!\n\n"
                            "ℹ️ *У цього користувача немає username*",
                            parse_mode='Markdown'
                        )
                else:
                    await query.edit_message_text("💕 У вас матч! Ви вподобали один одного!")
            else:
                # Відправляємо сповіщення про лайк
                await notification_system.notify_new_like(context, user.id, target_user_id)
                await query.edit_message_text(f"❤️ {message}")
        else:
            await query.edit_message_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки лайку: {e}", exc_info=True)
        try:
            await update.callback_query.edit_message_text("❌ Сталася помилка при обробці лайку.")
        except:
            pass

async def handle_next_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопки 'Далі' з callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        logger.info(f"🔍 [NEXT CALLBACK] Обробка кнопки 'Далі' для {user.id}")
        
        search_users = context.user_data.get('search_users', [])
        current_index = context.user_data.get('current_index', 0)
        search_type = context.user_data.get('search_type', 'random')
        
        logger.info(f"🔍 [NEXT CALLBACK] Тип пошуку: {search_type}, індекс: {current_index}, знайдено: {len(search_users)}")
        
        if not search_users:
            await query.edit_message_text("🔄 Шукаємо нові анкети...")
            from handlers.search import search_profiles
            await search_profiles(update, context)
            return
        
        # Якщо це пошук за містом, шукаємо наступного користувача
        if search_type == 'city':
            if current_index < len(search_users) - 1:
                current_index += 1
                context.user_data['current_index'] = current_index
                user_data = search_users[current_index]
                
                # Додаємо запис про перегляд профілю
                db.add_profile_view(user.id, user_data[1])
                
                await show_user_profile(update, context, user_data, "🏙️ Знайдені анкети")
            else:
                await query.edit_message_text("✅ Це остання анкета в цьому місті", reply_markup=get_main_menu(user.id))
        else:
            # Для випадкового пошуку - шукаємо нову анкету
            random_user = db.get_random_user(user.id)
            if random_user:
                # Додаємо запис про перегляд профілю
                db.add_profile_view(user.id, random_user[1])
                
                await show_user_profile(update, context, random_user, "💕 Знайдені анкети")
                context.user_data['search_users'] = [random_user]
                context.user_data['current_index'] = 0
            else:
                await query.edit_message_text(
                    "😔 Більше немає анкет для перегляду\n\n"
                    "💡 Спробуйте:\n"
                    "• Змінити критерії пошуку\n"
                    "• Пошукати за іншим містом\n"
                    "• Зачекати поки з'являться нові користувачі",
                    reply_markup=get_main_menu(user.id)
                )
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки кнопки 'Далі': {e}", exc_info=True)
        try:
            await update.callback_query.edit_message_text("❌ Сталася помилка.")
        except:
            pass

# Функції для реєстрації обробників
def setup_callback_handlers(application):
    """Налаштування callback обробників"""
    application.add_handler(CallbackQueryHandler(handle_like_callback, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(handle_next_profile_callback, pattern='^next_profile$'))
    logger.info("✅ Callback обробники налаштовані")