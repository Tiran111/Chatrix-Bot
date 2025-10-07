import os

# Спробуємо різні варіанти назв змінних
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')

# Якщо токен все ще не знайдено - використаємо тимчасовий для запуску
if not TOKEN:
    print("⚠️  Токен не знайдено в змінних середовища")
    # Тимчасово закоментуйте цю помилку для тесту:
    # raise ValueError("❌ TELEGRAM_BOT_TOKEN не знайдено!")
    TOKEN = "placeholder-token"  # Тимчасово для запуску

ADMIN_ID = int(os.getenv('ADMIN_ID', '1385645772'))

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

DATABASE_URL = os.getenv('DATABASE_URL')