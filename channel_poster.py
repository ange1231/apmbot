#!/usr/bin/env python3
"""
Модуль для создания постов с кнопками в Telegram каналах
"""

import asyncio
import logging
from aiogram import Bot, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import config
from database import get_db, Gunpack

logging.basicConfig(level=logging.INFO)

class ChannelPoster:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
    
    async def create_post_with_button(self, channel_username: str, gunpack_id: int, post_text: str = None):
        """Создает пост в канале с кнопкой 'Получить'"""
        db = get_db()
        try:
            gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
            if not gunpack:
                print(f"Ганпак с ID {gunpack_id} не найден")
                return None
            
            # Формируем текст поста
            if not post_text:
                post_text = f"🎁 **Новый ганпак доступен!**\n\n"
                post_text += f"**{gunpack.name}**\n\n"
                if gunpack.description:
                    post_text += f"{gunpack.description}\n\n"
                post_text += "Нажмите кнопку ниже для получения 👇"
            
            # Создаем inline кнопку
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🎁 Получить", 
                    callback_data=f"get_gunpack_{gunpack_id}"
                )]
            ])
            
            # Отправляем пост в канал
            try:
                message = await self.bot.send_message(
                    chat_id=channel_username,
                    text=post_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                print(f"✅ Пост успешно создан в канале {channel_username}")
                print(f"📝 Message ID: {message.message_id}")
                return message
            except Exception as e:
                print(f"❌ Ошибка отправки поста: {e}")
                return None
                
        finally:
            db.close()
    
    async def edit_post_button(self, channel_username: str, message_id: int, gunpack_id: int):
        """Редактирует кнопку в существующем посте"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Получить", 
                callback_data=f"get_gunpack_{gunpack_id}"
            )]
        ])
        
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=channel_username,
                message_id=message_id,
                reply_markup=keyboard
            )
            print(f"✅ Кнопка в посте {message_id} обновлена")
            return True
        except Exception as e:
            print(f"❌ Ошибка редактирования кнопки: {e}")
            return False
    
    async def create_gunpack_post(self, gunpack_id: int, channels: list = None):
        """Создает посты о ганпаке в указанных каналах"""
        if not channels:
            # Если каналы не указаны, используем все активные каналы из базы
            from database import Channel
            db = get_db()
            try:
                active_channels = db.query(Channel).filter(Channel.is_active == True).all()
                channels = [channel.name for channel in active_channels]
            finally:
                db.close()
        
        results = []
        for channel in channels:
            result = await self.create_post_with_button(channel, gunpack_id)
            results.append({"channel": channel, "success": result is not None})
        
        return results

# Функция для использования в основном боте
async def handle_gunpack_callback(callback: types.CallbackQuery):
    """Обрабатывает нажатие на кнопку 'Получить' в канале"""
    callback_data = callback.data
    if callback_data.startswith("get_gunpack_"):
        gunpack_id = int(callback_data.split("_")[2])
        
        db = get_db()
        try:
            gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
            if not gunpack:
                await callback.answer("Ганпак не найден!", show_alert=True)
                return
            
            # Перенаправляем пользователя в личные сообщения с ботом
            bot_username = (await callback.bot.get_me()).username
            
            await callback.answer(
                text=f"🎁 Перейдите в бот @{bot_username} для получения ганпака!",
                show_alert=True
            )
            
            # Отправляем приветственное сообщение в личный чат
            try:
                await callback.bot.send_message(
                    chat_id=callback.from_user.id,
                    text=f"🎁 *Вы запросили ганпак {escape_markdown_v2(gunpack.name)}\\!*\n\n"
                         f"Нажмите /start чтобы продолжить получение\\.",
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                print(f"Ошибка отправки личного сообщения: {e}")
                
                # Если не удалось отправить личное сообщение, показываем информацию
                text = f"🎁 *{escape_markdown_v2(gunpack.name)}*\n\n"
                text += f"{escape_markdown_v2(gunpack.description or '')}\n\n"
                text += "📋 *Условия получения:*\n"
                text += "Подпишитесь на следующие каналы:\n"
                
                # Получаем каналы для ганпака
                if gunpack.channels_required:
                    channels = json.loads(gunpack.channels_required)
                else:
                    from database import Channel
                    active_channels = db.query(Channel).filter(Channel.is_active == True).all()
                    channels = [channel.name for channel in active_channels]
                
                for channel in channels:
                    channel_link = channel if channel.startswith('https://') else f"https://t.me/{channel.replace('@', '')}"
                    text += f"• [{escape_markdown_v2(channel)}]({channel_link})\n"
                
                text += f"\nПосле подписки напишите боту @{bot_username}"
                
                await callback.message.answer(
                    text,
                    parse_mode="MarkdownV2"
                )
                
        finally:
            db.close()

def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2"""
    special_chars = '_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

if __name__ == "__main__":
    # Пример использования
    async def main():
        poster = ChannelPoster(config.BOT_TOKEN)
        
        # Создать пост для ганпака с ID=1 в канале @test_channel
        await poster.create_post_with_button("@test_channel", 1)
        
        # Или создать посты во всех активных каналах
        # await poster.create_gunpack_post(1)
    
    asyncio.run(main())
