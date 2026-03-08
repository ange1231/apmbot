"""
Обработчик рассылок в Telegram каналы
"""

import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import get_admin_channels
from database import get_db, Gunpack
from config import BOT_TOKEN as TELEGRAM_BOT_TOKEN

# Глобальная очередь для рассылок (если используется фоновый процесс)
broadcast_queue = []

async def send_broadcast_to_channels(gunpack_id, message_text, selected_channels, media_type='', media_url=''):
    """Отправка рассылки в каналы с локальной сессией бота"""
    db = get_db()
    
    # Создаем локальный экземпляр бота для конкретной сессии рассылки
    # Это решает проблему "AiohttpSession is closed" при повторных вызовах
    temp_bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            print("Ганпак для рассылки не найден")
            return False
        
        # Получаем каналы, где бот админ (используем тот же токен)
        admin_channels = await get_admin_channels()
        
        success_count = 0
        error_count = 0
        
        # Получаем инфо о боте один раз для deep_link
        bot_info = await temp_bot.get_me()
        bot_username = bot_info.username
        
        for channel_name in selected_channels:
            # Ищем chat_id канала
            channel_info = next((c for c in admin_channels if c['name'] == channel_name), None)
            if not channel_info:
                print(f"Бот не админ в канале @{channel_name}")
                error_count += 1
                continue
            
            try:
                # Создаем кнопку
                deep_link = f"https://t.me/{bot_username}?start=gunpack_{gunpack.id}"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📦 Получить {gunpack.name}",
                        url=deep_link
                    )]
                ])
                
                # Формируем текст
                text = f"{message_text}\n\n"
                text += f"📦 **{gunpack.name}**\n"
                if gunpack.description:
                    text += f"{gunpack.description}\n"
                
                # Отправка контента
                if media_type and media_url:
                    if media_type == 'photo':
                        await temp_bot.send_photo(
                            chat_id=channel_info['chat_id'],
                            photo=media_url,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                    elif media_type == 'gif':
                        await temp_bot.send_animation(
                            chat_id=channel_info['chat_id'],
                            animation=media_url,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                    elif media_type == 'youtube':
                        youtube_text = f"{text}\n\n🎥 [Смотреть видео]({media_url})"
                        await temp_bot.send_message(
                            chat_id=channel_info['chat_id'],
                            text=youtube_text,
                            reply_markup=keyboard,
                            parse_mode="Markdown",
                            disable_web_page_preview=False
                        )
                else:
                    await temp_bot.send_message(
                        chat_id=channel_info['chat_id'],
                        text=text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                
                print(f"✅ Рассылка отправлена в @{channel_name}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Ошибка отправки в @{channel_name}: {e}")
                error_count += 1
        
        print(f"📊 Рассылка завершена: ✅ {success_count} успешно, ❌ {error_count} с ошибками")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Критическая ошибка в обработчике: {e}")
        return False
    finally:
        # Корректное закрытие сессии для aiogram 3.x
        await temp_bot.session.close()
        db.close()

async def add_broadcast_to_queue(gunpack_id, message_text, selected_channels, media_type='', media_url=''):
    """Добавить рассылку в очередь"""
    broadcast_queue.append({
        'gunpack_id': gunpack_id,
        'message_text': message_text,
        'selected_channels': selected_channels,
        'media_type': media_type,
        'media_url': media_url
    })
    print(f"📝 Рассылка добавлена в очередь (в очереди: {len(broadcast_queue)})")

async def process_broadcast_queue():
    """Фоновая обработка очереди"""
    while True:
        if broadcast_queue:
            data = broadcast_queue.pop(0)
            print(f"📤 Обработка из очереди...")
            await send_broadcast_to_channels(
                data['gunpack_id'], 
                data['message_text'], 
                data['selected_channels'],
                data['media_type'], 
                data['media_url']
            )
        await asyncio.sleep(5)
