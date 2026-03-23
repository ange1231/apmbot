import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
DB_PATH = os.getenv('DB_PATH', 'database.db')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
PROXY_URL = os.getenv('PROXY_URL')  # None если не задан — бот работает без прокси

# Внутренний API-сервер бота (для проверки подписок с сайта)
# Бот поднимает HTTP-сервер на этом порту, сайт делает к нему запросы
BOT_API_PORT = int(os.getenv('BOT_API_PORT', 8765))
BOT_API_SECRET = os.getenv('BOT_API_SECRET', 'changeme-internal-secret')
