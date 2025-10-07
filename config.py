import os

# Отримуємо токен різними способами
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')

if not TOKEN:
    print("❌ ТОКЕН НЕ ЗНАЙДЕНО!")
    print("Доступні змінні середовища:")
    for key in os.environ.keys():
        print(f" - {key}")
    raise ValueError("Токен не знайдено!")

ADMIN_ID = int(os.getenv('ADMIN_ID', '1385645772'))

print(f"✅ Токен отримано: {TOKEN[:10]}...")
print(f"✅ ADMIN_ID: {ADMIN_ID}")