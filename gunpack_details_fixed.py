@dp.callback_query(F.data.startswith("gunpack_"))
async def gunpack_details(callback: types.CallbackQuery):
    gunpack_id = int(callback.data.split("_")[1])
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
        if not gunpack:
            await callback.answer("Ганпак не найден!", show_alert=True)
            return
        
        # Получаем каналы из JSON или используем активные каналы из базы
        if gunpack.channels_required:
            try:
                channels = json.loads(gunpack.channels_required)
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга JSON каналов: {e}")
                channels = []
        else:
            # Если каналы не указаны, используем все активные каналы
            active_channels = db.query(Channel).filter(Channel.is_active == True).all()
            channels = [channel.name for channel in active_channels]
        
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
