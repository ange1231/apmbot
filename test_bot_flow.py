"""
Тестовый скрипт для проверки работы бота
Проверяет сценарии:
1. Ганпак без каналов - должна быть прямая ссылка
2. Ганпак с каналами - проверка подписок
3. Подписанный пользователь - должна быть ссылка
"""

import json
from database import get_db, Gunpack, Channel

def test_gunpack_scenarios():
    """Проверяем различные сценарии ганпаков"""
    db = get_db()
    try:
        print("Testing gunpack scenarios...")
        
        # Получаем все ганпаки
        gunpacks = db.query(Gunpack).all()
        
        for gunpack in gunpacks:
            print(f"\nGunpack: {gunpack.name}")
            print(f"   ID: {gunpack.id}")
            print(f"   Active: {gunpack.is_active}")
            
            # Проверяем каналы
            if gunpack.channels_required:
                try:
                    channels = json.loads(gunpack.channels_required)
                    print(f"   Channels: {channels}")
                    
                    if channels:
                        print("   Requires subscription check")
                    else:
                        print("   Empty channels array - direct link")
                except json.JSONDecodeError as e:
                    print(f"   JSON error: {e}")
                    print("   Will be direct link")
            else:
                print("   No channels - direct link")
            
            print(f"   Link: {gunpack.download_link}")
        
        # Проверяем активные каналы
        print(f"\nActive channels:")
        active_channels = db.query(Channel).filter(Channel.is_active == True).all()
        for channel in active_channels:
            print(f"   - @{channel.name} ({channel.title})")
        
        if not active_channels:
            print("   No active channels")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_gunpack_scenarios()
