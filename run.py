import threading
import time
from bot import main as bot_main
from app import app as flask_app
from database import init_default_channels

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
        import os
        port = int(os.getenv('PORT', 5000))
        flask_app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
    except Exception as e:
        print(f"Ошибка запуска админ панели: {e}")

if __name__ == "__main__":
    print("Starting Telegram bot and admin panel...")
    
    # Инициализация базы данных
    print("Initializing database...")
    init_default_channels()
    print("Database initialized successfully!")
    
    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Небольшая задержка для инициализации бота
    time.sleep(2)
    
    # Запуск админ панели в основном потоке
    print("Admin panel available at: http://localhost:5000")
    run_admin_panel()
