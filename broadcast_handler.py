"""
Обработчик рассылок в Telegram каналы
"""

import asyncio
from bot import bot, get_admin_channels
from database import get_db, Gunpack
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def send_broadcast_to_channels(gunpack_id, message_text, selected_channels, media_type='', media_url=''):
    """Отправка рассылки в каналы"""
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            print("Ганпак для рассылки не найден")
            return False
        
        # Получаем каналы где бот админ
        admin_channels = await get_admin_channels()
        
        success_count = 0
        error_count = 0
        
        for channel_name in selected_channels:
            # Проверяем что бот админ в этом канале
            channel_info = next((c for c in admin_channels if c['name'] == channel_name), None)
            if not channel_info:
                print(f"Бот не админ в канале @{channel_name}")
                error_count += 1
                continue
            
            try:
                # Получаем информацию о боте
                bot_info = await bot.get_me()
                bot_username = bot_info.username
                
                # Создаем кнопку как ссылку на бота с параметром
                deep_link = f"https://t.me/{bot_username}?start=gunpack_{gunpack.id}"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📦 Получить {gunpack.name}",
                        url=deep_link
                    )]
                ])
                
                # Формируем сообщение
                text = f"{message_text}\n\n"
                text += f"📦 **{gunpack.name}**\n"
                if gunpack.description:
                    text += f"{gunpack.description}\n"
                
                # Отправляем сообщение с медиа или без
                if media_type and media_url:
                    if media_type == 'photo':
                        # Отправляем фото
                        await bot.send_photo(
                            chat_id=channel_info['chat_id'],
                            photo=media_url,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                    elif media_type == 'gif':
                        # Отправляем GIF
                        await bot.send_animation(
                            chat_id=channel_info['chat_id'],
                            animation=media_url,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                    elif media_type == 'youtube':
                        # Для YouTube просто добавляем ссылку в текст
                        youtube_text = f"{text}\n\n🎥 [Смотреть видео]({media_url})"
                        await bot.send_message(
                            chat_id=channel_info['chat_id'],
                            text=youtube_text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                    else:
                        # Неизвестный тип, отправляем как текст
                        await bot.send_message(
                            chat_id=channel_info['chat_id'],
                            text=text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                else:
                    # Отправляем без медиа
                    await bot.send_message(
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
        print(f"❌ Ошибка при отправке рассылки: {e}")
        return False
    finally:
        db.close()

# Глобальная очередь для рассылок
broadcast_queue = []

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
    """Обработка очереди рассылок"""
    while True:
        if broadcast_queue:
            broadcast_data = broadcast_queue.pop(0)
            print(f"📤 Обработка рассылки из очереди...")
            
            success = await send_broadcast_to_channels(
                broadcast_data['gunpack_id'],
                broadcast_data['message_text'],
                broadcast_data['selected_channels'],
                broadcast_data.get('media_type', ''),
                broadcast_data.get('media_url', '')
            )
            
            if success:
                print("✅ Рассылка успешно отправлена")
            else:
                print("❌ Ошибка при отправке рассылки")
        
        await asyncio.sleep(5)  # Проверяем очередь каждые 5 секунд
