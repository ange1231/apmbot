from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import json
from datetime import datetime
import config
from database import get_db, User, Gunpack, Download, Channel, GunpackChannel, init_default_channels
import os

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['DEBUG'] = True

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Инициализация каналов при первом запуске
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
def users():
    db = get_db()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        return render_template('users_dark.html', users=users)
    finally:
        db.close()

@app.route('/gunpacks')
def gunpacks():
    db = get_db()
    try:
        gunpacks = db.query(Gunpack).order_by(Gunpack.created_at.desc()).all()
        return render_template('gunpacks_dark_fixed.html', gunpacks=gunpacks)
    finally:
        db.close()

@app.route('/gunpacks/new', methods=['GET', 'POST'])
def new_gunpack():
    if request.method == 'POST':
        db = get_db()
        try:
            # Получаем выбранные каналы из чекбоксов
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
    
    # Получаем список каналов для формы
    db = get_db()
    try:
        all_channels = db.query(Channel).all()
        return render_template('gunpack_form_dark.html', gunpack=None, all_channels=all_channels, gunpack_channels=[])
    finally:
        db.close()

@app.route('/gunpacks/<int:id>/edit', methods=['GET', 'POST'])
def edit_gunpack(id):
    print(f"Редактирование ганпака с ID: {id}")
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if not gunpack:
            print(f"Ганпак с ID {id} не найден")
            flash('Ганпак не найден!', 'error')
            return redirect(url_for('gunpacks'))
        
        print(f"Найден ганпак: {gunpack.name}")
        
        if request.method == 'POST':
            print("Обработка POST запроса")
            gunpack.name = request.form['name']
            gunpack.description = request.form['description']
            gunpack.image_url = request.form['image_url']
            gunpack.download_link = request.form['download_link']
            
            # Получаем выбранные каналы из чекбоксов
            selected_channels = request.form.getlist('channels')
            gunpack.channels_required = json.dumps(selected_channels)
            
            gunpack.is_active = 'is_active' in request.form
            gunpack.updated_at = datetime.utcnow()
            db.commit()
            flash('Ганпак успешно обновлен!', 'success')
            return redirect(url_for('gunpacks'))
        
        # Получаем список каналов для формы
        all_channels = db.query(Channel).all()
        try:
            gunpack_channels = json.loads(gunpack.channels_required) if gunpack.channels_required else []
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON каналов: {e}, данные: {gunpack.channels_required}")
            gunpack_channels = []
        
        print(f"Рендеринг шаблона с ганпаком: {gunpack.name}")
        return render_template('gunpack_form_dark.html', gunpack=gunpack, all_channels=all_channels, gunpack_channels=gunpack_channels)
    except Exception as e:
        print(f"Ошибка в edit_gunpack: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Ошибка: {str(e)}', 'error')
        return redirect(url_for('gunpacks'))
    finally:
        db.close()

@app.route('/gunpacks/<int:id>/toggle', methods=['POST'])
def toggle_gunpack(id):
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if gunpack:
            gunpack.is_active = not gunpack.is_active
            db.commit()
            flash(f'Ганпак {"активирован" if gunpack.is_active else "деактивирован"}!', 'success')
        return redirect(url_for('gunpacks'))
    finally:
        db.close()

@app.route('/gunpacks/<int:id>/delete', methods=['POST'])
def delete_gunpack(id):
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if gunpack:
            # Удаляем все связанные скачивания
            downloads = db.query(Download).filter(Download.gunpack_id == id).all()
            for download in downloads:
                db.delete(download)
            
            # Удаляем сам ганпак
            db.delete(gunpack)
            db.commit()
            
            downloads_count = len(downloads)
            if downloads_count > 0:
                flash(f'Ганпак успешно удален! Также удалено {downloads_count} записей о скачиваниях.', 'success')
            else:
                flash('Ганпак успешно удален!', 'success')
        else:
            flash('Ганпак не найден!', 'error')
        return redirect(url_for('gunpacks'))
    except Exception as e:
        db.rollback()
        flash(f'Ошибка при удалении ганпака: {str(e)}', 'error')
        return redirect(url_for('gunpacks'))
    finally:
        db.close()

@app.route('/admin/cleanup')
def cleanup_database():
    """Очистка базы данных от осиротевших записей"""
    db = get_db()
    try:
        # Находим скачивания без связанных ганпаков
        orphan_downloads = db.query(Download).outerjoin(Gunpack).filter(Gunpack.id.is_(None)).all()
        
        # Удаляем осиротевшие скачивания
        deleted_count = 0
        for download in orphan_downloads:
            db.delete(download)
            deleted_count += 1
        
        db.commit()
        
        if deleted_count > 0:
            flash(f'Очистка завершена! Удалено {deleted_count} осиротевших записей о скачиваниях.', 'success')
        else:
            flash('Очистка завершена! Осиротевших записей не найдено.', 'success')
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        db.rollback()
        flash(f'Ошибка при очистке базы данных: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.close()

@app.route('/broadcast', methods=['GET', 'POST'])
def broadcast():
    """Страница рассылки в Telegram каналы"""
    db = get_db()
    try:
        if request.method == 'POST':
            # Получаем данные формы
            gunpack_id = request.form['gunpack_id']
            message_text = request.form['message_text']
            selected_channels = request.form.getlist('channels')
            media_type = request.form.get('media_type', '')
            media_url = request.form.get('media_url', '')
            
            if not gunpack_id or not message_text or not selected_channels:
                flash('Заполните все поля и выберите хотя бы один канал!', 'error')
                return redirect(url_for('broadcast'))
            
            # Проверяем валидность медиа если указано
            if media_type and not media_url:
                flash('Укажите URL медиа!', 'error')
                return redirect(url_for('broadcast'))
            
            # Добавляем рассылку в очередь для бота
            try:
                from broadcast_handler import add_broadcast_to_queue
                import asyncio
                
                # Запускаем асинхронную функцию
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(add_broadcast_to_queue(
                    int(gunpack_id), 
                    message_text, 
                    selected_channels,
                    media_type,
                    media_url
                ))
                loop.close()
                
                flash('Рассылка добавлена в очередь! Бот отправит сообщения в ближайшее время.', 'success')
            except Exception as e:
                flash(f'Ошибка при добавлении рассылки: {str(e)}', 'error')
            
            return redirect(url_for('dashboard'))
        
        # Получаем активные ганпаки для выбора
        gunpacks = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        
        # Получаем активные каналы
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        
        return render_template('broadcast_dark.html', gunpacks=gunpacks, channels=channels)
    finally:
        db.close()

@app.route('/channels')
def channels():
    db = get_db()
    try:
        channels = db.query(Channel).order_by(Channel.created_at.desc()).all()
        return render_template('channels_dark.html', channels=channels)
    finally:
        db.close()

@app.route('/channels/new', methods=['GET', 'POST'])
def new_channel():
    if request.method == 'POST':
        db = get_db()
        try:
            channel = Channel(
                name=request.form['name'],
                title=request.form['title'],
                description=request.form.get('description', ''),
                is_active='is_active' in request.form
            )
            db.add(channel)
            db.commit()
            flash('Канал успешно создан!', 'success')
            return redirect(url_for('channels'))
        finally:
            db.close()
    
    return render_template('channel_form_dark.html', channel=None)

@app.route('/channels/<int:id>/edit', methods=['GET', 'POST'])
def edit_channel(id):
    db = get_db()
    try:
        channel = db.query(Channel).filter(Channel.id == id).first()
        if not channel:
            flash('Канал не найден!', 'error')
            return redirect(url_for('channels'))
        
        if request.method == 'POST':
            channel.name = request.form['name']
            channel.title = request.form['title']
            channel.description = request.form.get('description', '')
            channel.is_active = 'is_active' in request.form
            db.commit()
            flash('Канал успешно обновлен!', 'success')
            return redirect(url_for('channels'))
        
        return render_template('channel_form_dark.html', channel=channel)
    finally:
        db.close()

@app.route('/channels/<int:id>/toggle', methods=['POST'])
def toggle_channel(id):
    db = get_db()
    try:
        channel = db.query(Channel).filter(Channel.id == id).first()
        if channel:
            channel.is_active = not channel.is_active
            db.commit()
            flash(f'Канал {"активирован" if channel.is_active else "деактивирован"}!', 'success')
        return redirect(url_for('channels'))
    finally:
        db.close()

@app.route('/channels/<int:id>/delete', methods=['POST'])
def delete_channel(id):
    db = get_db()
    try:
        channel = db.query(Channel).filter(Channel.id == id).first()
        if channel:
            # Проверяем, используется ли канал в ганпаках
            gunpacks_using_channel = []
            gunpacks = db.query(Gunpack).all()
            
            for gunpack in gunpacks:
                if gunpack.channels_required:
                    try:
                        channels = json.loads(gunpack.channels_required)
                        if channel.name in channels:
                            gunpacks_using_channel.append(gunpack.name)
                    except json.JSONDecodeError:
                        pass
            
            if gunpacks_using_channel:
                # Если канал используется, не удаляем его, а предлагаем деактивировать
                flash(f'Канал используется в ганпаках: {", ".join(gunpacks_using_channel)}. Деактивируйте его вместо удаления.', 'warning')
                channel.is_active = False
                db.commit()
            else:
                # Если канал не используется, удаляем его
                db.delete(channel)
                db.commit()
                flash('Канал успешно удален!', 'success')
        else:
            flash('Канал не найден!', 'error')
        return redirect(url_for('channels'))
    except Exception as e:
        db.rollback()
        flash(f'Ошибка при удалении канала: {str(e)}', 'error')
        return redirect(url_for('channels'))
    finally:
        db.close()

@app.route('/gunpacks/<int:id>/select_channels', methods=['GET'])
def select_channels_for_post(id):
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if not gunpack:
            flash('Ганпак не найден!', 'error')
            return redirect(url_for('gunpacks'))
        
        channels = db.query(Channel).all()
        
        return render_template('channel_select.html', gunpack=gunpack, channels=channels)
    finally:
        db.close()

@app.route('/gunpacks/<int:id>/create_post', methods=['POST'])
def create_gunpack_post(id):
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if not gunpack:
            flash('Ганпак не найден!', 'error')
            return redirect(url_for('gunpacks'))
        
        # Получаем выбранные каналы из формы
        selected_channels = request.form.getlist('channels')
        post_text = request.form.get('post_text', '').strip()
        
        if not selected_channels:
            flash('Выберите хотя бы один канал!', 'error')
            return redirect(url_for('select_channels_for_post', id=id))
        
        # Создаем посты в выбранных каналах
        from channel_poster import ChannelPoster
        import asyncio
        
        async def create_posts():
            poster = ChannelPoster(config.BOT_TOKEN)
            results = []
            
            for channel in selected_channels:
                result = await poster.create_post_with_button(channel, id, post_text if post_text else None)
                results.append({"channel": channel, "success": result is not None})
            
            return results
        
        # Запускаем асинхронную задачу
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(create_posts())
        loop.close()
        
        # Анализируем результаты
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        if success_count == total_count:
            flash(f'✅ Посты успешно созданы в {success_count} каналах!', 'success')
        elif success_count > 0:
            flash(f'⚠️ Посты созданы в {success_count} из {total_count} каналов', 'warning')
        else:
            flash('❌ Не удалось создать посты ни в одном канале', 'error')
        
        return redirect(url_for('gunpacks'))
    finally:
        db.close()

@app.route('/statistics')
def statistics():
    db = get_db()
    try:
        # Общее количество пользователей (как на главной)
        total_users = db.query(User).count()
        
        gunpacks = db.query(Gunpack).filter(Gunpack.is_active == True).all()
        stats = []
        
        for gunpack in gunpacks:
            # Количество скачиваний
            downloads_count = db.query(Download).filter(Download.gunpack_id == gunpack.id).count()
            
            # Количество уникальных пользователей
            unique_users_count = db.query(Download).filter(Download.gunpack_id == gunpack.id).distinct(Download.user_id).count()
            
            stats.append({
                'gunpack': gunpack,
                'downloads_count': downloads_count,
                'unique_users_count': unique_users_count
            })
        
        return render_template('statistics_dark.html', stats=stats, total_users=total_users)
    finally:
        db.close()

@app.route('/export/users/xml')
def export_users_xml():
    db = get_db()
    try:
        users = db.query(User).all()
        
        root = ET.Element('users')
        for user in users:
            user_elem = ET.SubElement(root, 'user')
            ET.SubElement(user_elem, 'id').text = str(user.id)
            ET.SubElement(user_elem, 'telegram_id').text = str(user.telegram_id)
            ET.SubElement(user_elem, 'username').text = user.username or ''
            ET.SubElement(user_elem, 'first_name').text = user.first_name or ''
            ET.SubElement(user_elem, 'last_name').text = user.last_name or ''
            ET.SubElement(user_elem, 'created_at').text = user.created_at.isoformat()
        
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        
        output = io.BytesIO()
        output.write(xml_str.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'users_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml',
            mimetype='text/xml'
        )
    finally:
        db.close()

@app.route('/api/gunpacks/<int:id>/stats')
def api_gunpack_stats(id):
    db = get_db()
    try:
        gunpack = db.query(Gunpack).filter(Gunpack.id == id).first()
        if not gunpack:
            return jsonify({'error': 'Gunpack not found'}), 404
        
        downloads = db.query(Download).filter(Download.gunpack_id == id).count()
        recent_downloads = db.query(Download).filter(Download.gunpack_id == id).order_by(Download.downloaded_at.desc()).limit(10).all()
        
        return jsonify({
            'gunpack': {
                'id': gunpack.id,
                'name': gunpack.name,
                'downloads': downloads
            },
            'recent_downloads': [
                {
                    'user': download.user.first_name,
                    'downloaded_at': download.downloaded_at.isoformat()
                }
                for download in recent_downloads
            ]
        })
    finally:
        db.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
