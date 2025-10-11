import sqlite3
import os
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

# Шлях до бази даних
DATABASE_PATH = 'dating_bot.db'

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.init_db()
        self.update_database_structure()

    def init_db(self):
        """Ініціалізація бази даних з правильними стовпцями"""
        logger.info("🔄 Ініціалізація бази даних...")

        # Таблиця користувачів - ОНОВЛЕНА СТРУКТУРА
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
                rating REAL DEFAULT 5.0,
                daily_likes_count INTEGER DEFAULT 0,
                last_like_date DATE,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # Таблиця матчів
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user1_id) REFERENCES users (id),
                FOREIGN KEY (user2_id) REFERENCES users (id),
                UNIQUE(user1_id, user2_id)
            )
        ''')
        
        # Таблиця для відстеження переглядів профілю
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
        logger.info("✅ База даних ініціалізована")
    
    def update_database_structure(self):
        """Оновлення структури бази даних - ВИПРАВЛЕНА ВЕРСІЯ"""
        try:
            logger.info("🔄 Перевірка структури бази даних...")
            
            # Перевіряємо чи є стовпець first_name
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            logger.info(f"🔍 Наявні стовпці: {columns}")
            
            changes_made = False
            
            # Додаємо відсутні стовпці без DEFAULT значень спочатку
            if 'first_name' not in columns:
                logger.info("➕ Додаємо стовпець first_name...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN first_name TEXT')
                changes_made = True
            
            if 'last_active' not in columns:
                logger.info("➕ Додаємо стовпець last_active...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN last_active TIMESTAMP')
                changes_made = True
            
            if 'rating' not in columns:
                logger.info("➕ Додаємо стовпець rating...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN rating REAL')
                changes_made = True
            
            if 'daily_likes_count' not in columns:
                logger.info("➕ Додаємо стовпець daily_likes_count...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN daily_likes_count INTEGER')
                changes_made = True
            
            if 'last_like_date' not in columns:
                logger.info("➕ Додаємо стовпець last_like_date...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN last_like_date DATE')
                changes_made = True
            
            if changes_made:
                self.conn.commit()
                logger.info("✅ Структура бази даних оновлена")
                
                # Тепер оновлюємо значення для нових стовпців
                self.initialize_new_columns()
            else:
                logger.info("✅ Структура бази даних вже актуальна")
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення структури БД: {e}")

    def initialize_new_columns(self):
        """Ініціалізація значень для нових стовпців"""
        try:
            logger.info("🔄 Ініціалізація значень для нових стовпців...")
            
            # Оновлюємо first_name для існуючих користувачів
            self.cursor.execute('UPDATE users SET first_name = "Користувач" WHERE first_name IS NULL')
            
            # Оновлюємо last_active для існуючих користувачів
            self.cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE last_active IS NULL')
            
            # Оновлюємо rating для існуючих користувачів
            self.cursor.execute('UPDATE users SET rating = 5.0 WHERE rating IS NULL')
            
            # Оновлюємо daily_likes_count для існуючих користувачів
            self.cursor.execute('UPDATE users SET daily_likes_count = 0 WHERE daily_likes_count IS NULL')
            
            self.conn.commit()
            logger.info("✅ Значення для нових стовпців ініціалізовані")
            
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації стовпців: {e}")

    def add_user(self, telegram_id, username, first_name):
        """Додавання нового користувача"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO users (telegram_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (telegram_id, username, first_name))
            self.conn.commit()
            logger.info(f"✅ Користувач доданий/оновлений: {telegram_id} - {first_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка додавання користувача: {e}")
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
            logger.error(f"❌ Помилка отримання користувача: {e}")
            return None
    
    def update_user_profile(self, telegram_id, age, gender, city, seeking_gender, goal, bio):
        """Оновлення профілю користувача"""
        try:
            logger.info(f"🔄 Оновлення профілю для {telegram_id}")
            
            self.cursor.execute('''
                UPDATE users 
                SET age = ?, gender = ?, city = ?, seeking_gender = ?, goal = ?, bio = ?, last_active = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (age, gender, city, seeking_gender, goal, bio, telegram_id))
            
            # Оновлюємо рейтинг
            self.update_user_rating(telegram_id)
            
            self.conn.commit()
            logger.info(f"✅ Профіль оновлено для {telegram_id}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Помилка оновлення профілю: {e}")
            return False
    
    def update_user_rating(self, telegram_id):
        """Оновлення рейтингу користувача"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                return
            
            # Проста формула рейтингу
            base_rating = 5.0
            bonus = 0.0
            
            # Бонус за фото
            if user.get('has_photo'):
                bonus += 1.0
            
            # Бонус за заповнений профіль
            if user.get('bio') and len(user.get('bio', '')) > 20:
                bonus += 1.0
            
            # Бонус за лайки
            likes_count = user.get('likes_count', 0)
            bonus += min(likes_count * 0.1, 3.0)  # Макс +3 за лайки
            
            new_rating = min(base_rating + bonus, 10.0)
            
            self.cursor.execute('UPDATE users SET rating = ? WHERE telegram_id = ?', (new_rating, telegram_id))
            logger.info(f"✅ Рейтинг оновлено для {telegram_id}: {new_rating}")
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення рейтингу: {e}")
    
    def add_profile_photo(self, telegram_id, file_id):
        """Додавання фото до профілю"""
        try:
            logger.info(f"🔄 Додаємо фото для {telegram_id}")
            
            # Отримаємо user_id
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено")
                return False
            
            user_id = user[0]
            
            # Перевіряємо кількість фото
            current_photos = self.get_profile_photos(telegram_id)
            if len(current_photos) >= 3:
                logger.error("❌ Досягнуто ліміт фото (максимум 3)")
                return False
            
            # Додаємо фото
            self.cursor.execute('INSERT INTO photos (user_id, file_id) VALUES (?, ?)', (user_id, file_id))
            
            # Встановлюємо, що користувач має фото
            self.cursor.execute('UPDATE users SET has_photo = TRUE WHERE telegram_id = ?', (telegram_id,))
            
            # Оновлюємо рейтинг
            self.update_user_rating(telegram_id)
            
            self.conn.commit()
            logger.info("✅ Фото успішно додано до бази даних!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання фото: {e}")
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
            logger.error(f"❌ Помилка отримання фото: {e}")
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
            logger.error(f"❌ Помилка отримання фото: {e}")
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
            logger.error(f"❌ Помилка отримання профілю: {e}")
            return None, False
    
    def get_random_user(self, current_user_id, city=None):
        """Отримання випадкового користувача для пошуку - ВИПРАВЛЕНА ВЕРСІЯ"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                logger.error(f"❌ Поточного користувача {current_user_id} не знайдено")
                return None
            
            # ДЕТАЛЬНА ВІДЛАДКА
            logger.info(f"🔍 [SEARCH DEBUG] Пошук для: {current_user_id}")
            logger.info(f"🔍 [SEARCH DEBUG] Поточний користувач: {current_user}")
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            current_gender = current_user.get('gender')
            
            logger.info(f"🔍 [SEARCH DEBUG] Стать поточного: {current_gender}, шукає: {seeking_gender}")
            
            query = '''
                SELECT u.* FROM users u
                WHERE u.telegram_id != ? AND u.age IS NOT NULL 
                AND u.has_photo = TRUE AND u.is_banned = FALSE
            '''
            params = [current_user_id]
            
            # ВИПРАВЛЕНА ЛОГІКА ПОШУКУ ЗА СТАТТЮ
            if seeking_gender != 'all':
                query += ' AND u.gender = ?'
                params.append(seeking_gender)
                logger.info(f"🔍 [SEARCH DEBUG] Фільтр за статтю: {seeking_gender}")
            else:
                logger.info(f"🔍 [SEARCH DEBUG] Шукає всі статі")
            
            if city:
                query += ' AND u.city LIKE ?'
                params.append(f'%{city}%')
                logger.info(f"🔍 [SEARCH DEBUG] Фільтр за містом: {city}")
            
            query += ' ORDER BY RANDOM() LIMIT 1'
            
            logger.info(f"🔍 [SEARCH DEBUG] SQL: {query}")
            logger.info(f"🔍 [SEARCH DEBUG] Параметри: {params}")
            
            self.cursor.execute(query, params)
            user = self.cursor.fetchone()
            
            if user:
                logger.info(f"🔍 [SEARCH DEBUG] Знайдено користувача: ID {user[1]}, стать {user[5]}")
            else:
                logger.info(f"🔍 [SEARCH DEBUG] Користувачів не знайдено")
                
            return user
        except Exception as e:
            logger.error(f"❌ Помилка отримання випадкового користувача: {e}")
            return None
    
    def get_users_by_city(self, city, current_user_id):
        """Отримання користувачів за містом"""
        try:
            logger.info(f"🔍 Пошук у місті: '{city}' для користувача {current_user_id}")
            
            current_user = self.get_user(current_user_id)
            if not current_user:
                logger.error("❌ Поточного користувача не знайдено")
                return []
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            logger.info(f"🔍 Шукає стать: {seeking_gender}")
            
            # Видаляємо емодзі з назви міста
            clean_city = city.replace('🏙️ ', '').strip()
            
            query = '''
                SELECT u.* FROM users u
                WHERE u.telegram_id != ? AND u.city LIKE ? 
                AND u.age IS NOT NULL AND u.has_photo = TRUE AND u.is_banned = FALSE
            '''
            params = [current_user_id, f'%{clean_city}%']
            
            if seeking_gender != 'all':
                query += ' AND u.gender = ?'
                params.append(seeking_gender)
            
            query += ' ORDER BY RANDOM() LIMIT 20'
            
            logger.info(f"🔍 SQL запит: {query}")
            logger.info(f"🔍 Параметри: {params}")
            
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
            logger.info(f"🔍 Знайдено користувачів: {len(users)}")
            return users
        except Exception as e:
            logger.error(f"❌ Помилка пошуку за містом: {e}")
            return []
    
    def get_likes_count(self, user_id):
        """Отримання кількості лайків"""
        try:
            self.cursor.execute('SELECT likes_count FROM users WHERE telegram_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ Помилка отримання лайків: {e}")
            return 0
    
    def can_like_today(self, user_id):
        """Перевірка чи може користувач ставити лайки сьогодні"""
        try:
            user = self.get_user(user_id)
            if not user:
                return False, "Користувача не знайдено"
            
            today = date.today()
            last_like_date = user.get('last_like_date')
            daily_likes = user.get('daily_likes_count', 0)
            
            # Якщо останній лайк був не сьогодні - скидаємо лічильник
            if last_like_date != today:
                self.cursor.execute(
                    'UPDATE users SET daily_likes_count = 0, last_like_date = ? WHERE telegram_id = ?',
                    (today, user_id)
                )
                self.conn.commit()
                return True, "Можна ставити лайки"
            
            # Перевіряємо ліміт
            if daily_likes >= 50:
                return False, "Досягнуто денний ліміт лайків (50)"
            
            return True, f"Залишилось лайків: {50 - daily_likes}"
            
        except Exception as e:
            logger.error(f"❌ Помилка перевірки лайків: {e}")
            return False, "Помилка перевірки"
    
    def add_like(self, from_user_id, to_user_id):
        """Додавання лайку з перевіркою обмежень"""
        try:
            # Перевіряємо чи може користувач ставити лайки
            can_like, message = self.can_like_today(from_user_id)
            if not can_like:
                return False, message
            
            # Перевіряємо чи вже ставив лайк
            if self.has_liked(from_user_id, to_user_id):
                return False, "Ви вже лайкали цього користувача"
            
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (from_user_id,))
            from_user = self.cursor.fetchone()
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (to_user_id,))
            to_user = self.cursor.fetchone()
            
            if not from_user or not to_user:
                return False, "Користувача не знайдено"
            
            # Додаємо лайк
            self.cursor.execute('INSERT OR IGNORE INTO likes (from_user_id, to_user_id) VALUES (?, ?)', (from_user[0], to_user[0]))
            
            # Оновлюємо кількість лайків
            self.cursor.execute('UPDATE users SET likes_count = likes_count + 1 WHERE id = ?', (to_user[0],))
            
            # Оновлюємо денний лічильник лайків
            today = date.today()
            self.cursor.execute(
                'UPDATE users SET daily_likes_count = daily_likes_count + 1, last_like_date = ? WHERE telegram_id = ?',
                (today, from_user_id)
            )
            
            # Оновлюємо рейтинг
            self.update_user_rating(to_user_id)
            
            self.conn.commit()
            
            # Перевіряємо чи це взаємний лайк
            is_mutual = self.has_liked(to_user_id, from_user_id)
            
            if is_mutual:
                # Створюємо матч
                self.cursor.execute('''
                    INSERT OR IGNORE INTO matches (user1_id, user2_id)
                    VALUES (?, ?)
                ''', (min(from_user_id, to_user_id), max(from_user_id, to_user_id)))
                self.conn.commit()
            
            return True, "Лайк додано" if not is_mutual else "Лайк додано! 💕 У вас матч!"
            
        except Exception as e:
            logger.error(f"❌ Помилка додавання лайку: {e}")
            return False, "Помилка додавання лайку"
    
    def get_user_matches(self, telegram_id):
        """Отримання матчів користувача"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            if not user:
                return []
            
            self.cursor.execute('''
                SELECT DISTINCT u.* FROM users u
                JOIN matches m ON (u.telegram_id = m.user1_id OR u.telegram_id = m.user2_id)
                WHERE (m.user1_id = ? OR m.user2_id = ?) AND u.telegram_id != ?
            ''', (telegram_id, telegram_id, telegram_id))
            
            matches = self.cursor.fetchall()
            return matches
        except Exception as e:
            logger.error(f"❌ Помилка отримання матчів: {e}")
            return []
    
    def get_top_users_by_rating(self, limit=10, gender=None):
        """Отримання топу користувачів за рейтингом"""
        try:
            query = '''
                SELECT * FROM users 
                WHERE is_banned = FALSE AND age IS NOT NULL AND has_photo = TRUE
            '''
            params = []
            
            if gender:
                query += ' AND gender = ?'
                params.append(gender)
                
            query += ' ORDER BY rating DESC, likes_count DESC LIMIT ?'
            params.append(limit)
            
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
            
            logger.info(f"🔍 [TOP] Знайдено {len(users)} користувачів для топу")
            return users
        except Exception as e:
            logger.error(f"❌ Помилка отримання топу за рейтингом: {e}")
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
            logger.error(f"❌ Помилка отримання лайкерів: {e}")
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
            logger.error(f"❌ Помилка перевірки лайку: {e}")
            return False

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
            logger.error(f"❌ Помилка отримання статистики: {e}")
            return 0, 0, 0, []

    def get_users_count(self):
        """Отримання загальної кількості користувачів"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ Помилка отримання кількості користувачів: {e}")
            return 0

    def get_all_users(self):
        """Отримання всіх користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            users = self.cursor.fetchall()
            return users
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувачів: {e}")
            return []

    def get_banned_users(self):
        """Отримання заблокованих користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE is_banned = TRUE')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання заблокованих: {e}")
            return []

    def get_all_active_users(self, exclude_user_id=None):
        """Отримання всіх активних користувачів"""
        try:
            if exclude_user_id:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL AND has_photo = TRUE AND is_banned = FALSE AND telegram_id != ?
                    ORDER BY last_active DESC
                ''', (exclude_user_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM users 
                    WHERE age IS NOT NULL AND has_photo = TRUE AND is_banned = FALSE
                    ORDER BY last_active DESC
                ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання активних користувачів: {e}")
            return []

    def search_users_advanced(self, user_id, gender, city, goal):
        """Розширений пошук користувачів"""
        try:
            query = '''
                SELECT * FROM users 
                WHERE telegram_id != ? AND age IS NOT NULL 
                AND has_photo = TRUE AND is_banned = FALSE
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
            
            query += ' ORDER BY RANDOM() LIMIT 20'
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка розширеного пошуку: {e}")
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
            
            self.conn.commit()
            logger.info("✅ Старі дані очищено")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка очищення даних: {e}")
            return False

    def ban_user(self, telegram_id):
        """Заблокувати користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = TRUE WHERE telegram_id = ?', (telegram_id,))
            self.conn.commit()
            logger.info(f"✅ Користувач {telegram_id} заблокований")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка блокування користувача {telegram_id}: {e}")
            return False

    def unban_user(self, telegram_id):
        """Розблокувати користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE telegram_id = ?', (telegram_id,))
            self.conn.commit()
            logger.info(f"✅ Користувач {telegram_id} розблокований")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка розблокування користувача {telegram_id}: {e}")
            return False

    def unban_all_users(self):
        """Розблокувати всіх користувачів"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE is_banned = TRUE')
            self.conn.commit()
            logger.info("✅ Всі користувачі розблоковані")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка розблокування всіх користувачів: {e}")
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
                pass  # Якщо не число, шукаємо за імені
            
            # Пошук за іменем або username
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE first_name LIKE ? OR username LIKE ?
                ORDER BY created_at DESC
            ''', (f'%{query}%', f'%{query}%'))
            
            results = self.cursor.fetchall()
            return results
        except Exception as e:
            logger.error(f"❌ Помилка пошуку користувача: {e}")
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
            logger.error(f"❌ Помилка отримання користувача: {e}")
            return None

    def update_user_name(self, telegram_id, first_name):
        """Оновити ім'я користувача"""
        try:
            self.cursor.execute('''
                UPDATE users SET first_name = ? WHERE telegram_id = ?
            ''', (first_name, telegram_id))
            self.conn.commit()
            logger.info(f"✅ Ім'я оновлено для {telegram_id}: {first_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка оновлення імені: {e}")
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
            logger.error(f"❌ Помилка додавання перегляду: {e}")
        return False

    def debug_user_profile(self, telegram_id):
        """Відладка профілю користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            
            if user:
                logger.info(f"🔍 [DEBUG USER] ID: {user[1]}")
                logger.info(f"🔍 [DEBUG USER] Ім'я: {user[3]}")
                logger.info(f"🔍 [DEBUG USER] Вік: {user[4]}")
                logger.info(f"🔍 [DEBUG USER] Стать: {user[5]}")
                logger.info(f"🔍 [DEBUG USER] Місто: {user[6]}")
                logger.info(f"🔍 [DEBUG USER] Фото: {user[10]}")
                logger.info(f"🔍 [DEBUG USER] Лайків: {user[12]}")
                logger.info(f"🔍 [DEBUG USER] Рейтинг: {user[14]}")
                logger.info(f"🔍 [DEBUG USER] Заблокований: {user[13]}")
                return True
            else:
                logger.info(f"🔍 [DEBUG USER] Користувача {telegram_id} не знайдено")
                return False
        except Exception as e:
            logger.error(f"❌ Помилка відладки: {e}")
            return False

    def calculate_user_rating(self, user_id):
        """Розрахунок рейтингу користувача - ВИПРАВЛЕНА ВЕРСІЯ"""
        try:
            user = self.get_user(user_id)
            if not user:
                return 5.0
            
            base_rating = 5.0
            bonus = 0.0
            
            # Бонус за наявність фото
            if user.get('has_photo'):
                bonus += 1.0
            
            # Бонус за заповнений профіль
            if user.get('bio') and len(user.get('bio', '')) > 20:
                bonus += 1.0
            
            # Бонус за кількість лайків
            likes_count = user.get('likes_count', 0)
            bonus += min(likes_count * 0.1, 3.0)  # Максимум +3 за лайки
            
            # Бонус за активність (остання активність)
            if user.get('last_active'):
                try:
                    last_active = datetime.fromisoformat(user['last_active'].replace('Z', '+00:00'))
                    days_since_active = (datetime.now() - last_active).days
                    if days_since_active <= 7:  # Активність за останні 7 днів
                        bonus += 0.5
                except Exception as e:
                    logger.error(f"❌ Помилка обробки last_active: {e}")

            new_rating = min(base_rating + bonus, 10.0)
            
            # Оновлюємо рейтинг в базі
            self.cursor.execute('UPDATE users SET rating = ? WHERE telegram_id = ?', (new_rating, user_id))
            self.conn.commit()
            
            logger.info(f"✅ Рейтинг розраховано для {user_id}: {new_rating}")
            return new_rating
            
        except Exception as e:
            logger.error(f"❌ Помилка розрахунку рейтингу: {e}")
            return 5.0

# Глобальний об'єкт бази даних
db = Database()