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
        
        # Перевіряємо чи потрібно скинути БД
        if self.needs_reset():
            logger.info("🔄 Виявлено проблеми з БД, виконуємо автоматичне скидання...")
            self.force_reset_database()
        else:
            self.init_db()
            self.update_database_structure()

    def needs_reset(self):
        """Перевіряє чи потрібно скинути БД"""
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            users_exists = self.cursor.fetchone() is not None
            
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='likes'")
            likes_exists = self.cursor.fetchone() is not None
            
            # Якщо немає таблиць або структура пошкоджена
            if not users_exists or not likes_exists:
                return True
                
            # Перевіряємо структуру таблиці users
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in self.cursor.fetchall()]
            required_columns = ['telegram_id', 'first_name', 'gender', 'seeking_gender']
            
            for col in required_columns:
                if col not in columns:
                    logger.warning(f"❌ Відсутній обов'язковий стовпець: {col}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"❌ Помилка перевірки БД: {e}")
            return True

    def force_reset_database(self):
        """Примусове скидання бази даних"""
        try:
            logger.info("🔄 Примусове скидання бази даних...")
            
            # Закриваємо з'єднання
            self.conn.close()
            
            # Видаляємо файл БД
            if os.path.exists(DATABASE_PATH):
                os.remove(DATABASE_PATH)
                logger.info("✅ Файл БД видалено")
            
            # Перестворюємо з'єднання
            self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
            # Ініціалізуємо БД
            self.init_db()
            logger.info("✅ База даних повністю скинута та перестворена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка скидання БД: {e}")
            # Спробуємо створити нову БД навіть якщо видалення не вдалося
            try:
                self.init_db()
                return True
            except:
                return False

    def reset_database(self):
        """Скидання бази даних через адмінку"""
        return self.force_reset_database()

    def init_db(self):
        """Ініціалізація бази даних з правильними стовпцями"""
        logger.info("🔄 Ініціалізація бази даних...")

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
                seeking_gender TEXT DEFAULT 'all',
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
        """Оновлення структури бази даних"""
        try:
            logger.info("🔄 Перевірка структури бази даних...")
            
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            logger.info(f"🔍 Наявні стовпці: {columns}")
            
            changes_made = False
            
            # Перевіряємо та додаємо відсутні стовпці
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
            
            if 'seeking_gender' not in columns:
                logger.info("➕ Додаємо стовпець seeking_gender...")
                self.cursor.execute('ALTER TABLE users ADD COLUMN seeking_gender TEXT DEFAULT "all"')
                changes_made = True
            
            if changes_made:
                self.conn.commit()
                logger.info("✅ Структура бази даних оновлена")
                self.initialize_new_columns()
            else:
                logger.info("✅ Структура бази даних вже актуальна")
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення структури БД: {e}")

    def initialize_new_columns(self):
        """Ініціалізація значень для нових стовпців"""
        try:
            logger.info("🔄 Ініціалізація значень для нових стовпців...")
            
            self.cursor.execute('UPDATE users SET first_name = "Користувач" WHERE first_name IS NULL')
            self.cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE last_active IS NULL')
            self.cursor.execute('UPDATE users SET rating = 5.0 WHERE rating IS NULL')
            self.cursor.execute('UPDATE users SET daily_likes_count = 0 WHERE daily_likes_count IS NULL')
            self.cursor.execute('UPDATE users SET seeking_gender = "all" WHERE seeking_gender IS NULL')
            
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
            logger.info(f"🔄 Дані для оновлення: вік={age}, стать={gender}, місто={city}, шукає={seeking_gender}, ціль={goal}")
            
            self.cursor.execute('''
                UPDATE users 
                SET age = ?, gender = ?, city = ?, seeking_gender = ?, goal = ?, bio = ?, last_active = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (age, gender, city, seeking_gender, goal, bio, telegram_id))
            
            # Оновлюємо рейтинг
            self.update_user_rating(telegram_id)
            
            self.conn.commit()
            
            # Перевіряємо оновлені дані
            self.cursor.execute('SELECT age, gender, city, seeking_gender, goal FROM users WHERE telegram_id = ?', (telegram_id,))
            updated_data = self.cursor.fetchone()
            logger.info(f"✅ Профіль оновлено для {telegram_id}. Перевірка: {updated_data}")
            
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
            
            base_rating = 5.0
            bonus = 0.0
            
            if user.get('has_photo'):
                bonus += 1.0
            
            if user.get('bio') and len(user.get('bio', '')) > 20:
                bonus += 1.0
            
            likes_count = user.get('likes_count', 0)
            bonus += min(likes_count * 0.1, 3.0)
            
            new_rating = min(base_rating + bonus, 10.0)
            
            self.cursor.execute('UPDATE users SET rating = ? WHERE telegram_id = ?', (new_rating, telegram_id))
            logger.info(f"✅ Рейтинг оновлено для {telegram_id}: {new_rating}")
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення рейтингу: {e}")
    
    def add_profile_photo(self, telegram_id, file_id):
        """Додавання фото до профілю"""
        try:
            logger.info(f"🔄 Додаємо фото для {telegram_id}")
            
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено")
                return False
            
            user_id = user[0]
            
            current_photos = self.get_profile_photos(telegram_id)
            if len(current_photos) >= 3:
                logger.error("❌ Досягнуто ліміт фото (максимум 3)")
                return False
            
            self.cursor.execute('INSERT INTO photos (user_id, file_id) VALUES (?, ?)', (user_id, file_id))
            self.cursor.execute('UPDATE users SET has_photo = TRUE WHERE telegram_id = ?', (telegram_id,))
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
        """Отримання випадкового користувача для пошуку"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                logger.error(f"❌ Поточного користувача {current_user_id} не знайдено")
                return None
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            current_gender = current_user.get('gender')
            
            query = '''
                SELECT u.* FROM users u
                WHERE u.telegram_id != ? AND u.age IS NOT NULL 
                AND u.has_photo = TRUE AND u.is_banned = FALSE
            '''
            params = [current_user_id]
            
            if seeking_gender != 'all':
                query += ' AND u.gender = ?'
                params.append(seeking_gender)
            
            if city:
                query += ' AND u.city LIKE ?'
                params.append(f'%{city}%')
            
            # Виключаємо вже лайкнутих користувачів
            query += ' AND u.telegram_id NOT IN (SELECT u2.telegram_id FROM users u2 JOIN likes l ON u2.id = l.to_user_id JOIN users u3 ON u3.id = l.from_user_id WHERE u3.telegram_id = ?)'
            params.append(current_user_id)
            
            query += ' ORDER BY RANDOM() LIMIT 1'
            
            self.cursor.execute(query, params)
            user = self.cursor.fetchone()
            
            return user
        except Exception as e:
            logger.error(f"❌ Помилка отримання випадкового користувача: {e}")
            return None
    
    def get_users_by_city(self, city, current_user_id):
        """Отримання користувачів за містом"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                return []
            
            seeking_gender = current_user.get('seeking_gender', 'all')
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
            
            # Виключаємо вже лайкнутих користувачів
            query += ' AND u.telegram_id NOT IN (SELECT u2.telegram_id FROM users u2 JOIN likes l ON u2.id = l.to_user_id JOIN users u3 ON u3.id = l.from_user_id WHERE u3.telegram_id = ?)'
            params.append(current_user_id)
            
            query += ' ORDER BY RANDOM() LIMIT 20'
            
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
            
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
            
            if last_like_date != today:
                self.cursor.execute(
                    'UPDATE users SET daily_likes_count = 0, last_like_date = ? WHERE telegram_id = ?',
                    (today, user_id)
                )
                self.conn.commit()
                return True, "Можна ставити лайки"
            
            if daily_likes >= 50:
                return False, "Досягнуто денний ліміт лайків (50)"
            
            return True, f"Залишилось лайків: {50 - daily_likes}"
            
        except Exception as e:
            logger.error(f"❌ Помилка перевірки лайків: {e}")
            return False, "Помилка перевірки"
    
    def add_like(self, from_user_id, to_user_id):
        """Додавання лайку з перевіркою обмежень"""
        try:
            can_like, message = self.can_like_today(from_user_id)
            if not can_like:
                return False, message
            
            if self.has_liked(from_user_id, to_user_id):
                return False, "Ви вже лайкали цього користувача"
            
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (from_user_id,))
            from_user = self.cursor.fetchone()
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (to_user_id,))
            to_user = self.cursor.fetchone()
            
            if not from_user or not to_user:
                return False, "Користувача не знайдено"
            
            self.cursor.execute('INSERT OR IGNORE INTO likes (from_user_id, to_user_id) VALUES (?, ?)', (from_user[0], to_user[0]))
            self.cursor.execute('UPDATE users SET likes_count = likes_count + 1 WHERE id = ?', (to_user[0],))
            
            today = date.today()
            self.cursor.execute(
                'UPDATE users SET daily_likes_count = daily_likes_count + 1, last_like_date = ? WHERE telegram_id = ?',
                (today, from_user_id)
            )
            
            self.update_user_rating(to_user_id)
            
            self.conn.commit()
            
            is_mutual = self.has_liked(to_user_id, from_user_id)
            
            if is_mutual:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO matches (user1_id, user2_id)
                    VALUES (?, ?)
                ''', (min(from_user[0], to_user[0]), max(from_user[0], to_user[0])))
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
                JOIN matches m ON (u.id = m.user1_id OR u.id = m.user2_id)
                WHERE (m.user1_id = ? OR m.user2_id = ?) AND u.id != ?
            ''', (user[0], user[0], user[0]))
            
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
            
            return users
        except Exception as e:
            logger.error(f"❌ Помилка отримання топу за рейтингом: {e}")
            return []

    def get_user_likers(self, telegram_id):
        """Отримати список користувачів, які лайкнули поточного користувача"""
        try:
            self.cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            if not user:
                return []
            
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
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = ? AND age IS NOT NULL', ('male',))
            male = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = ? AND age IS NOT NULL', ('female',))
            female = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND has_photo = TRUE')
            total_active = self.cursor.fetchone()[0]
            
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
        """Очищення старих даних з детальним логуванням"""
        try:
            # Рахуємо кількість записів перед очищенням
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NULL AND created_at < datetime("now", "-30 days")')
            old_incomplete = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM likes WHERE created_at < datetime("now", "-90 days")')
            old_likes = self.cursor.fetchone()[0]
            
            # Виконуємо очищення
            self.cursor.execute('''
                DELETE FROM users 
                WHERE age IS NULL AND created_at < datetime('now', '-30 days')
            ''')
            
            self.cursor.execute('''
                DELETE FROM likes 
                WHERE created_at < datetime('now', '-90 days')
            ''')
            
            # Оновлюємо статистику рейтингів
            self.cursor.execute('SELECT telegram_id FROM users WHERE age IS NOT NULL')
            active_users = self.cursor.fetchall()
            
            for user in active_users:
                self.calculate_user_rating(user[0])
            
            self.conn.commit()
            
            logger.info(f"✅ Очищено старих даних: {old_incomplete} неповних профілів, {old_likes} лайків")
            logger.info(f"📊 Оновлено рейтинги для {len(active_users)} активних користувачів")
            
            return {
                'deleted_incomplete': old_incomplete,
                'deleted_likes': old_likes,
                'updated_ratings': len(active_users)
            }
            
        except Exception as e:
            logger.error(f"❌ Помилка очищення даних: {e}")
            return False

    def ban_user(self, telegram_id):
        """Заблокувати користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для блокування")
                return False
            
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
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            
            if not user:
                logger.error(f"❌ Користувача {telegram_id} не знайдено для розблокування")
                return False
            
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
            try:
                user_id = int(query)
                self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (user_id,))
                result_by_id = self.cursor.fetchall()
                if result_by_id:
                    return result_by_id
            except ValueError:
                pass
            
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
            logger.error(f"❌ Помилка отримання користувача за ID: {e}")
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

    def calculate_user_rating(self, telegram_id):
        """Розрахунок рейтингу користувача"""
        try:
            user = self.get_user(telegram_id)
            if not user:
                return 5.0
            
            base_rating = 5.0
            bonus = 0.0
            
            if user.get('has_photo'):
                bonus += 1.0
            
            if user.get('bio') and len(user.get('bio', '')) > 20:
                bonus += 1.0
            
            likes_count = user.get('likes_count', 0)
            bonus += min(likes_count * 0.1, 3.0)
            
            if user.get('last_active'):
                try:
                    last_active = datetime.fromisoformat(user['last_active'].replace('Z', '+00:00'))
                    days_since_active = (datetime.now() - last_active).days
                    if days_since_active <= 7:
                        bonus += 0.5
                except Exception as e:
                    logger.error(f"❌ Помилка обробки last_active: {e}")

            new_rating = min(base_rating + bonus, 10.0)
            
            self.cursor.execute('UPDATE users SET rating = ? WHERE telegram_id = ?', (new_rating, telegram_id))
            self.conn.commit()
            
            logger.info(f"✅ Рейтинг розраховано для {telegram_id}: {new_rating}")
            return new_rating
            
        except Exception as e:
            logger.error(f"❌ Помилка розрахунку рейтингу: {e}")
            return 5.0

# Глобальний об'єкт бази даних
db = Database()