#!/usr/bin/env python3
"""
Скрипт для обновления базы данных до новой структуры
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, Channel, GunpackChannel, init_default_channels
from sqlalchemy import text

def update_database():
    """Обновление структуры базы данных"""
    print("Обновление базы данных...")
    
    # Создаем новые таблицы
    Base.metadata.create_all(engine)
    
    # Проверяем, существуют ли таблицы
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print(f"Таблицы в базе: {tables}")
    
    # Инициализируем каналы по умолчанию
    init_default_channels()
    
    print("База данных успешно обновлена!")

if __name__ == "__main__":
    update_database()
