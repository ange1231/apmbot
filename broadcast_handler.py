"""
Обработчик рассылок в Telegram каналы
"""

import asyncio
import logging
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_db, Gunpack, Channel
import config

logger = logging.getLogger(__name__)

# Глобальная очередь для рассылок
broadcast_queue = []


def _make_bot() -> Bot:
    """Создаёт бота с прокси если задан в .env — так же как в bot.py."""
    if config.PROXY_URL:
        session = AiohttpSession(proxy=config.PROXY_URL)
        return Bot(token=config.BOT_TOKEN, session=session)
    return Bot(token=config.BOT_TOKEN)


async def send_broadcast_to_channels(gunpack_id, message_text, selected_channels, media_type='', media_url=''):
    """Отправка рассылки в Telegram каналы."""
    db = get_db()
    temp_bot = _make_bot()

    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            logger.error("Рассылка: ганпак %s не найден", gunpack_id)
            return False

        bot_info = await temp_bot.get_me()
        bot_username = bot_info.username
        deep_link = f"https://t.me/{bot_username}?start=gunpack_{gunpack.id}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📦 Получить {gunpack.name}", url=deep_link)]
        ])

        text = f"{message_text}\n\n📦 **{gunpack.name}**\n"
        if gunpack.description:
            text += f"{gunpack.description}\n"

        success_count = 0
        error_count = 0

        for channel_name in selected_channels:
            formatted_name = channel_name if channel_name.startswith('@') else f"@{channel_name}"
            try:
                chat = await temp_bot.get_chat(formatted_name)
                chat_id = chat.id

                if media_type and media_url:
                    if media_type == 'photo':
                        await temp_bot.send_photo(chat_id=chat_id, photo=media_url,
                                                  caption=text, reply_markup=keyboard, parse_mode="Markdown")
                    elif media_type == 'gif':
                        await temp_bot.send_animation(chat_id=chat_id, animation=media_url,
                                                      caption=text, reply_markup=keyboard, parse_mode="Markdown")
                    elif media_type == 'youtube':
                        await temp_bot.send_message(chat_id=chat_id,
                                                    text=f"{text}\n\n🎥 [Смотреть видео]({media_url})",
                                                    reply_markup=keyboard, parse_mode="Markdown")
                else:
                    await temp_bot.send_message(chat_id=chat_id, text=text,
                                                reply_markup=keyboard, parse_mode="Markdown")

                logger.info("Рассылка: успешно отправлено в %s", formatted_name)
                success_count += 1

            except Exception as e:
                logger.error("Рассылка: ошибка канала %s: %s", formatted_name, e)
                error_count += 1

        logger.info("Рассылка завершена: успешно=%s ошибок=%s", success_count, error_count)
        return success_count > 0

    except Exception as e:
        logger.error("Рассылка: критическая ошибка: %s", e, exc_info=True)
        return False
    finally:
        await temp_bot.session.close()
        db.close()


async def process_broadcast_queue():
    """Фоновый цикл обработки очереди рассылок."""
    logger.info("Очередь рассылок запущена")
    while True:
        if broadcast_queue:
            data = broadcast_queue.pop(0)
            logger.info("Обработка рассылки для ганпака id=%s", data['gunpack_id'])
            await send_broadcast_to_channels(**data)
        await asyncio.sleep(5)
