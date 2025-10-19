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
            
            # Якщо немає однієї з основних таблиць - потрібно скинути
            if not users_exists or not likes_exists:
                logger.warning("❌ Відсутні основні таблиці БД")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"❌ Помилка перевірки БД: {e}")
            return True

    def init_db(self):
        """Ініціалізація бази даних (без скидання даних)"""
        try:
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
            logger.info("✅ База даних успішно ініціалізована")
            
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації БД: {e}")
            raise

    def update_database_structure(self):
        """Оновлення структури БД без втрати даних"""
        try:
            # Додаємо нові стовпці, якщо їх немає
            columns_to_add = [
                ('seeking_gender', 'TEXT DEFAULT "all"'),
                ('rating', 'REAL DEFAULT 5.0'),
                ('daily_likes_count', 'INTEGER DEFAULT 0'),
                ('last_like_date', 'DATE')
            ]
            
            for column_name, column_type in columns_to_add:
                try:
                    self.cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                    logger.info(f"✅ Додано стовпець {column_name}")
                except sqlite3.OperationalError:
                    # Стовпець вже існує
                    pass
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення структури БД: {e}")

    def force_reset_database(self):
        """Примусове скидання БД (використовується тільки при критичних помилках)"""
        try:
            # Закриваємо з'єднання
            self.conn.close()
            
            # Видаляємо файл БД
            if os.path.exists(DATABASE_PATH):
                os.remove(DATABASE_PATH)
                logger.info("🗑️ Стара БД видалена")
            
            # Перестворюємо з'єднання
            self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
            # Ініціалізуємо нову БД
            self.init_db()
            logger.info("🔄 БД успішно скинута та перестворена")
            
        except Exception as e:
            logger.error(f"❌ Помилка скидання БД: {e}")
            raise

    def reset_database(self):
        """Скидання БД (тільки для адміна)"""
        try:
            self.force_reset_database()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка скидання БД: {e}")
            return False

    def get_users_by_city(self, city, current_user_id):
        """Отримання користувачів за містом"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                return []
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            clean_city = city.replace('🏙️ ', '').strip()
            
            logger.info(f"🔍 [CITY SEARCH] Шукаємо в місті: '{clean_city}' для користувача {current_user_id}")
            logger.info(f"🔍 [CITY SEARCH] Шукає стать: {seeking_gender}")
            
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
            
            logger.info(f"🔍 [CITY SEARCH] Знайдено користувачів: {len(users)}")
            
            return users
        except Exception as e:
            logger.error(f"❌ Помилка пошуку за містом: {e}")
            return []

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

    def calculate_user_rating(self, user_id):
        """Розрахунок рейтингу користувача"""
        try:
            user = self.get_user(user_id)
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
            
            self.cursor.execute('UPDATE users SET rating = ? WHERE telegram_id = ?', (new_rating, user_id))
            self.conn.commit()
            
            logger.info(f"✅ Рейтинг розраховано для {user_id}: {new_rating}")
            return new_rating
            
        except Exception as e:
            logger.error(f"❌ Помилка розрахунку рейтингу: {e}")
            return 5.0

    # АДМІН МЕТОДИ
    def get_statistics(self):
        """Отримання статистики для адміна"""
        try:
            # Загальна кількість користувачів
            self.cursor.execute('SELECT COUNT(*) FROM users')
            total_users = self.cursor.fetchone()[0]
            
            # Кількість активних користувачів (з заповненим профілем)
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND has_photo = TRUE')
            active_users = self.cursor.fetchone()[0]
            
            # Кількість чоловіків та жінок
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = ?', ('male',))
            male_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE gender = ?', ('female',))
            female_count = self.cursor.fetchone()[0]
            
            # Статистика по цілях
            self.cursor.execute('SELECT goal, COUNT(*) FROM users WHERE goal IS NOT NULL GROUP BY goal')
            goals_stats = self.cursor.fetchall()
            
            return male_count, female_count, active_users, goals_stats
            
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики: {e}")
            return 0, 0, 0, []

    def get_users_count(self):
        """Отримати загальну кількість користувачів"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ Помилка отримання кількості користувачів: {e}")
            return 0

    def get_all_active_users(self, admin_id):
        """Отримати всіх активних користувачів (для адміна)"""
        try:
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE telegram_id != ? AND age IS NOT NULL 
                ORDER BY created_at DESC
            ''', (admin_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання списку користувачів: {e}")
            return []

    def get_all_users(self):
        """Отримати всіх користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання всіх користувачів: {e}")
            return []

    def search_user(self, search_query):
        """Пошук користувача за ID або іменем"""
        try:
            query = '''
                SELECT * FROM users 
                WHERE telegram_id = ? OR first_name LIKE ? OR username LIKE ?
                ORDER BY created_at DESC
            '''
            self.cursor.execute(query, (search_query, f'%{search_query}%', f'%{search_query}%'))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка пошуку користувача: {e}")
            return []

    def get_banned_users(self):
        """Отримати список заблокованих користувачів"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE is_banned = TRUE ORDER BY created_at DESC')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Помилка отримання заблокованих користувачів: {e}")
            return []

    def ban_user(self, user_id):
        """Заблокувати користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = TRUE WHERE telegram_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка блокування користувача: {e}")
            return False

    def unban_user(self, user_id):
        """Розблокувати користувача"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = FALSE WHERE telegram_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка розблокування користувача: {e}")
            return False

    def cleanup_old_data(self):
        """Очищення старих даних"""
        try:
            # Видаляємо користувачів без активності більше 30 днів
            self.cursor.execute('''
                DELETE FROM users 
                WHERE last_active < datetime('now', '-30 days') 
                AND age IS NULL
            ''')
            
            # Видаляємо старі фото
            self.cursor.execute('''
                DELETE FROM photos 
                WHERE user_id NOT IN (SELECT id FROM users)
            ''')
            
            self.conn.commit()
            logger.info("✅ Очищено старі дані")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка очищення даних: {e}")
            return False

# Глобальний об'єкт бази даних
db = Database()