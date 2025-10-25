from main import app, init_bot_sync, shutdown_bot_sync
import atexit

# Ініціалізуємо бота при завантаженні модуля
init_bot_sync()

# Реєструємо завершення при виході
atexit.register(shutdown_bot_sync)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)