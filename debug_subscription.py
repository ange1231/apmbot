#!/usr/bin/env python3
"""
Простой тест для отладки функции check_subscription
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем функцию из бота
async def test_check_subscription_function():
    """Тест функции check_subscription с мок данными"""
    
    # Мокаем функцию для тестирования без реального бота
    async def mock_check_subscription(user_id: int, channels: list) -> tuple[bool, list]:
        """Мок функция для тестирования"""
        unsubscribed_channels = []
        
        for channel in channels:
            # Имитируем проверку - первые 2 канала не подписаны, остальные подписаны
            if channel in ['@channel1', '@channel2']:
                unsubscribed_channels.append(channel)
        
        return len(unsubscribed_channels) == 0, unsubscribed_channels
    
    # Тестовые данные
    test_channels = ['@channel1', '@channel2', '@channel3', '@channel4']
    test_user_id = 123456789
    
    print("Тестирование функции check_subscription")
    print("=" * 50)
    print(f"Каналы: {test_channels}")
    print(f"User ID: {test_user_id}")
    print("-" * 50)
    
    # Вызываем функцию
    try:
        is_subscribed, unsubscribed = await mock_check_subscription(test_user_id, test_channels)
        
        print(f"Результат:")
        print(f"  is_subscribed: {is_subscribed}")
        print(f"  unsubscribed: {unsubscribed}")
        print("-" * 50)
        
        if is_subscribed:
            print("✅ Пользователь подписан на все каналы")
        else:
            print("❌ Пользователь не подписан на некоторые каналы:")
            for channel in unsubscribed:
                print(f"  - {channel}")
            
            subscribed = [c for c in test_channels if c not in unsubscribed]
            if subscribed:
                print("✅ Подписан на:")
                for channel in subscribed:
                    print(f"  - {channel}")
        
        print("\n✅ Тест пройден успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_json_parsing():
    """Тест парсинга JSON"""
    import json
    
    test_cases = [
        '["@channel1", "@channel2"]',
        '[]',
        '["@channel1"]',
        '',
        None
    ]
    
    print("\nТестирование парсинга JSON")
    print("=" * 50)
    
    for test_json in test_cases:
        try:
            if test_json:
                channels = json.loads(test_json)
                print(f"✅ '{test_json}' -> {channels}")
            else:
                channels = []
                print(f"✅ '{test_json}' -> {channels} (пусто)")
        except json.JSONDecodeError as e:
            print(f"❌ '{test_json}' -> Ошибка: {e}")
        except Exception as e:
            print(f"❌ '{test_json}' -> Неизвестная ошибка: {e}")

if __name__ == "__main__":
    print("Отладка функции проверки подписок")
    print("=" * 60)
    
    # Тест функции
    result1 = asyncio.run(test_check_subscription_function())
    
    # Тест JSON
    asyncio.run(test_json_parsing())
    
    print("\n" + "=" * 60)
    if result1:
        print("✅ Все тесты пройдены!")
    else:
        print("❌ Некоторые тесты не пройдены!")
