import threading
import time
from bot import main as bot_main
from app import app as flask_app

def run_bot():
    """Запуск Telegram бота"""
    try:
        import asyncio
        asyncio.run(bot_main())
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")

def run_admin_panel():
    """Запуск админ панели"""
    try:
        flask_app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"Ошибка запуска админ панели: {e}")

if __name__ == "__main__":
    print("Starting Telegram bot and admin panel...")
    
    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Небольшая задержка для инициализации бота
    time.sleep(2)
    
    # Запуск админ панели в основном потоке
    print("Admin panel available at: http://localhost:5000")
    run_admin_panel()
