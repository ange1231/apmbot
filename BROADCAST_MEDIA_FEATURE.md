# 📸 Медиа в рассылках - Фото, GIF и YouTube

## 🎯 Что добавлено

### Возможность прикреплять медиа к рассылкам в Telegram каналы:
- ✅ **Фото** - прямые ссылки на изображения
- ✅ **GIF** - анимированные изображения
- ✅ **YouTube** - ссылки на видео в тексте сообщения

## 🚀 Как это работает

### 1. Создание рассылки с медиа
```
Админ панель → 📤 Рассылка в ТГ → Выбор ганпака → Текст → Медиа → Каналы → Отправка
```

### 2. Типы медиа
- **Фото**: `https://example.com/image.jpg`
- **GIF**: `https://example.com/animation.gif`
- **YouTube**: `https://youtube.com/watch?v=...`

### 3. Отправка в каналы
```
Бот определяет тип медиа → Отправляет с соответствующим методом → Добавляет кнопку "Получить"
```

## 🎨 Обновленная форма рассылки

### Новые поля:
```html
<!-- Тип медиа -->
<select name="media_type">
    <option value="">Без медиа</option>
    <option value="photo">Фото</option>
    <option value="gif">GIF</option>
    <option value="youtube">YouTube видео</option>
</select>

<!-- URL медиа (появляется при выборе типа) -->
<input type="url" name="media_url" placeholder="https://...">
```

### JavaScript для динамического поля:
```javascript
document.getElementById('media_type').addEventListener('change', function() {
    const mediaUrlContainer = document.getElementById('media_url_container');
    if (this.value) {
        mediaUrlContainer.style.display = 'block';
        mediaUrl.required = true;
    } else {
        mediaUrlContainer.style.display = 'none';
        mediaUrl.required = false;
    }
});
```

## 🔧 Техническая реализация

### 1. Обновленный обработчик в app.py
```python
if request.method == 'POST':
    gunpack_id = request.form['gunpack_id']
    message_text = request.form['message_text']
    selected_channels = request.form.getlist('channels')
    media_type = request.form.get('media_type', '')
    media_url = request.form.get('media_url', '')
    
    # Валидация
    if media_type and not media_url:
        flash('Укажите URL медиа!', 'error')
        return redirect(url_for('broadcast'))
    
    # Добавление в очередь
    await add_broadcast_to_queue(
        int(gunpack_id), 
        message_text, 
        selected_channels,
        media_type,
        media_url
    )
```

### 2. Обновленный broadcast_handler.py
```python
async def send_broadcast_to_channels(gunpack_id, message_text, selected_channels, media_type='', media_url=''):
    # Формируем сообщение
    text = f"{message_text}\n\n📦 **{gunpack.name}**\n{gunpack.description or ''}"
    
    # Создаем кнопку
    deep_link = f"https://t.me/{bot_username}?start=gunpack_{gunpack.id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 Получить {gunpack.name}", url=deep_link)]
    ])
    
    # Отправляем с медиа или без
    if media_type and media_url:
        if media_type == 'photo':
            await bot.send_photo(chat_id, photo=media_url, caption=text, reply_markup=keyboard)
        elif media_type == 'gif':
            await bot.send_animation(chat_id, animation=media_url, caption=text, reply_markup=keyboard)
        elif media_type == 'youtube':
            youtube_text = f"{text}\n\n🎥 [Смотреть видео]({media_url})"
            await bot.send_message(chat_id, text=youtube_text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text=text, reply_markup=keyboard)
```

## 📱 Примеры рассылок

### 1. Рассылка с фото
```
[📷 Фото]
🔥 Новый ганпак доступен!

📦 WAVE ANIM GP by shxin
Анимированные волны для вашего интерфейса

[📦 Получить WAVE ANIM GP by shxin]
```

### 2. Рассылка с GIF
```
[🎬 GIF анимация]
🌟 Эксклюзивный ганпак!

📦 CRYSTAL UI GP
Прозрачный интерфейс с анимацией

[📦 Получить CRYSTAL UI GP]
```

### 3. Рассылка с YouTube
```
🔥 Новый ганпак доступен!

📦 PRO GAMING GP
Лучший ганпак для геймеров

🎥 Смотреть видео: https://youtube.com/watch?v=...

[📦 Получить PRO GAMING GP]
```

## 🎯 Преимущества

### 1. **Визуальная привлекательность:**
- ✅ **Фото** привлекают внимание
- ✅ **GIF** демонстрируют анимацию
- ✅ **YouTube** показывают функционал

### 2. **Гибкость:**
- ✅ **Необязательное поле** - можно отправлять без медиа
- ✅ **Динамический интерфейс** - поле URL появляется только при выборе типа
- ✅ **Валидация** - проверка обязательных полей

### 3. **Универсальность:**
- ✅ **Прямые ссылки** на изображения
- ✅ **Поддержка YouTube** через markdown
- ✅ **Автоматическое определение** типа контента

## 🔄 Измененные файлы

### 1. `templates/broadcast_dark.html`
```html
<!-- Добавлены поля для медиа -->
<div class="mb-3">
    <label for="media_type" class="form-label text-white">Тип медиа (опционально)</label>
    <select class="form-select bg-dark text-white border-secondary" id="media_type" name="media_type">
        <option value="">Без медиа</option>
        <option value="photo">Фото</option>
        <option value="gif">GIF</option>
        <option value="youtube">YouTube видео</option>
    </select>
</div>

<div class="mb-3" id="media_url_container" style="display: none;">
    <label for="media_url" class="form-label text-white">URL медиа</label>
    <input type="url" class="form-control bg-dark text-white border-secondary" 
           id="media_url" name="media_url" placeholder="https://...">
</div>

<!-- JavaScript для динамического поля -->
<script>
document.getElementById('media_type').addEventListener('change', function() {
    const mediaUrlContainer = document.getElementById('media_url_container');
    if (this.value) {
        mediaUrlContainer.style.display = 'block';
        mediaUrl.required = true;
    } else {
        mediaUrlContainer.style.display = 'none';
        mediaUrl.required = false;
    }
});
</script>
```

### 2. `app.py` - маршрут `/broadcast`
```python
# Добавлена обработка медиа
media_type = request.form.get('media_type', '')
media_url = request.form.get('media_url', '')

# Валидация
if media_type and not media_url:
    flash('Укажите URL медиа!', 'error')
    return redirect(url_for('broadcast'))

# Передача в обработчик
await add_broadcast_to_queue(
    int(gunpack_id), 
    message_text, 
    selected_channels,
    media_type,
    media_url
)
```

### 3. `broadcast_handler.py`
```python
# Обновлена функция отправки
async def send_broadcast_to_channels(gunpack_id, message_text, selected_channels, media_type='', media_url=''):
    if media_type == 'photo':
        await bot.send_photo(chat_id, photo=media_url, caption=text, reply_markup=keyboard)
    elif media_type == 'gif':
        await bot.send_animation(chat_id, animation=media_url, caption=text, reply_markup=keyboard)
    elif media_type == 'youtube':
        youtube_text = f"{text}\n\n🎥 [Смотреть видео]({media_url})"
        await bot.send_message(chat_id, text=youtube_text, reply_markup=keyboard)
```

## 🚀 Как использовать

### 1. Создание рассылки с фото:
1. **Выберите ганпак**
2. **Напишите текст сообщения**
3. **Выберите "Фото"** в типе медиа
4. **Вставьте URL изображения**
5. **Выберите каналы**
6. **Отправьте рассылку**

### 2. Создание рассылки с GIF:
1. **Выберите ганпак**
2. **Напишите текст сообщения**
3. **Выберите "GIF"** в типе медиа
4. **Вставьте URL GIF**
5. **Выберите каналы**
6. **Отправьте рассылку**

### 3. Создание рассылки с YouTube:
1. **Выберите ганпак**
2. **Напишите текст сообщения**
3. **Выберите "YouTube видео"** в типе медиа
4. **Вставьте URL YouTube**
5. **Выберите каналы**
6. **Отправьте рассылку**

## 📊 Поддерживаемые форматы

### Фото:
- ✅ **JPG/JPEG**
- ✅ **PNG**
- ✅ **WEBP**
- ✅ **GIF** (как статичное изображение)

### Анимация:
- ✅ **GIF** (как анимация)
- ✅ **MP4** (через GIF)

### YouTube:
- ✅ **youtube.com/watch?v=...**
- ✅ **youtu.be/...**
- ✅ **Любые YouTube ссылки**

## 🎯 Результат

Теперь рассылки стали гораздо более привлекательными:
- ✅ **Визуальный контент** привлекает внимание
- ✅ **Демонстрация** функционала через видео
- ✅ **Гибкие настройки** медиа
- ✅ **Сохранение функциональности** кнопки "Получить"
- ✅ **Темная тема** и удобный интерфейс

Рассылки с медиа готовы к использованию! 🎉📸
