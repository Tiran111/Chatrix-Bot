from main import app, init_bot_sync

# Ініціалізуємо бота при імпорті
init_bot_sync()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)