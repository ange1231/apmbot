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
import asyncio
from functools import wraps
from urllib.parse import parse_qsl

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('У вас нет прав для доступа к этой странице.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Вспомогательная функция для Telegram Auth ---
def verify_telegram_data(init_data):
    try:
        # Разбираем строку параметров от Telegram
        vals = dict(parse_qsl(init_data))
        if 'hash' not in vals:
            return None
        
        hash_str = vals.pop('hash')
        # Собираем строку для проверки (ключи должны быть отсортированы)
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(vals.items())])
        
        # Вычисляем секретный ключ на основе токена бота
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        # Считаем HMAC и сравниваем с полученным хешем
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
        db = get_db()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user and user.password_hash and bcrypt.check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Неверный логин или пароль', 'error')
        finally:
            db.close()
    return render_template('login_dark.html')

@app.route('/auth-tg', methods=['POST'])
def auth_tg():
    data = request.json
    init_data = data.get('initData')
    user_info = verify_telegram_data(init_data)
    
    if user_info:
        tg_id = str(user_info.get('id'))
        db = get_db()
        try:
            # 1. Ищем пользователя
            user = db.query(User).filter(User.telegram_id == tg_id).first()
            
            # 2. Если пользователя нет или он не админ — ПРИНУДИТЕЛЬНО исправляем это
            if not user:
                # Если тебя нет в базе, создаем
                user = User(
                    telegram_id=tg_id, 
                    username=user_info.get('username', 'Admin'), 
                    role='admin'
                )
                db.add(user)
                db.commit()
           # elif user.role != 'admin':
                # Если ты есть, но не админ — даем права
              #  user.role = 'admin'
              #  db.commit()

            # 3. Теперь логиним
            login_user(user)
            return jsonify({"success": True})
        except Exception as e:
            print(f"Database error: {e}")
            return jsonify({"success": False}), 500
        finally:
            db.close()
    
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
@admin_required
def dashboard():
    init_default_channels()
    db = get_db()
    try:
        users_count = db.query(User).count()
        gunpacks_count = db.query(Gunpack).count()
        channels_count = db.query(Channel).count()
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
        users_list = db.query(User).order_by(User.created_at.desc()).all()
        return render_template('users_dark.html', users=users_list)
    finally:
        db.close()

@app.route('/statistics')
@login_required
@admin_required
def statistics():
    db = get_db()
    try:
        total_users = db.query(User).count()
        gunpacks = db.query(Gunpack).all()
        stats = []
        for gp in gunpacks:
            downloads = db.query(Download).filter(Download.gunpack_id == gp.id).count()
            stats.append({'gunpack': gp, 'downloads_count': downloads})
        return render_template('statistics_dark.html', stats=stats, total_users=total_users)
    finally:
        db.close()

# --- 5. Управление Ганпаками ---
@app.route('/gunpacks')
@login_required
@admin_required
def gunpacks():
    db = get_db()
    try:
        gunpacks_list = db.query(Gunpack).order_by(Gunpack.created_at.desc()).all()
        return render_template('gunpacks_dark_fixed.html', gunpacks=gunpacks_list)
    finally:
        db.close()

@app.route('/gunpacks/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_gunpack(id):
    db = get_db()
    try:
        gp = db.query(Gunpack).get(id)
        if gp:
            db.delete(gp)
            db.commit()
            flash('Ганпак удален', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Ошибка: {e}', 'error')
    finally:
        db.close()
    return redirect(url_for('gunpacks'))

@app.route('/gunpacks/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_gunpack():
    db = get_db()
    try:
        if request.method == 'POST':
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

# --- 6. Управление Каналами ---
@app.route('/channels', methods=['GET', 'POST'])
@login_required
@admin_required
def channels():
    db = get_db()
    try:
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            title = request.form.get('title', '').strip()
            if name and title:
                if not name.startswith('@') and not name.startswith('-100'):
                    name = '@' + name
                new_ch = Channel(name=name, title=title, is_active=True)
                db.add(new_ch)
                db.commit()
                flash('Канал добавлен', 'success')
            return redirect(url_for('channels'))
        
        channels_list = db.query(Channel).all()
        return render_template('channels_dark.html', channels=channels_list)
    finally:
        db.close()

@app.route('/channels/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_channel(id):
    db = get_db()
    try:
        ch = db.query(Channel).get(id)
        if ch:
            db.delete(ch)
            db.commit()
            flash('Канал удален', 'success')
    except Exception as e:
        db.rollback()
    finally:
        db.close()
    return redirect(url_for('channels'))

@app.route('/channels/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_channel(id):
    db = get_db()
    try:
        channel = db.query(Channel).get(id)
        if not channel:
            flash('Канал не найден!', 'error')
            return redirect(url_for('channels'))
        
        if request.method == 'POST':
            channel.name = request.form.get('name', '').strip()
            channel.title = request.form.get('title', '').strip()
            channel.description = request.form.get('description', '')
            if channel.name and not channel.name.startswith('@') and not channel.name.startswith('-100'):
                channel.name = '@' + channel.name
            db.commit()
            flash('Канал успешно обновлен!', 'success')
            return redirect(url_for('channels'))
        
        return render_template('channel_form_dark.html', channel=channel)
    except Exception as e:
        db.rollback()
        flash(f'Ошибка: {e}', 'error')
        return redirect(url_for('channels'))
    finally:
        db.close()

@app.route('/channels/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_channel():
    if request.method == 'POST':
        db = get_db()
        try:
            name = request.form.get('name', '').strip()
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '')
            is_active = 'is_active' in request.form
            
            if name and title:
                if not name.startswith('@') and not name.startswith('-100'):
                    name = '@' + name
                
                new_ch = Channel(
                    name=name, 
                    title=title, 
                    description=description, 
                    is_active=is_active
                )
                db.add(new_ch)
                db.commit()
                flash('Канал успешно создан!', 'success')
                return redirect(url_for('channels'))
            else:
                flash('Заполните обязательные поля!', 'error')
        except Exception as e:
            db.rollback()
            flash(f'Ошибка: {e}', 'error')
        finally:
            db.close()
            
    return render_template('channel_form_dark.html', channel=None)

@app.route('/channels/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_channel(id):
    db = get_db()
    try:
        ch = db.query(Channel).get(id)
        if ch:
            ch.is_active = not ch.is_active
            db.commit()
    finally:
        db.close()
    return redirect(url_for('channels'))

# --- 7. Управление Пользователями ---
@app.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    db = get_db()
    try:
        user = db.query(User).get(id)
        if user:
            db.delete(user)
            db.commit()
            flash('Пользователь удален', 'success')
    finally:
        db.close()
    return redirect(url_for('users'))

@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    db = get_db()
    try:
        user = db.query(User).get(id)
        if not user:
            return redirect(url_for('users'))
        if request.method == 'POST':
            user.role = request.form.get('role', 'user')
            db.commit()
            flash('Данные пользователя обновлены', 'success')
            return redirect(url_for('users'))
        return render_template('user_form_dark.html', user=user)
    finally:
        db.close()

# --- 8. Сервисные функции ---
@app.route('/admin/cleanup', methods=['GET', 'POST'])
@login_required
@admin_required
def cleanup_database():
    db = get_db()
    try:
        db.query(User).filter(User.username == None).delete()
        db.commit()
        flash('База данных оптимизирована', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Ошибка очистки: {e}', 'error')
    finally:
        db.close()
    return redirect(url_for('dashboard'))

@app.route('/export/xml')
@login_required
@admin_required
def export_users_xml():
    db = get_db()
    try:
        users_list = db.query(User).all()
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<users>\n'
        for index, u in enumerate(users_list, start=1):
            xml += f'  <user number="{index}">\n'
            xml += f'    <id>{u.id}</id>\n'
            xml += f'    <username>{u.username or "N/A"}</username>\n'
            xml += f'    <telegram_id>{u.telegram_id or "N/A"}</telegram_id>\n'
            xml += f'    <role>{u.role}</role>\n'
            xml += f'  </user>\n'
        xml += '</users>'
        return Response(xml, mimetype='application/xml', 
                        headers={'Content-Disposition': 'attachment;filename=users_list.xml'})
    finally:
        db.close()

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

        gunpacks_list = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        channels_list = db.query(Channel).filter(Channel.is_active == True).all()
        return render_template('broadcast_dark.html', gunpacks=gunpacks_list, channels=channels_list)
    finally:
        db.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
