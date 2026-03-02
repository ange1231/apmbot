import asyncio
from bot import main as bot_main

if __name__ == "__main__":
    print("Starting Telegram bot...")
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot error: {e}")
