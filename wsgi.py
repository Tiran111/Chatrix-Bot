from main import app, init_bot_sync
import threading

# Запускаємо ініціалізацію бота в окремому потоці
bot_thread = threading.Thread(target=init_bot_sync, daemon=True)
bot_thread.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)