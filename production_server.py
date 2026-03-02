# Production сервер с Waitress (рекомендуется для Windows)
from waitress import serve
from app import app

if __name__ == "__main__":
    print("🚀 Запуск production сервера...")
    print("📊 Админ панель: http://localhost:8080")
    serve(app, host='0.0.0.0', port=8080)
