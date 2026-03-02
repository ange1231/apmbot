#!/usr/bin/env python3
"""
Тестирование функции проверки подписок
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from aiogram import Bot

async def test_check_subscription():
    """Тестирование проверки подписок с детализацией"""
    bot = Bot(token=config.BOT_TOKEN)
    
    # Тестовые каналы (замените на реальные)
    test_channels = ["@channel1", "@channel2"]  # Замените на ваши каналы
    test_user_id = 123456789  # Замените на ваш user_id
    
    print(f"Тестирование проверки подписок для пользователя {test_user_id}")
    print(f"Каналы: {test_channels}")
    print("-" * 50)
    
    unsubscribed_channels = []
    
    for channel in test_channels:
        try:
            # Преобразуем формат канала для API
            if channel.startswith('@'):
                chat_id = channel
            elif channel.startswith('https://t.me/'):
                chat_id = channel.replace('https://t.me/', '@')
            else:
                chat_id = f"@{channel}"
            
            print(f"Проверка подписки на {chat_id}...")
            
            member = await bot.get_chat_member(chat_id, test_user_id)
            print(f"✅ Статус пользователя: {member.status}")
            
            if member.status in ['member', 'creator', 'administrator']:
                print(f"✅ Пользователь подписан на {channel}")
            else:
                print(f"❌ Пользователь не подписан на {channel}")
                unsubscribed_channels.append(channel)
                
        except Exception as e:
            print(f"❌ Ошибка проверки {channel}: {e}")
            unsubscribed_channels.append(channel)
        
        print("-" * 30)
    
    # Итоговый результат
    is_subscribed = len(unsubscribed_channels) == 0
    print(f"Результат: {'✅ Подписан на все' if is_subscribed else '❌ Не подписан на некоторые'}")
    
    if unsubscribed_channels:
        print(f"Неподписанные каналы: {unsubscribed_channels}")
    
    return is_subscribed, unsubscribed_channels

async def test_bot_info():
    """Проверка информации о боте"""
    bot = Bot(token=config.BOT_TOKEN)
    
    try:
        bot_info = await bot.get_me()
        print(f"Бот: @{bot_info.username}")
        print(f"ID: {bot_info.id}")
        print(f"Имя: {bot_info.first_name}")
    except Exception as e:
        print(f"Ошибка получения информации о боте: {e}")

if __name__ == "__main__":
    print("Тестирование Telegram бота")
    print("=" * 50)
    
    # Проверка информации о боте
    asyncio.run(test_bot_info())
    print()
    
    # Тестирование подписок
    print("Внимание: замените test_channels и test_user_id на реальные значения!")
    print("Или пропустите этот тест, если у вас нет реальных данных.")
    print()
    
    user_input = input("Запустить тест проверки подписок? (y/n): ")
    if user_input.lower() == 'y':
        asyncio.run(test_check_subscription())
    else:
        print("Тест пропущен.")
