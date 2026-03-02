#!/usr/bin/env python3
"""
Скрипт для загрузки проекта на PythonAnywhere
"""

import os
import zipfile
import requests

def create_project_zip():
    """Создает ZIP архив проекта"""
    files_to_include = [
        'app.py', 'bot.py', 'database.py', 'broadcast_handler.py',
        'wsgi.py', 'requirements.txt', '.gitignore'
    ]
    
    folders_to_include = ['templates', 'static']
    
    with zipfile.ZipFile('project.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Добавляем файлы
        for file in files_to_include:
            if os.path.exists(file):
                zipf.write(file)
        
        # Добавляем папки
        for folder in folders_to_include:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path)
    
    print("✅ Архив project.zip создан!")

if __name__ == "__main__":
    create_project_zip()
    print("\n📁 Загрузи project.zip в PythonAnywhere через Web интерфейс")
    print("🔄 Затем распакуй и установи зависимости: pip install -r requirements.txt")
