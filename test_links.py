#!/usr/bin/env python3
"""
Тестирование кликабельных ссылок для Telegram
"""

def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2"""
    special_chars = '_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_channel_link(channel: str) -> str:
    """Форматирует ссылку на канал"""
    channel_link = channel if channel.startswith('https://') else f"https://t.me/{channel.replace('@', '')}"
    return f"[{escape_markdown_v2(channel)}]({channel_link})"

# Тестовые каналы
test_channels = [
    "@channel1",
    "@my_awesome_channel",
    "channel_with-dashes",
    "https://t.me/direct_channel"
]

print("Тестирование форматирования ссылок:")
print("=" * 50)

for channel in test_channels:
    formatted = format_channel_link(channel)
    print(f"Канал: {channel}")
    print(f"Ссылка: {formatted}")
    print("-" * 30)

# Тест полного сообщения
print("\nПример полного сообщения:")
print("=" * 50)

channels = ["@channel1", "@channel2"]
text = "Gunpack Test\n\n"
text += "Conditions:\n"
text += "Subscribe to channels:\n"

for channel in channels:
    channel_link = channel if channel.startswith('https://') else f"https://t.me/{channel.replace('@', '')}"
    text += f"• [{escape_markdown_v2(channel)}]({channel_link})\n"

print(text)
