from database import get_db, User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
db = get_db()

def create_root_admin():
    # Проверяем, есть ли уже админ
    admin = db.query(User).filter(User.username == 'admin').first()
    if not admin:
        hashed_password = bcrypt.generate_password_hash('твой_пароль_тут').decode('utf-8')
        new_admin = User(
            username='admin',
            password_hash=hashed_password,
            role='admin',
            is_verified=True,
            telegram_id=0 # Заглушка
        )
        db.add(new_admin)
        db.commit()
        print("✅ Админ создан успешно!")
    else:
        print("ℹ️ Админ уже существует.")

if __name__ == "__main__":
    create_root_admin()
