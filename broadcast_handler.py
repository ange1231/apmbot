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
    """Отправка рассылки в каналы с локальной сессией бота"""
    db = get_db()
    
    # Создаем локальный экземпляр бота для конкретной сессии рассылки
    temp_bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            print("Ганпак для рассылки не найден")
            return False
        
        # --- ПОЛУЧАЕМ КАНАЛЫ НАПРЯМУЮ ИЗ БД ---
        # Это исключает ошибку "Event loop is closed"
        db_channels = db.query(Channel).filter(Channel.is_active == True).all()
        admin_channels = []
        for ch in db_channels:
            # Очищаем имя от @ для сравнения
            clean_db_name = ch.name.replace('@', '').strip()
            admin_channels.append({
                'name': clean_db_name,
                'chat_id': ch.chat_id
            })
        
        success_count = 0
        error_count = 0
        
        # Получаем инфо о боте для формирования ссылок
        bot_info = await temp_bot.get_me()
        bot_username = bot_info.username
        
        for channel_name in selected_channels:
            # Очищаем имя канала из формы
            target_name = channel_name.replace('@', '').strip()
            
            # Ищем chat_id в списке из БД
            channel_info = next((c for c in admin_channels if c['name'] == target_name), None)
            
            if not channel_info:
                print(f"❌ Канал {channel_name} не найден в базе активных каналов")
                error_count += 1
                continue
            
            try:
                # Создаем кнопку-ссылку на бота
                deep_link = f"https://t.me/{bot_username}?start=gunpack_{gunpack.id}"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📦 Получить {gunpack.name}",
                        url=deep_link
                    )]
                ])
                
                # Формируем текст сообщения
                text = f"{message_text}\n\n"
                text += f"📦 **{gunpack.name}**\n"
                if gunpack.description:
                    text += f"{gunpack.description}\n"
                
                # Отправка контента в зависимости от типа медиа
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
                
                print(f"✅ Рассылка успешно отправлена в @{target_name}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Ошибка при отправке в @{target_name}: {e}")
                error_count += 1
        
        print(f"📊 Итог рассылки: ✅ {success_count} успешно, ❌ {error_count} ошибок")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Критическая ошибка в обработчике: {e}")
        return False
    finally:
        # Закрываем сессию временного бота и соединение с БД
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
