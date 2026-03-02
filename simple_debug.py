#!/usr/bin/env python3
"""
Простой тест для отладки функции check_subscription
"""

import asyncio
import json

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
    
    print("Testing check_subscription function")
    print("=" * 50)
    print(f"Channels: {test_channels}")
    print(f"User ID: {test_user_id}")
    print("-" * 50)
    
    # Вызываем функцию
    try:
        is_subscribed, unsubscribed = await mock_check_subscription(test_user_id, test_channels)
        
        print(f"Result:")
        print(f"  is_subscribed: {is_subscribed}")
        print(f"  unsubscribed: {unsubscribed}")
        print("-" * 50)
        
        if is_subscribed:
            print("User subscribed to all channels")
        else:
            print("User not subscribed to some channels:")
            for channel in unsubscribed:
                print(f"  - {channel}")
            
            subscribed = [c for c in test_channels if c not in unsubscribed]
            if subscribed:
                print("Subscribed to:")
                for channel in subscribed:
                    print(f"  - {channel}")
        
        print("\nTest passed successfully!")
        return True
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_json_parsing():
    """Тест парсинга JSON"""
    
    test_cases = [
        '["@channel1", "@channel2"]',
        '[]',
        '["@channel1"]',
        '',
        None
    ]
    
    print("\nTesting JSON parsing")
    print("=" * 50)
    
    for test_json in test_cases:
        try:
            if test_json:
                channels = json.loads(test_json)
                print(f"OK: '{test_json}' -> {channels}")
            else:
                channels = []
                print(f"OK: '{test_json}' -> {channels} (empty)")
        except json.JSONDecodeError as e:
            print(f"ERROR: '{test_json}' -> JSON Error: {e}")
        except Exception as e:
            print(f"ERROR: '{test_json}' -> Unknown error: {e}")

if __name__ == "__main__":
    print("Debug subscription check function")
    print("=" * 60)
    
    # Тест функции
    result1 = asyncio.run(test_check_subscription_function())
    
    # Тест JSON
    asyncio.run(test_json_parsing())
    
    print("\n" + "=" * 60)
    if result1:
        print("All tests passed!")
    else:
        print("Some tests failed!")
