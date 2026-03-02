import asyncio
import os
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile, InputMediaAnimation
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command

from database import get_db, User, Gunpack, Download, Channel
import config

# Функция для экранирования MarkdownV2
def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2"""
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Получить ганпак")],
            [KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_gunpacks_keyboard():
    """Создает клавиатуру с ганпаками"""
    db = get_db()
    try:
        gunpacks = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        keyboard = []
        
        for gunpack in gunpacks:
            keyboard.append([InlineKeyboardButton(
                text=f"📦 {gunpack.name}",
                callback_data=f"gunpack_{gunpack.id}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    finally:
        db.close()

async def get_admin_channels():
    """Получает список каналов где бот является администратором"""
    try:
        # Получаем все каналы из базы данных
        db = get_db()
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        admin_channels = []
        
        for channel in channels:
            try:
                # Проверяем права бота в канале
                chat_member = await bot.get_chat_member(f"@{channel.name}", bot.id)
                if chat_member.status in ['administrator', 'creator']:
                    admin_channels.append({
                        'name': channel.name,
                        'title': channel.title or channel.name,
                        'chat_id': f"@{channel.name}"
                    })
            except Exception as e:
                print(f"Ошибка проверки прав для канала @{channel.name}: {e}")
        
        return admin_channels
    finally:
        db.close()

async def check_subscription(user_id: int, channels: list) -> tuple[bool, list]:
    """Проверяет подписку пользователя на каналы, возвращает (статус, список неподписанных)"""
    unsubscribed_channels = []
    
    for channel in channels:
        try:
            # Преобразуем формат канала для API
            if channel.startswith('@'):
                chat_id = channel
            elif channel.startswith('https://t.me/'):
                chat_id = channel.replace('https://t.me/', '@')
            else:
                chat_id = f"@{channel}"
            
            print(f"Проверка подписки на {chat_id} для пользователя {user_id}")
            
            member = await bot.get_chat_member(chat_id, user_id)
            print(f"Статус пользователя: {member.status}")
            
            if member.status not in ['member', 'creator', 'administrator']:
                print(f"Пользователь не подписан на {chat_id}")
                unsubscribed_channels.append(channel)
        except Exception as e:
            print(f"Ошибка проверки подписки на {channel}: {e}")
            unsubscribed_channels.append(channel)
    
    return len(unsubscribed_channels) == 0, unsubscribed_channels

def get_direct_image_url(url: str) -> str:
    """Преобразует URL с разных хостингов в прямой URL изображения/GIF"""
    if 'ibb.co' in url:
        # Поддерживаем разные форматы ibb.co:
        # https://ibb.co/xxxxxxx
        # https://ibb.co/album/xxxxxxx
        # https://ibb.co/gallery/xxxxxxx
        
        # Заменяем домен на i.ibb.co для прямого доступа к изображению
        url = url.replace('https://ibb.co/', 'https://i.ibb.co/')
        url = url.replace('http://ibb.co/', 'http://i.ibb.co/')
        
        # Если URL не заканчивается расширением изображения, добавляем его
        if not any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
            # Пробуем получить расширение из оригинального URL или добавляем .jpg
            url += '.jpg'
    elif 'postimg.cc' in url:
        # PostImg уже дает прямые ссылки, оставляем как есть
        pass
    elif 'ezgif.com' in url:
        # EzGif оптимизированные GIF, оставляем как есть
        pass
    
    return url

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    db = get_db()
    try:
        # Создаем пользователя если его нет
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            db.add(user)
            db.commit()
        
        # Проверяем есть ли параметр в команде /start
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if args and args[0].startswith('gunpack_'):
            # Если есть параметр gunpack_, сразу показываем ганпак
            gunpack_id = int(args[0].split('_')[1])
            
            # Проверяем существование ганпака
            gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
            if gunpack:
                # Создаем искусственный callback для gunpack_details
                class MockCallback:
                    def __init__(self, message_obj, gunpack_id_val):
                        self.id = "mock_callback"
                        self.from_user = message_obj.from_user
                        self.message = message_obj
                        self.data = f"gunpack_{gunpack_id_val}"
                        self.chat_instance = "mock_chat_instance"
                    
                    async def answer(self, text=None, show_alert=None):
                        pass
                
                mock_callback = MockCallback(message, gunpack_id)
                await gunpack_details(mock_callback)
                return
            else:
                await message.answer(
                    "❌ Ганпак не найден! Попробуйте выбрать его из меню.",
                    reply_markup=get_main_keyboard()
                )
                return
        
        # Отправляем приветствие с логотипом
        logo_path = os.path.join(os.getcwd(), 'logoSblack.png')
        if os.path.exists(logo_path):
            try:
                await message.answer_photo(
                    photo=FSInputFile(logo_path),
                    caption="🎮 Добро пожаловать!\n\n"
                           "Архив модов by shxin. "
                           "",
                    reply_markup=get_main_keyboard()
                )
            except Exception as e:
                print(f"Ошибка отправки логотипа: {e}")
                await message.answer(
                    "🎮 Добро пожаловать!\n\n"
                    "Архив модов by shxin. "
                    "",
                    reply_markup=get_main_keyboard()
                )
        else:
            await message.answer(
                "🎮 Добро пожаловать!\n\n"
                    "Архив модов by shxin. "
                    "",
                reply_markup=get_main_keyboard()
            )
    finally:
        db.close()

@dp.message(F.text == "📦 Получить ганпак")
async def show_gunpacks(message: types.Message):
    """Показывает список ганпаков"""
    keyboard = get_gunpacks_keyboard()
    await message.answer(
        "📦 Выберите ганпак:",
        reply_markup=keyboard
    )

@dp.message(F.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    """Информация о боте"""
    # Отправляем информацию с логотипом
    logo_path = os.path.join(os.getcwd(), 'logoSblack.png')
    if os.path.exists(logo_path):
        try:
            await message.answer_photo(
                photo=FSInputFile(logo_path),
                caption="ℹ️ **О боте**\n\n"
                       "Этот бот для получения доступа к модам "
                       "Чтобы получить мод, нужно подписаться на указанные каналы(или нет)\n\n"
                       "🔗 **Контакты:**\n"
                       "Если у вас есть вопросы, свяжитесь с администратором - @shxinq",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки логотипа в о боте: {e}")
            await message.answer(
                "ℹ️ **О боте**\n\n"
                "Этот бот для получения доступа к модам "
                "Чтобы получить мод, нужно подписаться на указанные каналы(или нет)\n\n"
                "🔗 **Контакты:**\n"
                "Если у вас есть вопросы, свяжитесь с администратором - @shxinq",
                parse_mode="Markdown"
            )
    else:
        await message.answer(
            "ℹ️ **О боте**\n\n"
            "Этот бот для получения доступа к модам "
            "Чтобы получить мод, нужно подписаться на указанные каналы(или нет)\n\n"
            "🔗 **Контакты:**\n"
            "Если у вас есть вопросы, свяжитесь с администратором - @shxinq",
            parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("gunpack_"))
async def gunpack_details(callback: types.CallbackQuery):
    gunpack_id = int(callback.data.split("_")[1])
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            await callback.answer("Ганпак не найден!", show_alert=True)
            return
        
        # Получаем каналы из JSON
        channels = []
        if gunpack.channels_required:
            try:
                channels = json.loads(gunpack.channels_required)
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга JSON каналов: {e}")
                channels = []
        
        # Если каналы не настроены, сразу даем ссылку
        if not channels:
            # Записываем скачивание
            try:
                user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
                if not user:
                    # Создаем пользователя если его нет
                    user = User(
                        telegram_id=callback.from_user.id,
                        username=callback.from_user.username,
                        first_name=callback.from_user.first_name,
                        last_name=callback.from_user.last_name
                    )
                    db.add(user)
                    db.commit()
                
                download = Download(user_id=user.id, gunpack_id=gunpack.id)
                db.add(download)
                db.commit()
                
                text = f"📦 {gunpack.name}\n\n"
                text += f"{gunpack.description or ''}\n\n"
                text += "🔗 **Ссылка на ганпак:**\n"
                text += f"{gunpack.download_link}\n\n"
                text += "Спасибо за использование нашего бота! 👍"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                ])
                
                # Обрабатываем URL изображения для поддержки разных хостингов
                media_url = None
                is_gif = False
                if gunpack.image_url:
                    try:
                        processed_url = get_direct_image_url(gunpack.image_url)
                        # Проверяем, является ли URL GIF
                        if processed_url.lower().endswith('.gif') or 'gif' in processed_url.lower():
                            is_gif = True
                        media_url = processed_url
                    except Exception as e:
                        print(f"Ошибка обработки URL изображения: {e}")
                
                # Отправляем сообщение с медиа или текстом
                try:
                    if media_url:
                        if is_gif:
                            # Отправляем GIF
                            await callback.message.answer_animation(
                                animation=media_url,
                                caption=text,
                                reply_markup=keyboard,
                                parse_mode="Markdown"
                            )
                        else:
                            # Отправляем фото
                            await callback.message.answer_photo(
                                photo=media_url,
                                caption=text,
                                reply_markup=keyboard,
                                parse_mode="Markdown"
                            )
                    else:
                        # Отправляем только текст
                        await callback.message.answer(
                            text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                except Exception as e:
                    print(f"Ошибка отправки сообщения с медиа: {e}")
                    # Если основная отправка не удалась, пробуем упрощенную версию
                    await callback.message.answer(
                        f"📦 {gunpack.name}\n\n"
                        f"🔗 Ссылка на ганпак:\n"
                        f"{gunpack.download_link}\n\n"
                        "Спасибо за использование нашего бота! 👍",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                        ])
                    )
            except Exception as e:
                print(f"Ошибка при записи скачивания: {e}")
                await callback.message.answer(
                    f"📦 {gunpack.name}\n\n"
                    f"🔗 Ссылка на ганпак:\n"
                    f"{gunpack.download_link}\n\n"
                    "Спасибо за использование нашего бота! 👍",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                    ])
                )
            return
        
        text = f"📦 {gunpack.name}\n\n"
        text += f"{gunpack.description or ''}\n\n"
        text += "📋 Условия получения:\n"
        text += "Подпишитесь на следующие каналы:\n"
        
        # Создаем клавиатуру с кнопками каналов
        channel_buttons = []
        for channel in channels:
            # Очищаем имя канала от @ в начале
            channel_name = channel.lstrip('@')
            
            # Создаем правильный URL для канала
            if channel.startswith('https://t.me/'):
                channel_link = channel
            elif channel.startswith('@'):
                channel_link = f"https://t.me/{channel[1:]}"
            else:
                channel_link = f"https://t.me/{channel_name}"
            
            # Валидация URL
            if channel_link and len(channel_link) > 15:  # Минимальная длина для t.me ссылки
                print(f"Создаю кнопку для канала: {channel_name} -> {channel_link}")
                channel_buttons.append([InlineKeyboardButton(text=f"📺 {channel_name}", url=channel_link)])
            else:
                print(f"Пропускаю невалидный канал: {channel}")
        
        # Добавляем основные кнопки
        channel_buttons.extend([
            [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack.id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=channel_buttons)
        
        # Обрабатываем URL изображения для поддержки разных хостингов
        media_url = None
        is_gif = False
        if gunpack.image_url:
            try:
                processed_url = get_direct_image_url(gunpack.image_url)
                # Проверяем, является ли URL GIF
                if processed_url.lower().endswith('.gif') or 'gif' in processed_url.lower():
                    is_gif = True
                media_url = processed_url
            except Exception as e:
                print(f"Ошибка обработки URL изображения: {e}")
        
        # Отправляем сообщение с медиа или текстом
        try:
            if media_url:
                if is_gif:
                    # Отправляем GIF
                    await callback.message.answer_animation(
                        animation=media_url,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                else:
                    # Отправляем фото
                    await callback.message.answer_photo(
                        photo=media_url,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
            else:
                # Отправляем только текст
                await callback.message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            # Если основная отправка не удалась, пробуем упрощенную версию
            try:
                simple_text = f"📦 {gunpack.name}\n\n{gunpack.description or ''}\n\n📋 Условия получения:\nПодпишитесь на каналы и нажмите 'Проверить подписки'"
                await callback.message.answer(
                    simple_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack.id}")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                    ])
                )
            except Exception as e2:
                print(f"Ошибка отправки упрощенного сообщения: {e2}")
                await callback.message.answer("Произошла ошибка. Попробуйте еще раз.")
        
    except Exception as e:
        print(f"Общая ошибка в gunpack_details: {e}")
        import traceback
        traceback.print_exc()
        await callback.message.answer("Произошла ошибка при загрузке ганпака. Попробуйте еще раз.")
    finally:
        db.close()

@dp.callback_query(F.data.startswith("check_"))
async def check_subscriptions(callback: types.CallbackQuery):
    gunpack_id = int(callback.data.split("_")[1])
    
    # Показываем пользователю, что проверка началась
    await callback.answer("🔄 Проверяю подписки...")
    
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            await callback.message.answer(
                "❌ Ганпак не найден!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                ])
            )
            return
        
        # Получаем каналы из JSON
        channels = []
        if gunpack.channels_required:
            try:
                channels = json.loads(gunpack.channels_required)
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга JSON каналов: {e}")
                channels = []
        
        print(f"Проверка подписок для ганпака {gunpack_id}, каналы: {channels}")
        
        # Если каналы не настроены, сразу даем ссылку
        if not channels:
            # Записываем скачивание
            try:
                user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
                if not user:
                    # Создаем пользователя если его нет
                    user = User(
                        telegram_id=callback.from_user.id,
                        username=callback.from_user.username,
                        first_name=callback.from_user.first_name,
                        last_name=callback.from_user.last_name
                    )
                    db.add(user)
                    db.commit()
                
                download = Download(user_id=user.id, gunpack_id=gunpack.id)
                db.add(download)
                db.commit()
                
                text = f"✅ {gunpack.name}\n\n"
                text += f"🔗 **Ссылка на ганпак:**\n"
                text += f"{gunpack.download_link}\n\n"
                text += "Спасибо за использование нашего бота! 👍"
                
                # Обрабатываем URL изображения для поддержки разных хостингов
                media_url = None
                is_gif = False
                if gunpack.image_url:
                    try:
                        processed_url = get_direct_image_url(gunpack.image_url)
                        # Проверяем, является ли URL GIF
                        if processed_url.lower().endswith('.gif') or 'gif' in processed_url.lower():
                            is_gif = True
                        media_url = processed_url
                    except Exception as e:
                        print(f"Ошибка обработки URL изображения: {e}")
                
                # Отправляем сообщение с медиа или текстом
                try:
                    if media_url:
                        if is_gif:
                            # Отправляем GIF
                            await callback.message.answer_animation(
                                animation=media_url,
                                caption=text,
                                reply_markup=get_main_keyboard(),
                                parse_mode="Markdown"
                            )
                        else:
                            # Отправляем фото
                            await callback.message.answer_photo(
                                photo=media_url,
                                caption=text,
                                reply_markup=get_main_keyboard(),
                                parse_mode="Markdown"
                            )
                    else:
                        # Отправляем только текст
                        await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
                except Exception as e:
                    print(f"Ошибка отправки сообщения с медиа: {e}")
                    # Если основная отправка не удалась, пробуем упрощенную версию
                    await callback.message.answer(
                        f"✅ {gunpack.name}\n\n"
                        f"🔗 Ссылка на ганпак:\n"
                        f"{gunpack.download_link}\n\n"
                        "Спасибо за использование нашего бота! 👍",
                        reply_markup=get_main_keyboard()
                    )
            except Exception as e:
                print(f"Ошибка при записи скачивания: {e}")
                await callback.message.answer(
                    f"✅ {gunpack.name}\n\n"
                    f"🔗 Ссылка на ганпак:\n"
                    f"{gunpack.download_link}\n\n"
                    "Спасибо за использование нашего бота! 👍",
                    reply_markup=get_main_keyboard()
                )
            return
        
        # Проверяем подписки с таймаутом
        try:
            print(f"Начинаю проверку подписок для пользователя {callback.from_user.id}")
            is_subscribed, unsubscribed = await asyncio.wait_for(
                check_subscription(callback.from_user.id, channels),
                timeout=10.0  # 10 секунд таймаут
            )
            print(f"Результат проверки: is_subscribed={is_subscribed}, unsubscribed={unsubscribed}")
        except asyncio.TimeoutError:
            print("Таймаут проверки подписок")
            await callback.message.answer(
                "⏰ Время проверки подписок истекло. Попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack.id}")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                ])
            )
            return
        except Exception as e:
            print(f"Ошибка при проверке подписок: {e}")
            await callback.message.answer(
                "❌ Произошла ошибка при проверке подписок. Попробуйте еще раз.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack.id}")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                ])
            )
            return
        
        # Проверяем, есть ли у gunpack медиа
        has_media = gunpack.image_url is not None and gunpack.image_url.strip() != ""
        
        if is_subscribed:
            # Записываем скачивание
            try:
                user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
                if not user:
                    # Создаем пользователя если его нет
                    user = User(
                        telegram_id=callback.from_user.id,
                        username=callback.from_user.username,
                        first_name=callback.from_user.first_name,
                        last_name=callback.from_user.last_name
                    )
                    db.add(user)
                    db.commit()
                
                download = Download(user_id=user.id, gunpack_id=gunpack.id)
                db.add(download)
                db.commit()
                
                text = f"✅ Отлично! Вы подписаны на все каналы!\n\n"
                text += f"🔗 Ссылка на ганпак {gunpack.name}:\n"
                text += f"{gunpack.download_link}\n\n"
                text += f"Спасибо за подписку! 👍"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                ])
                
                if has_media:
                    print(f"У ганпака есть медиа, отправляем новое сообщение")
                    await callback.message.answer(text, reply_markup=keyboard)
                else:
                    print(f"У ганпака нет медиа, пробуем редактировать сообщение")
                    try:
                        await callback.message.edit_text(text, reply_markup=keyboard)
                    except Exception as e:
                        print(f"Ошибка редактирования сообщения: {e}")
                        await callback.message.answer(text, reply_markup=keyboard)
            except Exception as e:
                print(f"Ошибка при записи скачивания: {e}")
                await callback.message.answer(
                    "✅ Вы подписаны на все каналы! Но произошла ошибка при записи скачивания.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
                    ])
                )
        else:
            # Создаем inline кнопки для каналов
            channel_buttons = []
            for channel in unsubscribed:
                channel_name = channel.lstrip('@')
                if channel.startswith('https://t.me/'):
                    channel_link = channel
                elif channel.startswith('@'):
                    channel_link = f"https://t.me/{channel[1:]}"
                else:
                    channel_link = f"https://t.me/{channel_name}"
                
                # Валидация URL
                if channel_link and len(channel_link) > 15:
                    channel_buttons.append([InlineKeyboardButton(
                        text=f"❌ {channel_name}", 
                        url=channel_link
                    )])
            
            # Добавляем кнопки для подписанных каналов
            subscribed_channels = [c for c in channels if c not in unsubscribed]
            for channel in subscribed_channels:
                channel_name = channel.lstrip('@')
                if channel.startswith('https://t.me/'):
                    channel_link = channel
                elif channel.startswith('@'):
                    channel_link = f"https://t.me/{channel[1:]}"
                else:
                    channel_link = f"https://t.me/{channel_name}"
                
                # Валидация URL
                if channel_link and len(channel_link) > 15:
                    channel_buttons.append([InlineKeyboardButton(
                        text=f"✅ {channel_name}", 
                        url=channel_link
                    )])
            
            # Добавляем кнопки действий
            channel_buttons.extend([
                [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack.id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=channel_buttons)
            
            text = "❌ Вы не подписаны на следующие каналы!\n\n"
            text += "Пожалуйста, подпишитесь на каналы и нажмите 'Проверить подписки' еще раз."
            
            if has_media:
                print(f"У ганпака есть медиа, отправляем новое сообщение")
                await callback.message.answer(text, reply_markup=keyboard)
            else:
                print(f"У ганпака нет медиа, пробуем редактировать сообщение")
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard)
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await callback.message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"Общая ошибка в check_subscriptions: {e}")
        import traceback
        traceback.print_exc()
        await callback.message.answer(
            "❌ Произошла ошибка при проверке подписок. Попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
            ])
        )
    finally:
        db.close()

@dp.callback_query(F.data.startswith("get_gunpack_"))
async def handle_channel_gunpack_callback(callback: types.CallbackQuery):
    """Обрабатывает нажатие на кнопку 'Получить' в канале"""
    await handle_gunpack_callback(callback)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_gunpacks")
async def back_to_gunpacks(callback: types.CallbackQuery):
    keyboard = get_gunpacks_keyboard()
    try:
        await callback.message.edit_text(
            "📦 Выберите ганпак:",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка редактирования сообщения: {e}")
        await callback.message.answer(
            "📦 Выберите ганпак:",
            reply_markup=keyboard
        )
    await callback.answer()

async def handle_gunpack_callback(callback: types.CallbackQuery):
    """Общая функция для обработки ганпаков"""
    await gunpack_details(callback)

async def main():
    """Запуск бота"""
    try:
        # Запускаем обработчик очереди рассылок
        from broadcast_handler import process_broadcast_queue
        asyncio.create_task(process_broadcast_queue())
        
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
