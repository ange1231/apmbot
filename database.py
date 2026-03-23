from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config
from flask_login import UserMixin
Base = declarative_base()

class User(Base, UserMixin): # Добавляем UserMixin
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, index=True) # nullable=True, т.к. админ может быть не из ТГ
    username = Column(String(255), unique=True) # Логин для входа на сайт
    password_hash = Column(String(255)) # Хэш пароля
    role = Column(String(50), default='user') # 'admin' или 'user'
    first_name = Column(String(255))
    last_name = Column(String(255))
    is_admin = Column(Boolean, default=False)
    email = Column(String(255), unique=True)
    is_verified = Column(Boolean, default=False)
    two_factor_secret = Column(String(32)) 
    
    created_at = Column(DateTime, default=datetime.utcnow)
    downloads = relationship("Download", back_populates="user")
class Channel(Base):
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)  # @channel_name
    title = Column(String(255), nullable=False)  # Название канала
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    gunpacks = relationship("Gunpack", secondary="gunpack_channels", back_populates="channels")

class GunpackChannel(Base):
    __tablename__ = 'gunpack_channels'
    
    id = Column(Integer, primary_key=True)
    gunpack_id = Column(Integer, ForeignKey('gunpacks.id'), nullable=False)
    channel_id = Column(Integer, ForeignKey('channels.id'), nullable=False)

class Gunpack(Base):
    __tablename__ = 'gunpacks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    download_link = Column(String(500), nullable=False)
    channels_required = Column(Text)  # Оставляем для обратной совместимости
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    downloads = relationship("Download", back_populates="gunpack")
    channels = relationship("Channel", secondary="gunpack_channels", back_populates="gunpacks")

class Download(Base):
    __tablename__ = 'downloads'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    gunpack_id = Column(Integer, ForeignKey('gunpacks.id'), nullable=False)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="downloads")
    gunpack = relationship("Gunpack", back_populates="downloads")

# Создание базы данных
engine = create_engine(f'sqlite:///{config.DB_PATH}')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

class _DbContextManager:
    """Позволяет использовать get_db() и как обычную сессию (bot.py),
    и как контекстный менеджер: with get_db() as db: (app.py)."""
    def __init__(self):
        self._session = Session()

    # Проброс всех атрибутов SQLAlchemy-сессии
    def __getattr__(self, name):
        return getattr(self._session, name)

    # Поддержка with-блока
    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._session.rollback()
        self._session.close()
        return False

    def close(self):
        self._session.close()

def get_db():
    return _DbContextManager()

def init_default_channels():
    """Инициализация каналов по умолчанию"""
    db = get_db()
    try:
        # Проверяем, есть ли уже каналы
        if db.query(Channel).count() == 0:
            default_channels = [
                Channel(name='@channel1', title='Channel 1', description='Первый канал для подписки'),
                Channel(name='@channel2', title='Channel 2', description='Второй канал для подписки'),
                Channel(name='@channel3', title='Channel 3', description='Третий канал для подписки')
            ]
            for channel in default_channels:
                db.add(channel)
            db.commit()
            print("Каналы по умолчанию созданы")
    finally:
        db.close()
