"""
Обработчик рассылок в Telegram каналы
"""

import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# Импортируем только модели, не трогаем функции из bot.py во время рассылки
from database import get_db, Gunpack, Channel 
from config import BOT_TOKEN as TELEGRAM_BOT_TOKEN

# Глобальная очередь для рассылок (если используется фоновый процесс)
broadcast_queue = []

async def send_broadcast_to_channels(gunpack_id, message_text, selected_channels, media_type='', media_url=''):
    """Отправка рассылки: бот сам находит ID канала по его @username"""
    db = get_db()
    temp_bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            print("Ганпак не найден")
            return False
        
        success_count = 0
        error_count = 0
        
        bot_info = await temp_bot.get_me()
        bot_username = bot_info.username
        
        for channel_name in selected_channels:
            # Убеждаемся, что имя начинается с @
            formatted_name = channel_name if channel_name.startswith('@') else f"@{channel_name}"
            
            try:
                # ВАЖНО: Получаем актуальный ID чата напрямую через бота
                chat = await temp_bot.get_chat(formatted_name)
                chat_id = chat.id 
                
                # Создаем кнопку
                deep_link = f"https://t.me/{bot_username}?start=gunpack_{gunpack.id}"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"📦 Получить {gunpack.name}", url=deep_link)]
                ])
                
                text = f"{message_text}\n\n📦 **{gunpack.name}**\n"
                if gunpack.description:
                    text += f"{gunpack.description}\n"
                
                # Отправка
                if media_type and media_url:
                    if media_type == 'photo':
                        await temp_bot.send_photo(chat_id=chat_id, photo=media_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")
                    elif media_type == 'gif':
                        await temp_bot.send_animation(chat_id=chat_id, animation=media_url, caption=text, reply_markup=keyboard, parse_mode="Markdown")
                    elif media_type == 'youtube':
                        await temp_bot.send_message(chat_id=chat_id, text=f"{text}\n\n🎥 [Смотреть видео]({media_url})", reply_markup=keyboard, parse_mode="Markdown")
                else:
                    await temp_bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="Markdown")
                
                print(f"✅ Успешно отправлено в {formatted_name}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Ошибка канала {formatted_name}: {e}")
                error_count += 1
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False
    finally:
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
    print(f"📝 Добавлено в очередь (всего: {len(broadcast_queue)})")

async def process_broadcast_queue():
    """Фоновый цикл обработки очереди"""
    while True:
        if broadcast_queue:
            data = broadcast_queue.pop(0)
            print(f"📤 Обработка задачи из очереди для ID {data['gunpack_id']}")
            await send_broadcast_to_channels(**data)
        await asyncio.sleep(5)
