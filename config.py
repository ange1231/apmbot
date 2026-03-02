import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
DB_PATH = os.getenv('DB_PATH', 'database.db')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

REQUIRED_CHANNELS = [
    '@channel1',  # Замените на ваши каналы
    '@channel2',
    '@channel3'
]
