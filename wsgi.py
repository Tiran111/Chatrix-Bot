from main import app, init_bot
import os

print("🚀 Запуск бота через WSGI...")

# Ініціалізація бота
print("🔧 Ініціалізація бота...")
if init_bot():
    print("✅ Бот успішно ініціалізовано")
else:
    print("❌ Помилка ініціалізації бота")

# Експортуємо Flask додаток для Gunicorn
application = app

if __name__ == "__main__":
    # Цей блок виконується тільки при запуску напряму
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Запуск сервера на порті {port}")
    application.run(host='0.0.0.0', port=port)