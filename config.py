import os

# Отримуємо змінні оточення
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Безпечне отримання ADMIN_ID
admin_id_str = os.getenv('ADMIN_ID')
if admin_id_str and admin_id_str.isdigit():
    ADMIN_ID = int(admin_id_str)
else:
    ADMIN_ID = 1385645772  # Ваш Telegram ID як fallback
    print(f"⚠️  ADMIN_ID не встановлено, використовую fallback: {ADMIN_ID}")

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

DATABASE_URL = os.getenv('DATABASE_URL')

# Перевірка обов'язкових змінних
if not TOKEN:
    print("❌ КРИТИЧНА ПОМИЛКА: TELEGRAM_BOT_TOKEN не встановлено!")
    print("ℹ️  Бот не запуститься без токена")
    # Не викликаємо помилку тут, дозволимо main.py обробити це
else:
    print(f"✅ Конфігурація завантажена: TOKEN={'✅' if TOKEN else '❌'}, ADMIN_ID={ADMIN_ID}")