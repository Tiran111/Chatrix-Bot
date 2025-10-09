import sqlite3
import os
from datetime import datetime, date

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
                rating REAL DEFAULT 5.0,
                daily_likes_count INTEGER DEFAULT 0,
                last_like_date DATE
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
            
            # Оновлюємо рейтинг після змін профілю
            self.update_rating_on_profile_update(telegram_id)
            
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
            
            # Оновлюємо рейтинг після додавання фото
            self.update_rating_on_profile_update(telegram_id)
            
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
    
    def get_random_user(self, current_user_id, city=None):
        """Отримання випадкового користувача для пошуку"""
        try:
            current_user = self.get_user(current_user_id)
            if not current_user:
                return None
            
            seeking_gender = current_user.get('seeking_gender', 'all')
            
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
            
            query += ' ORDER BY RANDOM() LIMIT 1'
            
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
            '''
            params = [current_user_id, f'%{clean_city}%']
            
            if seeking_gender != 'all':
                query += ' AND u.gender = ?'
                params.append(seeking_gender)
            
            query += ' ORDER BY RANDOM() LIMIT 20'
            
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
            self.cursor.execute('SELECT likes_count FROM users WHERE telegram_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"❌ Помилка отримання лайків: {e}")
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
            print(f"❌ Помилка перевірки лайків: {e}")
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
            self.update_rating_on_like(to_user_id)
            
            self.conn.commit()
            
            # Перевіряємо чи це взаємний лайк
            is_mutual = self.has_liked(to_user_id, from_user_id)
            
            return True, "Лайк додано" if not is_mutual else "Лайк додано! 💕 У вас матч!"
            
        except Exception as e:
            print(f"❌ Помилка додавання лайку: {e}")
            return False, "Помилка додавання лайку"
    
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
            
            print(f"🔍 [TOP] Знайдено {len(users)} користувачів для топу")
            
            # Детальна відладка
            for i, user in enumerate(users, 1):
                print(f"🔍 [TOP {i}] ID: {user[1]}, Ім'я: {user[3]}, Рейтинг: {user[14]}, Лайків: {user[12]}")
            
            return users
        except Exception as e:
            print(f"❌ Помилка отримання топу за рейтингом: {e}")
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

    def calculate_user_rating(self, user_id):
        """Розрахунок рейтингу користувача"""
        try:
            user_data = self.get_user(user_id)
            if not user_data:
                return 5.0
                
            likes_count = user_data.get('likes_count', 0)
            has_photo = user_data.get('has_photo', False)
            has_bio = bool(user_data.get('bio'))
            bio_length = len(user_data.get('bio', ''))
            
            # Базова формула рейтингу
            base_rating = 5.0
            
            # Бонус за лайки
            rating_bonus = min(likes_count * 0.2, 3.0)  # Максимум +3 за лайки
            
            # Бонуси за заповненість профілю
            if has_photo:
                rating_bonus += 1.0
            
            if has_bio:
                if bio_length > 50:
                    rating_bonus += 1.5
                elif bio_length > 20:
                    rating_bonus += 1.0
                else:
                    rating_bonus += 0.5
            
            final_rating = min(base_rating + rating_bonus, 10.0)
            return round(final_rating, 1)
        except Exception as e:
            print(f"❌ Помилка розрахунку рейтингу: {e}")
            return 5.0

    def update_rating_on_like(self, user_id):
        """Оновлення рейтингу при отриманні лайку"""
        try:
            new_rating = self.calculate_user_rating(user_id)
            
            self.cursor.execute(
                'UPDATE users SET rating = ? WHERE telegram_id = ?',
                (new_rating, user_id)
            )
            self.conn.commit()
            print(f"✅ Рейтинг оновлено для {user_id}: {new_rating}")
            return True
        except Exception as e:
            print(f"❌ Помилка оновлення рейтингу: {e}")
            return False

    def update_rating_on_profile_update(self, user_id):
        """Оновлення рейтингу при зміні профілю"""
        try:
            new_rating = self.calculate_user_rating(user_id)
            
            self.cursor.execute(
                'UPDATE users SET rating = ? WHERE telegram_id = ?',
                (new_rating, user_id)
            )
            self.conn.commit()
            print(f"✅ Рейтинг оновлено при зміні профілю для {user_id}: {new_rating}")
            return True
        except Exception as e:
            print(f"❌ Помилка оновлення рейтингу профілю: {e}")
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

    def debug_user_profile(self, telegram_id):
        """Відладка профілю користувача"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = self.cursor.fetchone()
            
            if user:
                print(f"🔍 [DEBUG USER] ID: {user[1]}")
                print(f"🔍 [DEBUG USER] Ім'я: {user[3]}")
                print(f"🔍 [DEBUG USER] Вік: {user[4]}")
                print(f"🔍 [DEBUG USER] Стать: {user[5]}")
                print(f"🔍 [DEBUG USER] Місто: {user[6]}")
                print(f"🔍 [DEBUG USER] Фото: {user[10]}")
                print(f"🔍 [DEBUG USER] Лайків: {user[12]}")
                print(f"🔍 [DEBUG USER] Рейтинг: {user[14]}")
                print(f"🔍 [DEBUG USER] Заблокований: {user[13]}")
                return True
            else:
                print(f"🔍 [DEBUG USER] Користувача {telegram_id} не знайдено")
                return False
        except Exception as e:
            print(f"❌ Помилка відладки: {e}")
            return False

# Глобальний об'єкт бази даних
db = Database()