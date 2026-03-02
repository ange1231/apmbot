#!/usr/bin/env python3
"""
Тестирование поддержки изображений и GIF
"""

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

def is_gif_url(url: str) -> bool:
    """Проверяет, является ли URL GIF"""
    return url.lower().endswith('.gif') or 'gif' in url.lower()

# Тестовые URL
test_urls = [
    "https://ibb.co/abc123",
    "https://ibb.co/album/test123",
    "https://i.postimg.cc/VvKGs4FK/0001-02020-ezgif-com-optimize.gif",
    "https://ezgif.com/optimize.gif",
    "https://i.ibb.co/already-direct.jpg",
    "https://example.com/image.png"
]

print("Тестирование преобразования URL изображений и GIF:")
print("=" * 60)

for url in test_urls:
    converted = get_direct_image_url(url)
    is_gif = is_gif_url(converted)
    media_type = "GIF" if is_gif else "Image"
    
    print(f"Оригинал: {url}")
    print(f"Результат: {converted}")
    print(f"Тип: {media_type}")
    print("-" * 40)
