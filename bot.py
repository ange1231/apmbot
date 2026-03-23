import asyncio
import os
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile,
)
from aiogram.filters import Command

from database import get_db, User, Gunpack, Download, Channel
import config

# ---------------------------------------------------------------------------
# Логирование (вместо print везде)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Инициализация бота
# Прокси берётся из .env (PROXY_URL). Если не задан — бот работает без прокси.
# ---------------------------------------------------------------------------
if config.PROXY_URL:
    logger.info("Запуск с прокси: %s", config.PROXY_URL.split('@')[-1])
    session = AiohttpSession(proxy=config.PROXY_URL)
    bot = Bot(token=config.BOT_TOKEN, session=session)
else:
    logger.info("Запуск без прокси")
    bot = Bot(token=config.BOT_TOKEN)

dp = Dispatcher()

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def escape_markdown_v2(text: str) -> str:
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Получить ганпак")],
            [KeyboardButton(text="ℹ️ О боте")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_gunpacks_keyboard() -> InlineKeyboardMarkup:
    db = get_db()
    try:
        gunpacks = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        keyboard = [
            [InlineKeyboardButton(text=f"📦 {gp.name}", callback_data=f"gunpack_{gp.id}")]
            for gp in gunpacks
        ]
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    finally:
        db.close()


def channel_to_url(channel: str) -> str | None:
    if channel.startswith('https://t.me/'):
        link = channel
    elif channel.startswith('@'):
        link = f"https://t.me/{channel[1:]}"
    else:
        link = f"https://t.me/{channel.lstrip('@')}"
    return link if len(link) > 15 else None


def get_direct_image_url(url: str) -> str:
    if 'ibb.co' in url:
        url = url.replace('https://ibb.co/', 'https://i.ibb.co/')
        url = url.replace('http://ibb.co/', 'http://i.ibb.co/')
        if not any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
            url += '.jpg'
    return url


def parse_gunpack_media(gunpack: Gunpack) -> tuple:
    """Возвращает (media_url, is_gif) или (None, False)."""
    if not gunpack.image_url:
        return None, False
    try:
        url = get_direct_image_url(gunpack.image_url)
        is_gif = url.lower().endswith('.gif') or 'gif' in url.lower()
        return url, is_gif
    except Exception as e:
        logger.warning("Ошибка обработки URL изображения: %s", e)
        return None, False


async def send_gunpack_message(target, text: str, keyboard: InlineKeyboardMarkup,
                               gunpack: Gunpack, fallback_text: str = None) -> None:
    """Единая функция отправки: фото/GIF или текст. При ошибке — fallback."""
    media_url, is_gif = parse_gunpack_media(gunpack)
    try:
        if media_url:
            if is_gif:
                await target.answer_animation(animation=media_url, caption=text,
                                              reply_markup=keyboard, parse_mode="Markdown")
            else:
                await target.answer_photo(photo=media_url, caption=text,
                                          reply_markup=keyboard, parse_mode="Markdown")
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        logger.warning("Ошибка отправки с медиа (%s): %s — отправляю текст", media_url, e)
        await target.answer(
            fallback_text or f"📦 {gunpack.name}\n\n🔗 Ссылка:\n{gunpack.download_link}",
            reply_markup=keyboard,
        )


def get_or_create_user(db, tg_user) -> User:
    """Возвращает пользователя из БД или создаёт нового."""
    user = db.query(User).filter(User.telegram_id == str(tg_user.id)).first()
    if not user:
        user = User(
            telegram_id=str(tg_user.id),
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
        )
        db.add(user)
        db.commit()
        logger.info("Новый пользователь: %s (id=%s)", tg_user.username, tg_user.id)
    return user


def record_download(db, user: User, gunpack: Gunpack) -> bool:
    """
    Записывает скачивание только если его ещё не было.
    Возвращает True если запись добавлена, False если уже существует.
    """
    exists = db.query(Download).filter(
        Download.user_id == user.id,
        Download.gunpack_id == gunpack.id,
    ).first()
    if exists:
        logger.info("Повторный запрос ганпака %s от user %s — запись пропущена", gunpack.id, user.id)
        return False
    db.add(Download(user_id=user.id, gunpack_id=gunpack.id))
    db.commit()
    return True


async def check_subscription(user_id: int, channels: list) -> tuple:
    """Проверяет подписки. Возвращает (все_подписаны, список_неподписанных)."""
    unsubscribed = []
    for channel in channels:
        if channel.startswith('@'):
            chat_id = channel
        elif channel.startswith('https://t.me/'):
            chat_id = '@' + channel.split('t.me/')[-1]
        else:
            chat_id = f"@{channel}"
        try:
            logger.debug("Проверка подписки на %s для user_id=%s", chat_id, user_id)
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status not in ('member', 'creator', 'administrator'):
                unsubscribed.append(channel)
        except Exception as e:
            logger.warning("Ошибка проверки подписки на %s: %s", chat_id, e)
            unsubscribed.append(channel)
    return len(unsubscribed) == 0, unsubscribed


def build_channels_keyboard(channels: list, check_callback: str) -> InlineKeyboardMarkup:
    buttons = []
    for channel in channels:
        link = channel_to_url(channel)
        name = channel.lstrip('@').split('/')[-1]
        if link:
            buttons.append([InlineKeyboardButton(text=f"📺 {name}", url=link)])
        else:
            logger.warning("Пропускаю невалидный канал: %s", channel)
    buttons.extend([
        [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=check_callback)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_check_result_keyboard(channels: list, unsubscribed: list, gunpack_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for channel in unsubscribed:
        link = channel_to_url(channel)
        name = channel.lstrip('@').split('/')[-1]
        if link:
            buttons.append([InlineKeyboardButton(text=f"❌ {name}", url=link)])
    for channel in [c for c in channels if c not in unsubscribed]:
        link = channel_to_url(channel)
        name = channel.lstrip('@').split('/')[-1]
        if link:
            buttons.append([InlineKeyboardButton(text=f"✅ {name}", url=link)])
    buttons.extend([
        [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

WELCOME_TEXT = "🎮 Добро пожаловать!\n\nАрхив модов by shxin."
ABOUT_TEXT = (
    "ℹ️ **О боте**\n\n"
    "Этот бот для получения доступа к модам. "
    "Чтобы получить мод, нужно подписаться на указанные каналы (или нет).\n\n"
    "🔗 **Контакты:**\n"
    "Если есть вопросы — пишите администратору: @shxinq"
)
LOGO_PATH = os.path.join(os.getcwd(), 'logoSblack.png')


async def send_with_logo(target, text: str, reply_markup=None, parse_mode: str = None):
    if os.path.exists(LOGO_PATH):
        try:
            await target.answer_photo(
                photo=FSInputFile(LOGO_PATH),
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except Exception as e:
            logger.warning("Не удалось отправить логотип: %s", e)
    await target.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

# ---------------------------------------------------------------------------
# Обработчики
# ---------------------------------------------------------------------------

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db = get_db()
    try:
        get_or_create_user(db, message.from_user)

        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        if args and args[0].startswith('gunpack_'):
            try:
                gunpack_id = int(args[0].split('_')[1])
            except (IndexError, ValueError):
                gunpack_id = None

            if gunpack_id:
                gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
                if gunpack:
                    class MockCallback:
                        data = f"gunpack_{gunpack_id}"
                        from_user = message.from_user
                        message = message
                        async def answer(self, text=None, show_alert=None): pass
                    await gunpack_details(MockCallback())
                    return
            await message.answer("❌ Ганпак не найден!", reply_markup=get_main_keyboard())
            return

        await send_with_logo(message, WELCOME_TEXT, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error("Ошибка в cmd_start: %s", e, exc_info=True)
    finally:
        db.close()


@dp.message(F.text == "📦 Получить ганпак")
async def show_gunpacks(message: types.Message):
    await message.answer("📦 Выберите ганпак:", reply_markup=get_gunpacks_keyboard())


@dp.message(F.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    await send_with_logo(message, ABOUT_TEXT, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("gunpack_"))
async def gunpack_details(callback: types.CallbackQuery):
    try:
        gunpack_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            await callback.answer("Ганпак не найден!", show_alert=True)
            return

        channels = []
        if gunpack.channels_required:
            try:
                channels = json.loads(gunpack.channels_required)
            except json.JSONDecodeError as e:
                logger.error("Ошибка парсинга JSON каналов у ганпака %s: %s", gunpack_id, e)

        # Каналы не требуются — сразу выдаём ссылку
        if not channels:
            user = get_or_create_user(db, callback.from_user)
            record_download(db, user, gunpack)
            text = (
                f"📦 {gunpack.name}\n\n"
                f"{gunpack.description or ''}\n\n"
                f"🔗 **Ссылка на ганпак:**\n{gunpack.download_link}\n\n"
                "Спасибо за использование нашего бота! 👍"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
            ])
            await send_gunpack_message(callback.message, text, keyboard, gunpack)
            return

        text = (
            f"📦 {gunpack.name}\n\n"
            f"{gunpack.description or ''}\n\n"
            "📋 Подпишитесь на следующие каналы:"
        )
        keyboard = build_channels_keyboard(channels, f"check_{gunpack_id}")
        await send_gunpack_message(callback.message, text, keyboard, gunpack)

    except Exception as e:
        logger.error("Ошибка в gunpack_details: %s", e, exc_info=True)
        await callback.message.answer("Произошла ошибка. Попробуйте ещё раз.")
    finally:
        db.close()


@dp.callback_query(F.data.startswith("check_"))
async def check_subscriptions(callback: types.CallbackQuery):
    try:
        gunpack_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректный запрос", show_alert=True)
        return

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

        channels = []
        if gunpack.channels_required:
            try:
                channels = json.loads(gunpack.channels_required)
            except json.JSONDecodeError as e:
                logger.error("Ошибка парсинга JSON каналов: %s", e)

        if not channels:
            user = get_or_create_user(db, callback.from_user)
            record_download(db, user, gunpack)
            text = (
                f"✅ {gunpack.name}\n\n"
                f"🔗 **Ссылка на ганпак:**\n{gunpack.download_link}\n\n"
                "Спасибо! 👍"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
            ])
            await send_gunpack_message(callback.message, text, keyboard, gunpack)
            return

        # Проверяем подписки
        try:
            is_subscribed, unsubscribed = await asyncio.wait_for(
                check_subscription(callback.from_user.id, channels),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Таймаут проверки подписок для user_id=%s", callback.from_user.id)
            await callback.message.answer(
                "⏰ Время проверки истекло. Попробуйте ещё раз.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack_id}")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")],
                ])
            )
            return

        has_media = bool(gunpack.image_url and gunpack.image_url.strip())

        if is_subscribed:
            user = get_or_create_user(db, callback.from_user)
            record_download(db, user, gunpack)  # дублей нет — проверяет внутри

            text = (
                f"✅ Отлично! Вы подписаны на все каналы!\n\n"
                f"🔗 Ссылка на {gunpack.name}:\n{gunpack.download_link}\n\n"
                "Спасибо за подписку! 👍"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")]
            ])
            if has_media:
                await callback.message.answer(text, reply_markup=keyboard)
            else:
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard)
                except Exception:
                    await callback.message.answer(text, reply_markup=keyboard)
        else:
            text = (
                "❌ Вы не подписаны на все каналы!\n\n"
                "Подпишитесь и нажмите «Проверить подписки» ещё раз."
            )
            keyboard = build_check_result_keyboard(channels, unsubscribed, gunpack_id)
            if has_media:
                await callback.message.answer(text, reply_markup=keyboard)
            else:
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard)
                except Exception:
                    await callback.message.answer(text, reply_markup=keyboard)

    except Exception as e:
        logger.error("Ошибка в check_subscriptions: %s", e, exc_info=True)
        await callback.message.answer(
            "❌ Ошибка при проверке подписок. Попробуйте ещё раз.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Проверить подписки", callback_data=f"check_{gunpack_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_gunpacks")],
            ])
        )
    finally:
        db.close()


@dp.callback_query(F.data.startswith("get_gunpack_"))
async def handle_channel_gunpack_callback(callback: types.CallbackQuery):
    await gunpack_details(callback)


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "back_to_gunpacks")
async def back_to_gunpacks(callback: types.CallbackQuery):
    keyboard = get_gunpacks_keyboard()
    try:
        await callback.message.edit_text("📦 Выберите ганпак:", reply_markup=keyboard)
    except Exception:
        await callback.message.answer("📦 Выберите ганпак:", reply_markup=keyboard)
    await callback.answer()

# ---------------------------------------------------------------------------
# Внутренний HTTP API — сайт обращается сюда для проверки подписок
# Слушает только 127.0.0.1 (не доступен снаружи)
# ---------------------------------------------------------------------------

from aiohttp import web as aiohttp_web

async def _handle_check_subscription(request: aiohttp_web.Request) -> aiohttp_web.Response:
    """
    POST /internal/check-subscription
    Body JSON: { "secret": "...", "telegram_id": 123, "gunpack_id": 1 }
    Response:  { "subscribed": true/false, "channels": [...], "download_link": "..." }
    """
    try:
        data = await request.json()
    except Exception:
        return aiohttp_web.json_response({"error": "invalid_json"}, status=400)

    # Проверка секрета
    if data.get("secret") != config.BOT_API_SECRET:
        return aiohttp_web.json_response({"error": "forbidden"}, status=403)

    telegram_id = data.get("telegram_id")
    gunpack_id  = data.get("gunpack_id")

    if not telegram_id or not gunpack_id:
        return aiohttp_web.json_response({"error": "missing_fields"}, status=400)

    # Достаём ганпак из БД
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            return aiohttp_web.json_response({"error": "gunpack_not_found"}, status=404)

        channels = []
        if gunpack.channels_required:
            try:
                channels = json.loads(gunpack.channels_required)
            except json.JSONDecodeError:
                channels = []

        # Если каналов нет — сразу разрешаем
        if not channels:
            return aiohttp_web.json_response({
                "subscribed": True,
                "channels": [],
                "download_link": gunpack.download_link,
            })

        # Проверяем подписку через Telegram
        try:
            is_subscribed, unsubscribed = await asyncio.wait_for(
                check_subscription(telegram_id, channels),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            return aiohttp_web.json_response({"error": "timeout"}, status=504)

        # Формируем список каналов с флагом подписки для фронтенда
        channel_info = []
        for ch in channels:
            name = ch.lstrip('@').split('/')[-1]
            if ch.startswith('https://t.me/'):
                url = ch
            elif ch.startswith('@'):
                url = f"https://t.me/{ch[1:]}"
            else:
                url = f"https://t.me/{ch.lstrip('@')}"
            channel_info.append({
                "name": name,
                "url": url,
                "subscribed": ch not in unsubscribed,
            })

        result = {
            "subscribed": is_subscribed,
            "channels": channel_info,
        }
        if is_subscribed:
            result["download_link"] = gunpack.download_link

        return aiohttp_web.json_response(result)

    except Exception as e:
        logger.error("Ошибка в internal API check-subscription: %s", e, exc_info=True)
        return aiohttp_web.json_response({"error": "internal"}, status=500)
    finally:
        db.close()


async def start_internal_api():
    """Запускает внутренний HTTP-сервер на 127.0.0.1:{BOT_API_PORT}."""
    app_api = aiohttp_web.Application()
    app_api.router.add_post('/internal/check-subscription', _handle_check_subscription)
    runner = aiohttp_web.AppRunner(app_api)
    await runner.setup()
    site = aiohttp_web.TCPSite(runner, '127.0.0.1', config.BOT_API_PORT)
    await site.start()
    logger.info("Внутренний API запущен на 127.0.0.1:%s", config.BOT_API_PORT)




# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------

async def main():
    logger.info("Запуск бота...")
    from broadcast_handler import process_broadcast_queue
    await start_internal_api()
    asyncio.create_task(process_broadcast_queue())
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
