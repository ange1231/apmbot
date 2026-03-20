from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import json
from datetime import datetime
import config
from database import get_db, User, Gunpack, Download, Channel, GunpackChannel, init_default_channels
import os
import asyncio

# --- 1. Инициализация приложения ---
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['DEBUG'] = True

# --- 2. Настройка безопасности ---
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    try:
        return db.query(User).filter(User.id == int(user_id)).first()
    finally:
        db.close()

# --- 3. Функции-помощники ---
def admin_required(f):
    """Декоратор для проверки прав администратора"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('У вас нет прав для доступа к этой странице.', 'error')
            return redirect(url_for('statistics'))
        return f(*args, **kwargs)
    return decorated_function

# --- 4. Роуты авторизации ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user and user.password_hash and bcrypt.check_password_hash(user.password_hash, password):
                login_user(user)
                flash('Вы успешно вошли!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Неверный логин или пароль', 'error')
        finally:
            db.close()
    return render_template('login_dark.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# --- 5. Основные страницы панели ---
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
@admin_required
def dashboard():
    init_default_channels()
    db = get_db()
    try:
        users_count = db.query(User).count()
        gunpacks_count = db.query(Gunpack).filter(Gunpack.is_active == True).count()
        channels_count = db.query(Channel).filter(Channel.is_active == True).count()
        total_downloads = db.query(Download).count()
        
        recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
        recent_downloads = db.query(Download).order_by(Download.downloaded_at.desc()).limit(5).all()
        
        return render_template('dashboard_dark.html', 
                             users_count=users_count,
                             gunpacks_count=gunpacks_count,
                             channels_count=channels_count,
                             total_downloads=total_downloads,
                             recent_users=recent_users,
                             recent_downloads=recent_downloads)
    finally:
        db.close()

@app.route('/users')
@login_required
@admin_required
def users():
    db = get_db()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        return render_template('users_dark.html', users=users)
    finally:
        db.close()

@app.route('/statistics')
@login_required
def statistics():
    db = get_db()
    try:
        total_users = db.query(User).count()
        gunpacks = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        stats = []
        for gunpack in gunpacks:
            downloads_count = db.query(Download).filter(Download.gunpack_id == gunpack.id).count()
            unique_users_count = db.query(Download).filter(Download.gunpack_id == gunpack.id).distinct(Download.user_id).count()
            stats.append({
                'gunpack': gunpack,
                'downloads_count': downloads_count,
                'unique_users_count': unique_users_count
            })
        return render_template('statistics_dark.html', stats=stats, total_users=total_users)
    finally:
        db.close()

# --- 6. Управление Ганпаками ---
@app.route('/gunpacks')
@login_required
@admin_required
def gunpacks():
    db = get_db()
    try:
        gunpacks = db.query(Gunpack).order_by(Gunpack.created_at.desc()).all()
        return render_template('gunpacks_dark_fixed.html', gunpacks=gunpacks)
    finally:
        db.close()

@app.route('/gunpacks/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_gunpack():
    if request.method == 'POST':
        db = get_db()
        try:
            selected_channels = request.form.getlist('channels')
            gunpack = Gunpack(
                name=request.form['name'],
                description=request.form['description'],
                image_url=request.form['image_url'],
                download_link=request.form['download_link'],
                channels_required=json.dumps(selected_channels),
                is_active='is_active' in request.form,
                created_at=datetime.utcnow()
            )
            db.add(gunpack)
            db.commit()
            flash('Ганпак успешно добавлен!', 'success')
            return redirect(url_for('gunpacks'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')
        finally:
            db.close()
    
    db = get_db()
    try:
        all_channels = db.query(Channel).all()
        return render_template('gunpack_form_dark.html', gunpack=None, all_channels=all_channels, gunpack_channels=[])
    finally:
        db.close()

@app.route('/gunpacks/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_gunpack(id):
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if not gunpack:
            flash('Ганпак не найден!', 'error')
            return redirect(url_for('gunpacks'))
        
        if request.method == 'POST':
            gunpack.name = request.form['name']
            gunpack.description = request.form['description']
            gunpack.image_url = request.form['image_url']
            gunpack.download_link = request.form['download_link']
            selected_channels = request.form.getlist('channels')
            gunpack.channels_required = json.dumps(selected_channels)
            gunpack.is_active = 'is_active' in request.form
            gunpack.updated_at = datetime.utcnow()
            db.commit()
            flash('Ганпак успешно обновлен!', 'success')
            return redirect(url_for('gunpacks'))
        
        all_channels = db.query(Channel).all()
        gunpack_channels = json.loads(gunpack.channels_required) if gunpack.channels_required else []
        return render_template('gunpack_form_dark.html', gunpack=gunpack, all_channels=all_channels, gunpack_channels=gunpack_channels)
    finally:
        db.close()

# --- 7. Каналы и Рассылка ---
@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
@admin_required
def broadcast():
    db = get_db()
    try:
        if request.method == 'POST':
            gunpack_id = request.form.get('gunpack_id')
            message_text = request.form.get('message_text')
            selected_channels = request.form.getlist('channels')
            
            if not gunpack_id or not message_text or not selected_channels:
                flash('Заполните все поля!', 'error')
                return redirect(url_for('broadcast'))
            
            from broadcast_handler import send_broadcast_to_channels
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(send_broadcast_to_channels(
                    int(gunpack_id), message_text, selected_channels, 
                    request.form.get('media_type', ''), request.form.get('media_url', '')
                ))
                flash('Рассылка запущена!', 'success')
            finally:
                loop.close()
            return redirect(url_for('dashboard'))

        gunpacks = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        return render_template('broadcast_dark.html', gunpacks=gunpacks, channels=channels)
    finally:
        db.close()

# Добавь @login_required и @admin_required к остальным роутам (delete, toggle, channels) по аналогии.

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
