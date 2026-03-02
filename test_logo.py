#!/usr/bin/env python3
"""
Тестирование файла логотипа
"""

import os

def test_logo_file():
    """Проверка файла логотипа"""
    
    # Разные способы получить путь к файлу
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    paths_to_test = [
        "logoSblack.png",  # Относительный путь
        os.path.join(script_dir, "logoSblack.png"),  # Абсолютный путь
        "c:/Users/arsen/CascadeProjects/2048/logoSblack.png",  # Полный путь
        r"c:\Users\arsen\CascadeProjects\2048\logoSblack.png",  # Полный путь с raw string
    ]
    
    print("Проверка файла логотипа:")
    print("=" * 50)
    
    for i, path in enumerate(paths_to_test, 1):
        print(f"{i}. Путь: {path}")
        
        if os.path.exists(path):
            file_size = os.path.getsize(path)
            print(f"   ✅ Файл найден, размер: {file_size} байт ({file_size/1024:.1f} КБ)")
            
            # Проверяем, что это изображение
            if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                print(f"   ✅ Расширение файла корректно")
            else:
                print(f"   ⚠️  Расширение файла может быть некорректным")
                
        else:
            print(f"   ❌ Файл не найден")
        
        print("-" * 30)
    
    # Проверяем текущую рабочую директорию
    print(f"Текущая директория: {os.getcwd()}")
    print(f"Директория скрипта: {script_dir}")
    
    # Показываем все файлы в директории
    print("\nФайлы в директории проекта:")
    print("-" * 30)
    
    try:
        files = [f for f in os.listdir(script_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        if files:
            for file in files:
                size = os.path.getsize(os.path.join(script_dir, file))
                print(f"📷 {file} ({size/1024:.1f} КБ)")
        else:
            print("❌ Изображений не найдено")
    except Exception as e:
        print(f"Ошибка при чтении директории: {e}")

def test_path_generation():
    """Тестирование генерации пути как в боте"""
    
    print("\nТестирование генерации пути (как в боте):")
    print("=" * 50)
    
    # Имитируем код из бота
    try:
        import os
        logo_path = os.path.join(os.path.dirname(__file__), "logoSblack.png")
        print(f"Сгенерированный путь: {logo_path}")
        
        if os.path.exists(logo_path):
            print("✅ Путь корректен, файл существует")
        else:
            print("❌ Путь некорректен, файл не найден")
            
    except Exception as e:
        print(f"Ошибка при генерации пути: {e}")

if __name__ == "__main__":
    test_logo_file()
    test_path_generation()
    
    print("\n" + "=" * 50)
    print("Если файл не найден, проверьте:")
    print("1. Файл logoSblack.png находится в директории проекта")
    print("2. Имя файла написано правильно (регистр имеет значение)")
    print("3. Файл не поврежден")
    print("4. Права доступа к файлу позволяют чтение")
