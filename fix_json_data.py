import json
from database import get_db, Gunpack

def fix_gunpack_channels():
    """Исправляет невалидные JSON данные в поле channels_required"""
    db = get_db()
    try:
        gunpacks = db.query(Gunpack).all()
        
        for gunpack in gunpacks:
            if gunpack.channels_required:
                print(f"Проверка ганпака {gunpack.id}: {gunpack.name}")
                print(f"Текущее значение: {gunpack.channels_required}")
                
                try:
                    # Проверяем валидность JSON
                    channels = json.loads(gunpack.channels_required)
                    print(f"JSON валидный: {channels}")
                except json.JSONDecodeError as e:
                    print(f"Ошибка JSON: {e}")
                    
                    # Пытаемся исправить данные
                    try:
                        # Если данные выглядят как простой текст, пробуем преобразовать
                        if gunpack.channels_required.startswith('[') and gunpack.channels_required.endswith(']'):
                            # Возможно, это уже массив, но с ошибками
                            cleaned = gunpack.channels_required.replace("'", '"').replace(' ', '')
                            try:
                                json.loads(cleaned)
                                gunpack.channels_required = cleaned
                                print(f"Исправлено на: {cleaned}")
                            except:
                                # Если все еще ошибка, создаем пустой массив
                                gunpack.channels_required = '[]'
                                print("Установлено пустое значение")
                        else:
                            # Если это не массив, создаем массив из строки
                            gunpack.channels_required = json.dumps([gunpack.channels_required])
                            print(f"Преобразовано в массив: {gunpack.channels_required}")
                    except Exception as fix_error:
                        print(f"Ошибка исправления: {fix_error}")
                        gunpack.channels_required = '[]'
                
                db.commit()
                print("---")
        
        print("Исправление завершено!")
        
    finally:
        db.close()

if __name__ == "__main__":
    fix_gunpack_channels()
