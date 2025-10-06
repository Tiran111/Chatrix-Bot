import sqlite3
import os
from datetime import datetime

# Шлях до бази даних
DATABASE_PATH = 'dating_bot.db'

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        """Ініціалізація бази даних"""
        print("🔄 Ініціалізація бази даних...")
        
        # Таблиця користувачів
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                city TEXT,
                seeking_gender TEXT,
                goal TEXT,
                bio TEXT,
                has_photo BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                likes_count INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                rating REAL DEFAULT 5.0
            )
        ''')
        
        # Таблиця фото
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Таблиця лайків
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user_id) REFERENCES users (id),
                FOREIGN KEY (to_user_id) REFERENCES users (id),
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        
        # Таблиця для відстеження щоденних лайків
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                likes_given INTEGER DEFAULT 0,
                date DATE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, date)
            )
        ''')
        
        # Таблиця для переглядів профілів
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                viewer_id INTEGER NOT NULL,
                viewed_user_id INTEGER NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (viewer_id) REFERENCES users (id),
                FOREIGN KEY (viewed_user_id) REFERENCES users (id)
            )
        ''')
        
        self.conn.commit()
        print("✅ База даних ініціалізована")
    
    def add_user(self, telegram_id, username, first_name):
        """Додавання нового користувача"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO users (telegram_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (telegram_id, username, first_name))
            self.conn.commit()
            print(f"✅ Користувач доданий/оновлений: {telegram_id} - {first_name}")
            return True
        except Exception as e:
            print(f"❌ Помилка додавання користувача: {e}")
            return False
    
    def get_user(self, telegram_id):
        """Отримання користувача за telegram_id"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            if user:
                return dict(user)
            return None
        except Exception as e:
            print(f"❌ Помилка отримання користувача: {e}")
            return None
    
    def update_user_profile(self, telegram_id, age, gender, city, seeking_gender, goal, bio):
        """Оновлення профілю користувача"""
        try:
            print(f"🔄 Оновлення профілю для {telegram_id}")
            
            # Спочатку перевіримо чи користувач існує
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            existing_user = self.cursor.fetchone()
            
            if not existing_user:
                print(f"❌ Користувача {telegram_id} не знайдено, створюємо...")
                # Створюємо базового користувача
                self.cursor.execute('INSERT INTO users (telegram_id, first_name) VALUES (?, ?)', (telegram_id, "User"))
                self.conn.commit()
                print(f"✅ Користувача {telegram_id} створено")
            
            # Тепер оновлюємо профіль
            self.cursor.execute('''
                UPDATE users 
                SET age = ?, gender = ?, city = ?, seeking_gender = ?, goal = ?, bio = ?
                WHERE telegram_id = ?
            ''', (age, gender, city, seeking_gender, goal, bio, telegram_id))
            
            self.conn.commit()
            print(f"✅ Профіль оновлено для {telegram_id}")
            return True
                
        except Exception as e:
            print(f"❌ Помилка оновлення профілю: {e}")
            return False
    
    def add_profile_photo(self, telegram_id, file_id):
        """Додавання фото до профілю (максимум 3 фото)"""
        try:
            print(f"🔄 Додаємо фото для {telegram_id}, file_id: {file_id}")
            
            # Отримаємо user_id
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                print(f"❌ Користувача {telegram_id} не знайдено")
                return False
            
            user_id = user[0]
            
            # Перевіряємо кількість фото
            current_photos = self.get_profile_photos(telegram_id)
            if len(current_photos) >= 3:
                print(f"❌ Досягнуто ліміт фото (максимум 3)")
                return False
            
            # Додаємо фото
            self.cursor.execute('INSERT INTO photos (user_id, file_id) VALUES (?, ?)', (user_id, file_id))
            
            # Встановлюємо, що користувач має фото
            self.cursor.execute('UPDATE users SET has_photo = TRUE WHERE telegram_id = ?', (telegram_id,))
            
            self.conn.commit()
            print("✅ Фото успішно додано до бази даних!")
            return True
            
        except Exception as e:
            print(f"❌ Помилка додавання фото: {e}")
            return False
    
    def get_main_photo(self, telegram_id):
        """Отримання першого фото користувача"""
        try:
            self.cursor.execute('''
                SELECT p.file_id FROM photos p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = ?
                LIMIT 1
            ''', (telegram_id,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"❌ Помилка отримання фото: {e}")
            return None
    
    def get_profile_photos(self, telegram_id):
        """Отримання всіх фото профілю"""
        try:
            self.cursor.execute('''
                SELECT p.file_id FROM photos p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = ?
            ''', (telegram_id,))
            photos = self.cursor.fetchall()
            return [photo[0] for photo in photos]
        except Exception as e:
            print(f"❌ Помилка отримання фото: {e}")
            return []
    
    def get_user_profile(self, telegram_id):
        """Отримання профілю користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            if user and user[4]:  # перевірка чи заповнений вік
                return user, True
            return user, False
        except Exception as e:
            print(f"❌ Помилка отримання профілю: {e}")
            return None, False
    
    def calculate_user_rating(self, telegram_id):
        """Розрахунок рейтингу користувача"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                return 5.0
            
            base_rating = 5.0  # Базовий рейтинг
            
            # Бонус за лайки (0.1 за кожен лайк)
            likes_bonus = user.get('likes_count', 0) * 0.1
            base_rating += min(likes_bonus, 2.0)  # Макс +2.0
            
            # Бонус за заповненість профілю
            profile_bonus = 0
            if user.get('age'):
                profile_bonus += 0.5
            if user.get('bio') and len(user.get('bio', '')) > 50:
                profile_bonus += 1.0
            if user.get('city'):
                profile_bonus += 0.5
            
            # Бонус за фото
            photos = self.get_profile_photos(telegram_id)
            if len(photos) >= 1:
                profile_bonus += 1.0
            if len(photos) >= 3:
                profile_bonus += 1.0
            
            base_rating += profile_bonus
            
            # Обмежуємо діапазон 1.0 - 10.0
            final_rating = max(1.0, min(10.0, base_rating))
            
            # Оновлюємо рейтинг в базі
            self.cursor.execute(
                'UPDATE users SET rating = ? WHERE telegram_id = ?',
                (final_rating, telegram_id)
            )
            self.conn.commit()
            
            return final_rating
            
        except Exception as e:
            print(f"❌ Помилка розрахунку рейтингу: {e}")
            return 5.0

    def update_rating_on_like(self, to_user_id):
        """Оновлення рейтингу при отриманні лайка"""
        try:
            # Збільшуємо рейтинг на 0.2 за кожен лайк
            self.cursor.execute('''
                UPDATE users SET rating = MIN(10.0, rating + 0.2) 
                WHERE telegram_id = ?
            ''', (to_user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Помилка оновлення рейтингу: {e}")
            return False

    def get_random_user(self, current_user_id, city=None):
        """Отримання випадкового користувача для пошуку з урахуванням рейтингу"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                return None
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            
            query = '''
                SELECT u.* FROM users u
                WHERE u.telegram_id != ? AND u.age IS NOT NULL 
                AND u.has_photo = TRUE AND u.is_banned = FALSE
                AND u.rating IS NOT NULL
            '''
            params = [current_user_id]
            
            if seeking_gender != 'all':
                query += ' AND u.gender = ?'
                params.append(seeking_gender)
            
            if city:
                query += ' AND u.city LIKE ?'
                params.append(f'%{city}%')
            
            # Сортуємо по рейтингу (пріоритет) і випадково
            query += ' ORDER BY u.rating DESC, RANDOM() LIMIT 1'
            
            self.cursor.execute(query, params)
            user = self.cursor.fetchone()
            return user
        except Exception as e:
            print(f"❌ Помилка отримання випадкового користувача: {e}")
            return None
    
    def get_users_by_city(self, city, current_user_id):
        """Отримання користувачів за містом"""
        try:
            print(f"🔍 Пошук у місті: '{city}' для користувача {current_user_id}")
            
            current_user = self.get_user(current_user_id)
            if not current_user:
                print("❌ Поточного користувача не знайдено")
                return []
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            print(f"🔍 Шукає стать: {seeking_gender}")
            
            # Видаляємо емодзі з назви міста
            clean_city = city.replace('🏙️ ', '').strip()
            
            query = '''
                SELECT u.* FROM users u
                WHERE u.telegram_id != ? AND u.city LIKE ? 
                AND u.age IS NOT NULL AND u.has_photo = TRUE AND u.is_banned = FALSE
                AND u.rating IS NOT NULL
            '''
            params = [current_user_id, f'%{clean_city}%']
            
            if seeking_gender != 'all':
                query += ' AND u.gender = ?'
                params.append(seeking_gender)
            
            query += ' ORDER BY u.rating DESC, RANDOM() LIMIT 20'
            
            print(f"🔍 SQL запит: {query}")
            print(f"🔍 Параметри: {params}")
            
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
            print(f"🔍 Знайдено користувачів: {len(users)}")
            return users
        except Exception as e:
            print(f"❌ Помилка пошуку за містом: {e}")
            return []
    
    def get_likes_count(self, user_id):
        """Отримання кількості лайків"""
        try:
            self.cursor.execute('SELECT likes_count FROM users WHERE id = ?', (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"❌ Помилка отримання лайків: {e}")
            return 0
    
    def can_user_like(self, from_user_id):
        """Перевірити чи може користувач ставити лайки (обмеження 50 лайків на день)"""
        try:
            today = datetime.now().date()
            
            # Отримуємо user_id
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (from_user_id,))
            from_user = self.cursor.fetchone()
            if not from_user:
                return False
            
            user_id = from_user[0]
            
            # Перевіряємо кількість лайків сьогодні
            self.cursor.execute('''
                SELECT likes_given FROM daily_likes 
                WHERE user_id = ? AND date = ?
            ''', (user_id, today))
            
            result = self.cursor.fetchone()
            
            if result:
                likes_today = result[0]
                if likes_today >= 50:  # Ліміт 50 лайків на день
                    return False
            else:
                # Якщо запису немає, створюємо новий
                self.cursor.execute('''
                    INSERT INTO daily_likes (user_id, likes_given, date)
                    VALUES (?, 0, ?)
                ''', (user_id, today))
                self.conn.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Помилка перевірки ліміту лайків: {e}")
            return False
    
    def add_like(self, from_user_id, to_user_id):
        """Додавання лайку з оновленням рейтингу та перевіркою обмежень"""
        try:
            # Перевіряємо чи не лайкаємо самі себе
            if from_user_id == to_user_id:
                return False, "Ви не можете лайкнути самого себе!"
            
            # Перевіряємо чи не заблокований користувач
            from_user_data = self.get_user(from_user_id)
            to_user_data = self.get_user(to_user_id)
            
            if not from_user_data or not to_user_data:
                return False, "Користувача не знайдено"
            
            if from_user_data.get('is_banned') or to_user_data.get('is_banned'):
                return False, "Користувач заблокований"
            
            # Перевіряємо чи може користувач ставити лайки
            if not self.can_user_like(from_user_id):
                return False, "Досягнуто денний ліміт лайків (50)"
            
            # Перевіряємо чи вже існує лайк
            if self.has_liked(from_user_id, to_user_id):
                return False, "Ви вже лайкнули цього користувача"
            
            # Отримуємо user_id
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (from_user_id,))
            from_user = self.cursor.fetchone()
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (to_user_id,))
            to_user = self.cursor.fetchone()
            
            if not from_user or not to_user:
                return False, "Користувача не знайдено"
            
            # Додаємо лайк
            self.cursor.execute('INSERT OR IGNORE INTO likes (from_user_id, to_user_id) VALUES (?, ?)', (from_user[0], to_user[0]))
            
            if self.cursor.rowcount == 0:
                return False, "Лайк вже існує"
            
            # Оновлюємо кількість лайків
            self.cursor.execute('UPDATE users SET likes_count = likes_count + 1 WHERE id = ?', (to_user[0],))
            
            # ОНОВЛЮЄМО РЕЙТИНГ отримувача лайка
            self.update_rating_on_like(to_user_id)
            
            # Оновлюємо щоденний лічильник лайків
            today = datetime.now().date()
            self.cursor.execute('''
                UPDATE daily_likes 
                SET likes_given = likes_given + 1 
                WHERE user_id = ? AND date = ?
            ''', (from_user[0], today))
            
            self.conn.commit()
            return True, "Лайк успішно додано"
            
        except Exception as e:
            print(f"❌ Помилка додавання лайку: {e}")
            return False, f"Помилка: {e}"
    
    def get_user_matches(self, telegram_id):
        """Отримання матчів користувача"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            if not user:
                return []
            
            self.cursor.execute('''
                SELECT u.* FROM users u
                JOIN likes l1 ON u.id = l1.to_user_id
                JOIN likes l2 ON u.id = l2.from_user_id
                WHERE l1.from_user_id = ? AND l2.to_user_id = ? AND u.id != ?
            ''', (user[0], user[0], user[0]))
            
            matches = self.cursor.fetchall()
            return matches
        except Exception as e:
            print(f"❌ Помилка отримання матчів: {e}")
            return []
    
    def get_top_users_by_rating(self, limit=10, gender=None):
        """Топ користувачів по рейтингу"""
        try:
            query = '''
                SELECT * FROM users 
                WHERE is_banned = FALSE AND age IS NOT NULL 
                AND has_photo = TRUE AND rating IS NOT NULL
            '''
        
            params = []
            if gender:
                query += ' AND gender = ?'
                params.append(gender)
        
            query += ' ORDER BY rating DESC, likes_count DESC LIMIT ?'
            params.append(limit)
        
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
        
            print(f"🔍 [RATING] Знайдено користувачів: {len(users)}")
            return users
        except Exception as e:
            print(f"❌ Помилка отримання топу по рейтингу: {e}")
            return []

    def get_user_likers(self, telegram_id):
        """Отримати список користувачів, які лайкнули поточного користувача"""
        try:
            self.cursor.execute('''
                SELECT u.* FROM users u
                JOIN likes l ON u.id = l.from_user_id
                JOIN users target ON target.id = l.to_user_id
                WHERE target.telegram_id = ? AND u.telegram_id != ?
            ''', (telegram_id, telegram_id))
            
            likers = self.cursor.fetchall()
            return likers
        except Exception as e:
            print(f"❌ Помилка отримання лайкерів: {e}")
            return []
    
    def has_liked(self, from_user_id, to_user_id):
        """Перевірити чи поставив користувач лайк іншому користувачу"""
        try:
            self.cursor.execute('''
                SELECT l.id FROM likes l
                JOIN users u1 ON u1.id = l.from_user_id
                JOIN users u2 ON u2.id = l.to_user_id
                WHERE u1.telegram_id = ? AND u2.telegram_id = ?
            ''', (from_user_id, to_user_id))
            
            result = self.cursor.fetchone()
            return result is not None
        except Exception as e:
            print(f"❌ Помилка перевірки лайку: {e}")
            return False

    def add_profile_view(self, viewer_id, viewed_user_id):
        """Додати запис про перегляд профілю"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (viewer_id,))
            viewer = self.cursor.fetchone()
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (viewed_user_id,))
            viewed = self.cursor.fetchone()
            
            if viewer and viewed:
                self.cursor.execute('''
                    INSERT INTO profile_views (viewer_id, viewed_user_id)
                    VALUES (?, ?)
                ''', (viewer[0], viewed[0]))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"❌ Помилка додавання перегляду: {e}")
        return False

    def get_daily_likes_info(self, telegram_id):
        """Отримати інформацію про щоденні лайки користувача"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            if not user:
                return 0, 50
            
            today = datetime.now().date()
            self.cursor.execute('''
                SELECT likes_given FROM daily_likes 
                WHERE user_id = ? AND date = ?
            ''', (user[0], today))
            
            result = self.cursor.fetchone()
            likes_today = result[0] if result else 0
            
            return likes_today, 50  # Поточні лайки і ліміт
            
        except Exception as e:
            print(f"❌ Помилка отримання інформації про лайки: {e}")
            return 0, 50

    # АДМІН-ФУНКЦІЇ
    def get_statistics(self):
        """Отримання статистики"""
        try:
            # Статистика за статтю
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = ? AND age IS NOT NULL', ('male',))
            male = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = ? AND age IS NOT NULL', ('female',))
            female = self.cursor.fetchone()[0]
            
            # Активні анкети
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND has_photo = TRUE')
            total_active = self.cursor.fetchone()[0]
            
            # Статистика за цілями
            self.cursor.execute('SELECT goal, COUNT(*) FROM users WHERE goal IS NOT NULL GROUP BY goal')
            goals_stats = self.cursor.fetchall()
            
            return male, female, total_active, goals_stats
        except Exception as e:
            print(f"❌ Помилка отримання статистики: {e}")
            return 0, 0, 0, []

    def get_users_count(self):
        """Отримання загальної кількості користувачів"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"❌ Помилка отримання кількості користувачів: {e}")
            return 0

    def get_all_users(self):
        """Отримання всіх користувачів"""
        try:
            self.cursor.execute('SELECT telegram_id FROM users')
            users = self.cursor.fetchall()
            return [user[0] for user in users]
        except Exception as e:
            print(f"❌ Помилка отримання користувачів: {e}")
            return []

    def get_banned_users(self):
        """Отримання заблокованих користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE is_banned = TRUE')
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ Помилка отримання заблокованих: {e}")
            return []

    def get_all_active_users(self, exclude_user_id):
        """Отримання всіх активних користувачів"""
        try:
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE age IS NOT NULL AND has_photo = TRUE AND is_banned = FALSE
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ Помилка отримання активних користувачів: {e}")
            return []

    def search_users_advanced(self, user_id, gender, city, goal):
        """Розширений пошук користувачів з урахуванням рейтингу"""
        try:
            query = '''
                SELECT * FROM users 
                WHERE telegram_id != ? AND age IS NOT NULL 
                AND has_photo = TRUE AND is_banned = FALSE
                AND rating IS NOT NULL
            '''
            params = [user_id]
            
            if gender != 'all':
                query += ' AND gender = ?'
                params.append(gender)
            
            if city:
                query += ' AND city LIKE ?'
                params.append(f'%{city}%')
            
            if goal:
                query += ' AND goal = ?'
                params.append(goal)
            
            # Сортуємо по рейтингу
            query += ' ORDER BY rating DESC, RANDOM() LIMIT 20'
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"❌ Помилка розширеного пошуку: {e}")
            return []

    def cleanup_old_data(self):
        """Очищення старих даних"""
        try:
            # Видаляємо користувачів без профілю (старше 30 днів)
            self.cursor.execute('''
                DELETE FROM users 
                WHERE age IS NULL AND created_at < datetime('now', '-30 days')
            ''')
            
            # Видаляємо старі лайки (старше 90 днів)
            self.cursor.execute('''
                DELETE FROM likes 
                WHERE created_at < datetime('now', '-90 days')
            ''')
            
            # Видаляємо старі записи щоденних лайків (старше 7 днів)
            self.cursor.execute('''
                DELETE FROM daily_likes 
                WHERE date < date('now', '-7 days')
            ''')
            
            self.conn.commit()
            print("✅ Старі дані очищено")
            return True
        except Exception as e:
            print(f"❌ Помилка очищення даних: {e}")
            return False

    def ban_user(self, telegram_id):
        """Заблокувати користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = TRUE WHERE telegram_id = ?', (telegram_id,))
            self.conn.commit()
            print(f"✅ Користувач {telegram_id} заблокований")
            return True
        except Exception as e:
            print(f"❌ Помилка блокування користувача {telegram_id}: {e}")
            return False

    def unban_user(self, telegram_id):
        """Розблокувати користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE telegram_id = ?', (telegram_id,))
            self.conn.commit()
            print(f"✅ Користувач {telegram_id} розблокований")
            return True
        except Exception as e:
            print(f"❌ Помилка розблокування користувача {telegram_id}: {e}")
            return False

    def unban_all_users(self):
        """Розблокувати всіх користувачів"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE is_banned = TRUE')
            self.conn.commit()
            print("✅ Всі користувачі розблоковані")
            return True
        except Exception as e:
            print(f"❌ Помилка розблокування всіх користувачів: {e}")
            return False

    def search_user(self, query):
        """Пошук користувача за ID або іменем"""
        try:
            # Спробуємо знайти за ID (число)
            try:
                user_id = int(query)
                self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (user_id,))
                result_by_id = self.cursor.fetchall()
                if result_by_id:
                    return result_by_id
            except ValueError:
                pass  # Якщо не число, шукаємо за іменем
            
            # Пошук за іменем або username
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE first_name LIKE ? OR username LIKE ?
            ''', (f'%{query}%', f'%{query}%'))
            
            results = self.cursor.fetchall()
            return results
        except Exception as e:
            print(f"❌ Помилка пошуку користувача: {e}")
            return []
    
    def get_user_by_id(self, telegram_id):
        """Отримати користувача за telegram_id"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            if user:
                return dict(user)
            return None
        except Exception as e:
            print(f"❌ Помилка отримання користувача: {e}")
            return None

    def update_user_name(self, telegram_id, first_name):
        """Оновити ім'я користувача"""
        try:
            self.cursor.execute('''
                UPDATE users SET first_name = ? WHERE telegram_id = ?
            ''', (first_name, telegram_id))
            self.conn.commit()
            print(f"✅ Ім'я оновлено для {telegram_id}: {first_name}")
            return True
        except Exception as e:
            print(f"❌ Помилка оновлення імені: {e}")
            return False

# Глобальний об'єкт бази даних
db = Database()