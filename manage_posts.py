#!/usr/bin/env python3
"""
Утилита для управления постами в каналах
"""

import asyncio
import sys
import argparse
from channel_poster import ChannelPoster
import config
from database import get_db, Gunpack, Channel

async def create_post_for_gunpack(gunpack_id: int, channels: list = None, text: str = None):
    """Создает посты для указанного ганпака"""
    poster = ChannelPoster(config.BOT_TOKEN)
    
    if not channels:
        db = get_db()
        try:
            active_channels = db.query(Channel).filter(Channel.is_active == True).all()
            channels = [channel.name for channel in active_channels]
        finally:
            db.close()
    
    print(f"📢 Создание постов для ганпака #{gunpack_id}")
    print(f"📺 Каналы: {', '.join(channels)}")
    if text:
        print(f"📝 Текст: {text[:50]}...")
    print("-" * 50)
    
    results = []
    for channel in channels:
        result = await poster.create_post_with_button(channel, gunpack_id, text)
        results.append({"channel": channel, "success": result is not None})
    
    success_count = 0
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['channel']}")
        if result['success']:
            success_count += 1
    
    print("-" * 50)
    print(f"📊 Результат: {success_count}/{len(results)} постов создано")
    return results

async def list_gunpacks():
    """Показывает список всех ганпаков"""
    db = get_db()
    try:
        gunpacks = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        
        print("📦 Список активных ганпаков:")
        print("-" * 50)
        
        for gunpack in gunpacks:
            print(f"ID: {gunpack.id} | {gunpack.name}")
            if gunpack.description:
                desc = gunpack.description[:50] + "..." if len(gunpack.description) > 50 else gunpack.description
                print(f"    Описание: {desc}")
            print()
        
    finally:
        db.close()

async def list_channels():
    """Показывает список всех каналов"""
    db = get_db()
    try:
        channels = db.query(Channel).all()
        
        print("📺 Список каналов:")
        print("-" * 50)
        
        for channel in channels:
            status = "✅ Активен" if channel.is_active else "❌ Неактивен"
            print(f"{status} {channel.name} - {channel.title}")
        
    finally:
        db.close()

async def create_custom_post(gunpack_id: int, channel: str, text: str):
    """Создает кастомный пост в указанном канале"""
    poster = ChannelPoster(config.BOT_TOKEN)
    
    print(f"📢 Создание кастомного поста в {channel}")
    print(f"📦 Ганпак: #{gunpack_id}")
    print(f"📝 Текст: {text[:50]}...")
    print("-" * 50)
    
    result = await poster.create_post_with_button(channel, gunpack_id, text)
    
    if result:
        print(f"✅ Пост создан! Message ID: {result.message_id}")
    else:
        print("❌ Ошибка создания поста")

def main():
    parser = argparse.ArgumentParser(description="Управление постами в Telegram каналах")
    parser.add_argument("action", choices=["create", "list-gunpacks", "list-channels", "custom"], 
                       help="Действие")
    parser.add_argument("--gunpack", type=int, help="ID ганпака")
    parser.add_argument("--channels", nargs='+', help="Список каналов через пробел")
    parser.add_argument("--channel", help="Имя канала")
    parser.add_argument("--text", help="Текст поста")
    
    args = parser.parse_args()
    
    if args.action == "create":
        if not args.gunpack:
            print("❌ Укажите ID ганпака: --gunpack 1")
            return
        asyncio.run(create_post_for_gunpack(args.gunpack, args.channels))
    
    elif args.action == "list-gunpacks":
        asyncio.run(list_gunpacks())
    
    elif args.action == "list-channels":
        asyncio.run(list_channels())
    
    elif args.action == "custom":
        if not args.gunpack or not args.channel or not args.text:
            print("❌ Укажите все параметры: --gunpack 1 --channel @test --text 'Ваш текст'")
            return
        asyncio.run(create_custom_post(args.gunpack, args.channel, args.text))

if __name__ == "__main__":
    main()
