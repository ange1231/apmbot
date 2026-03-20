import threading
import time
import os
from app import app as flask_app
from database import init_default_channels

def run_bot():
    """Run Telegram bot - only if BOT_TOKEN is set and valid"""
    bot_token = os.getenv('BOT_TOKEN', '')
    if not bot_token or bot_token == 'placeholder':
        print("BOT_TOKEN not configured - bot will not start. Set BOT_TOKEN secret to enable the bot.")
        return
    try:
        from bot import main as bot_main
        import asyncio
        asyncio.run(bot_main())
    except Exception as e:
        print(f"Bot error: {e}")

def run_admin_panel():
    """Run admin panel"""
    port = int(os.getenv('PORT', 5000))
    flask_app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)

if __name__ == "__main__":
    print("Initializing database...")
    init_default_channels()
    print("Database initialized!")

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    time.sleep(1)

    print("Admin panel starting on port 5000...")
    run_admin_panel()
