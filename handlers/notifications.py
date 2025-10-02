from telegram import Update
from telegram.ext import ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
import asyncio

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
            
            # Оновлюємо рейтинг отримувача
            db.update_rating_on_like(to_user_id)
            
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
            print(f"✅ Покращене сповіщення про лайк відправлено {to_user_id}")
        except Exception as e:
            print(f"❌ Помилка покращеного сповіщення: {e}")
    
    async def notify_new_match(self, context: ContextTypes.DEFAULT_TYPE, user1_id, user2_id):
        """Сповістити про новий матч"""
        try:
            user1 = db.get_user(user1_id)
            user2 = db.get_user(user2_id)
            
            if user1 and user2:
                # Сповіщаємо першому користувачу
                await context.bot.send_message(
                    chat_id=user1_id,
                    text=f"💕 *У вас новий матч!*\n\nВи та {user2['first_name']} вподобали один одного!",
                    parse_mode='Markdown'
                )
                # Сповіщаємо другому користувачу
                await context.bot.send_message(
                    chat_id=user2_id,
                    text=f"💕 *У вас новий матч!*\n\nВи та {user1['first_name']} вподобали один одного!",
                    parse_mode='Markdown'
                )
                print(f"✅ Сповіщення про матч відправлено {user1_id} та {user2_id}")
        except Exception as e:
            print(f"❌ Помилка сповіщення про матч: {e}")
    
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
            print(f"❌ Помилка сповіщення про рейтинг: {e}")
    
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
            print(f"❌ Помилка щоденного сповіщення: {e}")
    
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
            print(f"❌ Помилка сповіщення про профіль: {e}")
    
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
            print(f"❌ Помилка отримання лайків за день: {e}")
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
            print(f"❌ Помилка отримання матчів за день: {e}")
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
            print(f"❌ Помилка отримання переглядів: {e}")
            return 0

# Глобальний об'єкт системи сповіщень
notification_system = NotificationSystem()

def init_notification_tables():
    """Ініціалізація таблиць для сповіщень"""
    try:
        # Таблиця для відстеження переглядів профілю
        db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                viewer_id INTEGER NOT NULL,
                viewed_user_id INTEGER NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (viewer_id) REFERENCES users (id),
                FOREIGN KEY (viewed_user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблиця для відстеження активності
        db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                activity_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        db.conn.commit()
        print("✅ Таблиці сповіщень ініціалізовано")
    except Exception as e:
        print(f"❌ Помилка ініціалізації таблиць сповіщень: {e}")

# Ініціалізація таблиць при імпорті
init_notification_tables()

# Додаємо метод до бази даних для додавання переглядів
def add_profile_view(viewer_id, viewed_user_id):
    """Додати запис про перегляд профілю"""
    try:
        db.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (viewer_id,))
        viewer = db.cursor.fetchone()
        db.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (viewed_user_id,))
        viewed = db.cursor.fetchone()
        
        if viewer and viewed:
            db.cursor.execute('''
                INSERT INTO profile_views (viewer_id, viewed_user_id)
                VALUES (?, ?)
            ''', (viewer[0], viewed[0]))
            db.conn.commit()
            return True
    except Exception as e:
        print(f"❌ Помилка додавання перегляду: {e}")
    return False

# Додаємо метод до глобального об'єкта db
db.add_profile_view = add_profile_view