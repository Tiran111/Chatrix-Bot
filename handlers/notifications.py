from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
try:
    from database_postgres import db
except ImportError:
    from database.models import db
from keyboards.main_menu import get_main_menu
from keyboards.main_menu import get_main_menu
import asyncio
import logging
from config import ADMIN_ID

logger = logging.getLogger(__name__)

class NotificationSystem:
    def __init__(self):
        self.pending_notifications = {}
    
    async def notify_new_like(self, context: ContextTypes.DEFAULT_TYPE, from_user_id, to_user_id):
        """Покращене сповіщення про лайк"""
        try:
            from_user = db.get_user(from_user_id)
            to_user = db.get_user(to_user_id)
            
            if not from_user or not to_user:
                return
            
            # Отримуємо актуальний рейтинг
            current_rating = db.calculate_user_rating(to_user_id)
            
            message = (
                f"💕 *У вас новий лайк!*\n\n"
                f"👤 *{from_user['first_name']}* вподобав(ла) вашу анкету!\n"
                f"⭐ *Ваш рейтинг:* {current_rating:.1f}/10.0\n\n"
                f"🎯 *Порада:* Активність підвищує ваш рейтинг!"
            )
            
            await context.bot.send_message(
                chat_id=to_user_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Сповіщення про лайк відправлено {to_user_id}")
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про лайк: {e}")
    
    async def notify_new_match(self, context: ContextTypes.DEFAULT_TYPE, user1_id, user2_id):
        """Сповістити про новий матч"""
        try:
            user1 = db.get_user(user1_id)
            user2 = db.get_user(user2_id)
            
            if user1 and user2:
                # Отримуємо username для кнопок
                user1_username = user1.get('username')
                user2_username = user2.get('username')
                
                # Сповіщаємо першому користувачу
                if user2_username:
                    keyboard1 = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{user2_username}")]
                    ])
                    await context.bot.send_message(
                        chat_id=user1_id,
                        text=f"💕 *У вас новий матч!*\n\nВи та {user2['first_name']} вподобали один одного!\n\n💬 *Тепер ви можете почати спілкування!*",
                        reply_markup=keyboard1,
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user1_id,
                        text=f"💕 *У вас новий матч!*\n\nВи та {user2['first_name']} вподобали один одного!\n\nℹ️ *У цього користувача немає username*",
                        parse_mode='Markdown'
                    )
                
                # Сповіщаємо другому користувачу
                if user1_username:
                    keyboard2 = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{user1_username}")]
                    ])
                    await context.bot.send_message(
                        chat_id=user2_id,
                        text=f"💕 *У вас новий матч!*\n\nВи та {user1['first_name']} вподобали один одного!\n\n💬 *Тепер ви можете почати спілкування!*",
                        reply_markup=keyboard2,
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user2_id,
                        text=f"💕 *У вас новий матч!*\n\nВи та {user1['first_name']} вподобали один одного!\n\nℹ️ *У цього користувача немає username*",
                        parse_mode='Markdown'
                    )
                    
                logger.info(f"✅ Сповіщення про матч відправлено {user1_id} та {user2_id}")
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про матч: {e}")
    
    async def notify_contact_admin(self, context: ContextTypes.DEFAULT_TYPE, user_id, message_text):
        """Сповістити адміна про нове повідомлення"""
        try:
            user = db.get_user(user_id)
            if not user:
                return
            
            admin_message = f"""📩 *Нове повідомлення від користувача*

👤 *Користувач:* {user['first_name']}
🆔 *ID:* `{user_id}`
📝 *Повідомлення:*
{message_text}"""

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Сповіщення адміну відправлено")
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення адміну: {e}")
    
    async def notify_broadcast_sent(self, context: ContextTypes.DEFAULT_TYPE, user_id):
        """Сповістити про успішну розсилку"""
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ *Розсилка успішно завершена!*",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про розсилку: {e}")
    
    async def notify_broadcast_complete(self, context: ContextTypes.DEFAULT_TYPE, admin_id, success_count, total_count):
        """Сповістити адміна про завершення розсилки"""
        try:
            message = (
                f"📢 *Розсилка завершена*\n\n"
                f"✅ Успішно: {success_count}\n"
                f"❌ Не вдалося: {total_count - success_count}\n"
                f"📊 Всього: {total_count}"
            )
            
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Сповіщення про розсилку відправлено адміну {admin_id}")
        except Exception as e:
            logger.error(f"❌ Помилка відправки сповіщення про розсилку: {e}")
    
    async def notify_broadcast_message(self, context: ContextTypes.DEFAULT_TYPE, user_id, message_text):
        """Сповістити користувача про розсилку"""
        try:
            broadcast_message = f"""📢 *Повідомлення від адміністратора*

{message_text}

---
💞 *Chatrix Bot* - знайомства та спілкування"""

            await context.bot.send_message(
                chat_id=user_id,
                text=broadcast_message,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"❌ Помилка відправки розсилки для {user_id}: {e}")
            return False
    
    async def notify_rating_update(self, context: ContextTypes.DEFAULT_TYPE, user_id):
        """Сповіщення про зміну рейтингу"""
        try:
            user = db.get_user(user_id)
            if not user:
                return
            
            current_rating = db.calculate_user_rating(user_id)
            old_rating = user.get('rating', 5.0)
            
            # Відправляємо сповіщення тільки якщо рейтинг змінився значно
            if abs(current_rating - old_rating) >= 0.3:
                if current_rating > old_rating:
                    emoji = "📈"
                    trend = "підвищився"
                else:
                    emoji = "📉" 
                    trend = "знизився"
                
                message = (
                    f"{emoji} *Ваш рейтинг {trend}!*\n\n"
                    f"⭐ *Новий рейтинг:* {current_rating:.1f}/10.0\n\n"
                    f"💡 *Як підвищити рейтинг:*\n"
                    f"• ❤️ Отримуйте лайки\n"
                    f"• 📝 Заповнюйте профіль\n" 
                    f"• 📷 Додавайте фото\n"
                    f"• 🔍 Буйте активними у пошуку"
                )
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про рейтинг: {e}")
    
    async def notify_daily_summary(self, context: ContextTypes.DEFAULT_TYPE, user_id):
        """Щоденна статистика"""
        try:
            user = db.get_user(user_id)
            if not user:
                return
            
            # Отримуємо статистику за день
            new_likes = self.get_new_likes_today(user_id)
            new_matches = self.get_new_matches_today(user_id)
            profile_views = self.get_profile_views_today(user_id)
            
            if new_likes > 0 or new_matches > 0:
                message = f"📊 *Ваша щоденна статистика:*\n\n"
                if new_likes > 0:
                    message += f"💕 Нові лайки: {new_likes}\n"
                if new_matches > 0:
                    message += f"💌 Нові матчі: {new_matches}\n"
                if profile_views > 0:
                    message += f"👀 Перегляди профілю: {profile_views}\n"
                
                message += f"\n🎯 Продовжуйте бути активними!"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"❌ Помилка щоденного сповіщення: {e}")
    
    async def notify_profile_completion(self, context: ContextTypes.DEFAULT_TYPE, user_id):
        """Нагадування про заповнення профілю"""
        try:
            user_data, is_complete = db.get_user_profile(user_id)
            
            if not is_complete:
                message = "📝 *Нагадування:*\n\nЗаповніть свій профіль повністю, щоб отримувати більше лайків та матчів!"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=get_main_menu(user_id),
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення про профіль: {e}")
    
    def get_new_likes_today(self, user_id):
        """Отримати кількість нових лайків сьогодні"""
        try:
            db.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
            user = db.cursor.fetchone()
            if not user:
                return 0
            
            db.cursor.execute('''
                SELECT COUNT(*) FROM likes 
                WHERE to_user_id = ? AND DATE(created_at) = DATE('now')
            ''', (user[0],))
            result = db.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ Помилка отримання лайків за день: {e}")
            return 0
    
    def get_new_matches_today(self, user_id):
        """Отримати кількість нових матчів сьогодні"""
        try:
            db.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
            user = db.cursor.fetchone()
            if not user:
                return 0
            
            db.cursor.execute('''
                SELECT COUNT(DISTINCT u.id) FROM users u
                JOIN likes l1 ON u.id = l1.to_user_id
                JOIN likes l2 ON u.id = l2.from_user_id
                WHERE l1.from_user_id = ? AND l2.to_user_id = ? 
                AND (DATE(l1.created_at) = DATE('now') OR DATE(l2.created_at) = DATE('now'))
            ''', (user[0], user[0]))
            
            result = db.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ Помилка отримання матчів за день: {e}")
            return 0
    
    def get_profile_views_today(self, user_id):
        """Отримати кількість переглядів профілю за день"""
        try:
            db.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
            user = db.cursor.fetchone()
            if not user:
                return 0
            
            db.cursor.execute('''
                SELECT COUNT(*) FROM profile_views 
                WHERE viewed_user_id = ? AND DATE(viewed_at) = DATE('now')
            ''', (user[0],))
            result = db.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ Помилка отримання переглядів: {e}")
            return 0

# Глобальний об'єкт системи сповіщень
notification_system = NotificationSystem()