from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import json
import hmac
import hashlib
from datetime import datetime
import config
from database import get_db, User, Gunpack, Download, Channel, init_default_channels
import os
from functools import wraps
from urllib.parse import parse_qsl
import threading
import asyncio
# --- 1. Инициализация приложения ---
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ID главного администратора берётся из .env (ADMIN_ID)
ADMIN_ID = config.ADMIN_ID

# --- 2. Настройка безопасности ---

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin_password'

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    with get_db() as db:
        return db.query(User).filter(User.id == int(user_id)).first()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('У вас нет прав для доступа к этой странице.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
def run_async_in_background(coroutine):
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coroutine)
        finally:
            loop.close()
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
def verify_telegram_data(init_data):
    try:
        vals = dict(parse_qsl(init_data))
        if 'hash' not in vals:
            return None
        
        hash_str = vals.pop('hash')
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(vals.items())])
        
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        hmac_check = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if hmac_check == hash_str:
            return json.loads(vals.get('user'))
        return None
    except Exception as e:
        print(f"Auth error: {e}")
        return None

# --- 3. Авторизация ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if user and user.password_hash and bcrypt.check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Неверный логин или пароль', 'error')
    return render_template('login_dark.html')

@app.route('/auth-tg', methods=['POST'])
def auth_tg():
    data = request.json
    init_data = data.get('initData')
    user_info = verify_telegram_data(init_data)
    
    if user_info:
        tg_id_int = user_info.get('id')
        tg_id_str = str(tg_id_int)
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == tg_id_str).first()
            target_role = 'admin' if tg_id_int == ADMIN_ID else 'user'
            
            if not user:
                user = User(
                    telegram_id=tg_id_str, 
                    username=user_info.get('username', f"User_{tg_id_str}"), 
                    role=target_role,
                    created_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            elif user.role != target_role:
                user.role = target_role
                db.commit()

            login_user(user)
            return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- 4. Основные страницы ---
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    with get_db() as db:
        users_count = db.query(User).count()
        gunpacks_count = db.query(Gunpack).count()
        channels_count = db.query(Channel).count()
        total_downloads = db.query(Download).count()

        if current_user.role == 'admin':
            recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
            recent_downloads = db.query(Download).order_by(Download.downloaded_at.desc()).limit(5).all()
            
            return render_template('dashboard_dark.html', 
                                   users_count=users_count, gunpacks_count=gunpacks_count,
                                   channels_count=channels_count, total_downloads=total_downloads,
                                   recent_users=recent_users, recent_downloads=recent_downloads)
        
        gunpacks_list = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        return render_template('user_dashboard.html', 
                               users_count=users_count, gunpacks_count=gunpacks_count,
                               total_downloads=total_downloads, gunpacks=gunpacks_list)

@app.route('/users')
@login_required
@admin_required
@requires_auth
def users():
    with get_db() as db:
        users_list = db.query(User).order_by(User.created_at.desc()).all()
        return render_template('users_dark.html', users=users_list)

@app.route('/statistics')
@login_required
@admin_required
@requires_auth
def statistics():
    with get_db() as db:
        total_users = db.query(User).count()
        gunpacks = db.query(Gunpack).all()
        stats = [{'gunpack': gp, 'downloads_count': db.query(Download).filter(Download.gunpack_id == gp.id).count()} for gp in gunpacks]
        return render_template('statistics_dark.html', stats=stats, total_users=total_users)

# --- 5. Управление Ганпаками ---
@app.route('/gunpacks')
@login_required

def gunpacks():
    with get_db() as db:
        gunpacks_list = db.query(Gunpack).order_by(Gunpack.created_at.desc()).all()
        return render_template('gunpacks_dark_fixed.html', gunpacks=gunpacks_list)

@app.route('/gunpacks/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
@requires_auth
def delete_gunpack(id):
    with get_db() as db:
        gp = db.query(Gunpack).get(id)
        if gp:
            db.delete(gp)
            db.commit()
            flash('Ганпак удален', 'success')
        return redirect(url_for('gunpacks'))

@app.route('/gunpacks/new', methods=['GET', 'POST'])
@login_required
@admin_required
@requires_auth
def new_gunpack():
    with get_db() as db:
        if request.method == 'POST':
            selected_channels = request.form.getlist('channels')
            gunpack = Gunpack(
                name=request.form['name'],
                description=request.form['description'],
                image_url=request.form['image_url'],
                download_link=request.form['download_link'],
                is_active='is_active' in request.form,
                created_at=datetime.utcnow()
            )
            db.add(gunpack)
            db.flush()  # Получаем ID
            
            # ✅ ORM вместо JSON
            for channel_name in selected_channels:
                channel = db.query(Channel).filter(Channel.name == channel_name).first()
                if channel:
                    gunpack.channels.append(channel)
            
            db.commit()
            flash('Ганпак успешно добавлен!', 'success')
            return redirect(url_for('gunpacks'))
        
        all_channels = db.query(Channel).all()
        return render_template('gunpack_form_dark.html', gunpack=None, all_channels=all_channels, gunpack_channels=[])
@app.route('/gunpacks/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
@requires_auth
def edit_gunpack(id):
    with get_db() as db:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if not gunpack:
            flash('Ганпак не найден!', 'error')
            return redirect(url_for('gunpacks'))
        
        if request.method == 'POST':
            gunpack.name = request.form['name']
            gunpack.description = request.form['description']
            gunpack.image_url = request.form['image_url']
            gunpack.download_link = request.form['download_link']
            gunpack.is_active = 'is_active' in request.form
            gunpack.updated_at = datetime.utcnow()
            
            # ✅ Очищаем старые связи
            gunpack.channels.clear()
            
            # ✅ Добавляем новые через ORM
            selected_channels = request.form.getlist('channels')
            for channel_name in selected_channels:
                channel = db.query(Channel).filter(Channel.name == channel_name).first()
                if channel:
                    gunpack.channels.append(channel)
            
            db.commit()
            flash('Ганпак успешно обновлен!', 'success')
            return redirect(url_for('gunpacks'))
        
        all_channels = db.query(Channel).all()
        # ✅ Получаем каналы из ORM вместо JSON
        gunpack_channels = [c.name for c in gunpack.channels]
        return render_template('gunpack_form_dark.html', gunpack=gunpack, all_channels=all_channels, gunpack_channels=gunpack_channels)
# --- 6. Управление Каналами ---
@app.route('/channels', methods=['GET', 'POST'])
@login_required
@admin_required
@requires_auth
def channels():
    with get_db() as db:
        if request.method == 'POST':
            name, title = request.form.get('name', '').strip(), request.form.get('title', '').strip()
            if name and title:
                if not name.startswith('@') and not name.startswith('-100'):
                    name = '@' + name
                db.add(Channel(name=name, title=title, is_active=True))
                db.commit()
                flash('Канал добавлен', 'success')
            return redirect(url_for('channels'))
        
        channels_list = db.query(Channel).all()
        return render_template('channels_dark.html', channels=channels_list)

@app.route('/channels/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
@requires_auth
def delete_channel(id):
    with get_db() as db:
        ch = db.query(Channel).get(id)
        if ch:
            db.delete(ch)
            db.commit()
            flash('Канал удален', 'success')
        return redirect(url_for('channels'))
@app.route('/channels/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
@requires_auth
def edit_channel(id):
    with get_db() as db:
        channel = db.query(Channel).get(id)
        if not channel:
            flash('Канал не найден', 'error')
            return redirect(url_for('channels'))
        
        if request.method == 'POST':
            channel.name = request.form.get('name', '').strip()
            channel.title = request.form.get('title', '').strip()
            
            # Если название не начинается с @ или -100, добавляем @
            if channel.name and not channel.name.startswith('@') and not channel.name.startswith('-100'):
                channel.name = '@' + channel.name
                
            db.commit()
            flash('Канал успешно обновлен', 'success')
            return redirect(url_for('channels'))
            
        return render_template('channel_form_dark.html', channel=channel)
# --- 7. Управление Пользователями ---
@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
@requires_auth
def edit_user(id):
    with get_db() as db:
        user = db.query(User).get(id)
        if not user: return redirect(url_for('users'))
        if request.method == 'POST':
            if int(user.telegram_id) == ADMIN_ID:
                flash('Роль главного администратора нельзя изменить.', 'error')
            else:
                user.role = request.form.get('role', 'user')
                db.commit()
                flash('Данные пользователя обновлены', 'success')
            return redirect(url_for('users'))
        return render_template('user_form_dark.html', user=user)

@app.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
@requires_auth
def delete_user(id):
    with get_db() as db:
        user = db.query(User).get(id)
        if user and int(user.telegram_id) != ADMIN_ID:
            db.delete(user)
            db.commit()
            flash('Пользователь удален', 'success')
        return redirect(url_for('users'))

# --- 8. Функции экспорта и очистки (Заглушки от BuildError) ---
# --- 8. Функции экспорта и очистки (Исправлено для шаблона) ---

@app.route('/admin/export/xml')
@login_required
@admin_required
@requires_auth
def export_users_xml():
    flash('Экспорт XML временно недоступен', 'info')
    return redirect(url_for('dashboard'))

@app.route('/admin/export/csv')
@login_required
@admin_required
@requires_auth
def export_users_csv():
    flash('Экспорт CSV временно недоступен', 'info')
    return redirect(url_for('dashboard'))

@app.route('/admin/cleanup-database')
@login_required
@admin_required
@requires_auth
def cleanup_database():
    flash('Очистка базы данных запрещена в целях безопасности', 'error')
    return redirect(url_for('dashboard'))

# Если вдруг в шаблоне есть ссылка на экспорт JSON
@app.route('/admin/export/json')
@login_required
@admin_required
@requires_auth
def export_users_json():
    with get_db() as db:
        users_list = db.query(User).all()
        data = [{"id": u.id, "tg_id": u.telegram_id, "username": u.username} for u in users_list]
        return jsonify(data)

# --- 9. Рассылка ---
@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
@admin_required
@requires_auth
def broadcast():
    with get_db() as db:
        if request.method == 'POST':
            gunpack_id = request.form.get('gunpack_id')
            message_text = request.form.get('message_text')
            selected_channels = request.form.getlist('channels')

            from broadcast_handler import broadcast_queue
            broadcast_queue.append({
                'gunpack_id': int(gunpack_id),
                'message_text': message_text,
                'selected_channels': selected_channels,
                'media_type': request.form.get('media_type', ''),
                'media_url': request.form.get('media_url', ''),
            })
            flash(f'Рассылка поставлена в очередь ({len(broadcast_queue)} задач)!', 'success')
            return redirect(url_for('dashboard'))

        gunpacks_list = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        channels_list = db.query(Channel).filter(Channel.is_active == True).all()
        return render_template('broadcast_dark.html', gunpacks=gunpacks_list, channels=channels_list)

# --- 10. API проверки подписки (вызывается JS на странице юзера) ---
@app.route('/api/check-subscription/<int:gunpack_id>', methods=['POST'])
@login_required
def api_check_subscription(gunpack_id):
    """
    Сайт спрашивает бота: подписан ли текущий юзер на каналы этого ганпака?
    Бот проверяет через Telegram API и возвращает результат.
    После подтверждения подписки — записываем скачивание в БД.
    """
    import requests as http_requests

    # У юзера должен быть telegram_id (он залогинен через Telegram)
    if not current_user.telegram_id:
        return jsonify({
            "error": "no_telegram",
            "message": "Войдите через Telegram чтобы проверить подписку"
        }), 400

    # Запрос к внутреннему API бота
    bot_api_url = f"http://127.0.0.1:{config.BOT_API_PORT}/internal/check-subscription"
    try:
        resp = http_requests.post(bot_api_url, json={
            "secret": config.BOT_API_SECRET,
            "telegram_id": int(current_user.telegram_id),
            "gunpack_id": gunpack_id,
        }, timeout=12)
        result = resp.json()
    except http_requests.exceptions.ConnectionError:
        return jsonify({
            "error": "bot_unavailable",
            "message": "Бот недоступен. Попробуйте через Telegram-бота."
        }), 503
    except Exception as e:
        return jsonify({"error": "internal", "message": str(e)}), 500

    if resp.status_code != 200:
        return jsonify(result), resp.status_code

    # Если подписан — записываем скачивание
    if result.get("subscribed"):
        with get_db() as db:
            user = db.query(User).filter(User.id == current_user.id).first()
            gunpack = db.query(Gunpack).filter(Gunpack.id == gunpack_id).first()
            if user and gunpack:
                already = db.query(Download).filter(
                    Download.user_id == user.id,
                    Download.gunpack_id == gunpack.id,
                ).first()
                if not already:
                    db.add(Download(user_id=user.id, gunpack_id=gunpack.id))
                    db.commit()

    return jsonify(result)

@app.route('/demo_user')
def demo_user():
    """Демо-страница — показывает как выглядит панель для обычного юзера."""
    with get_db() as db:
        gunpacks_count = db.query(Gunpack).filter(Gunpack.is_active == True).count()
        total_downloads = db.query(Download).count()
        gunpacks_list = db.query(Gunpack).filter(Gunpack.is_active == True).all()
    return render_template('demo_user_view.html',
                           gunpacks_count=gunpacks_count,
                           total_downloads=total_downloads,
                           gunpacks=gunpacks_list)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
