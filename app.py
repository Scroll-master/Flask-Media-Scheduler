from flask import Flask, render_template, redirect, url_for, flash ,request, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from moviepy.editor import VideoFileClip
import pymysql
import secrets, json, os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  # Добавлен для безопасной загрузки файлов
import threading


app = Flask(__name__)

app.secret_key = secrets.token_hex(16)

# Создайте объект UploadSet для медиафайлов


app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:20120512LiBuN@localhost/Users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'C:/Users/PC/Desktop/Python_Hope/static/videos'


db = SQLAlchemy(app)



login_manager = LoginManager()
login_manager.init_app(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.id


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.String(8))  # Длительность в формате ЧЧ:ММ:СС
    tags = db.Column(db.String(255), nullable=True)  # Теги, которые могут изначально отсутствовать
    status = db.Column(db.String(50), default='Активен')  # Добавленное поле статуса
    

def add_media_from_folder(folder_path):
    existing_media = {media.filename: media for media in Media.query.all()}
    actual_filenames = set(os.listdir(folder_path))

    # Обновление статуса для отсутствующих файлов
    for filename, media in existing_media.items():
        if filename not in actual_filenames:
            media.status = 'Отсутствует'
            db.session.add(media)

    # Добавление новых медиафайлов в БД
    for filename in actual_filenames:
        if filename.endswith((".mp4", ".avi")) and filename not in existing_media:
            filepath = os.path.join(folder_path, filename)
            clip = VideoFileClip(filepath)
            duration_seconds = int(clip.duration)
            duration_formatted = f"{duration_seconds // 3600:02d}:{(duration_seconds % 3600 // 60):02d}:{duration_seconds % 60:02d}"

            new_media = Media(
                title=filename,  # Используйте filename в качестве title
                filename=filename,
                filepath=filepath,
                created_at=datetime.now(),
                duration=duration_formatted,
                tags=None,  # Изначально теги отсутствуют
                status='Активен'  # Помечаем новый файл как активный
            )
            db.session.add(new_media)

    db.session.commit()




@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(255))
    type = db.Column(db.String(50))  # Например, 'периодическое', 'исключение', 'специальная дата'
    datetime = db.Column(db.DateTime, nullable=True)  # Обновлено для хранения даты и времени специального расписания
    events = db.relationship('Event', backref='schedule', lazy=True)



class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)  # Связь с медиафайлом
    start_time = db.Column(db.DateTime, nullable=False)  # Время начала события
    end_time = db.Column(db.DateTime, nullable=False)  # Время окончания события
    media = db.relationship('Media', backref='events')

@app.route('/')
def hello_world():
    return render_template('index.html')
        
        
#@app.route('/password')
#def passwordgem():
#        return password_hash
        
@app.route('/private', methods=['GET', 'POST'])
@login_required  # Требование аутентификации
def private():
    
    
    # Если метод запроса - POST, значит, данные были отправлены из формы
    if request.method == 'POST':
        # Получаем данные из формы (здесь предполагается наличие поля 'text')
        user_text = request.form.get('text')
        
        # Проверяем, что поле 'text' не пустое
        if user_text:
            # Создаем путь к файлу JSON на рабочем столе
            desktop_path = os.path.expanduser("~/Desktop")
            json_file_path = os.path.join(desktop_path, 'user_data.json')
            
            # Создаем или обновляем JSON файл с текстом пользователя
            user_data = {'username': current_user.username, 'text': user_text}
            with open(json_file_path, 'w') as json_file:
                json.dump(user_data, json_file)
            
            # Возвращаем сообщение об успешном сохранении
            flash('Ваш текст успешно сохранен в JSON файле на рабочем столе.')
            return redirect(url_for('private'))
    
    response = make_response(render_template('private.html', username=current_user.username))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('You have been logged in!', 'success')
            
            # Проверка роли пользователя и перенаправление на соответствующую страницу
            if user.role == 'master':
                return redirect(url_for('super_admin_page'))
            elif user.role == 'admin':
                return redirect(url_for('admin_page'))
            else:
                return redirect(url_for('index'))  # Или другая страница по умолчанию
            
        else:
            flash('Неправильное имя пользователя или пароль', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')




@app.route('/logout')
def logout():
    logout_user()
    response = redirect(url_for('hello_world'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
    
@app.route('/admin')
@login_required
def admin_page():
    if current_user.role not in ['admin', 'master']:
        return "Доступ запрещен", 403  # Или перенаправление на другую страницу
    # Логика страницы Admin
    return render_template('admin.html')

@app.route('/superadmin')
@login_required
def super_admin_page():
    if current_user.role != 'master':
        return "Доступ запрещен", 403  # Или перенаправление на другую страницу
    schedules = Schedule.query.all()  # Загружаем все расписания из базы данных
    events = Event.query.all()  # Загружаем все события из базы данных
    media_files = Media.query.all()  # Добавьте эту строку для получения медиафайлов
    # Логика страницы Super_Admin
    return render_template('super_admin.html', schedules=schedules, events=events, media_files=media_files)


#Маршрут для создания нового расписания:
@app.route('/schedule/new', methods=['GET', 'POST'])
@login_required
def new_schedule():
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    schedule = None  # Нет расписания при создании нового
    if request.method == 'POST':
        name = request.form.get('name')
        
        
        existing_schedule = Schedule.query.filter_by(name=name).first()
        if existing_schedule:
            flash('Расписание с таким названием уже существует.')
            return render_template('edit_schedule.html', schedule=None)
        
        description = request.form.get('description')
        schedule_type = request.form.get('type')
        datetime_str = request.form.get('datetime') if schedule_type == 'специальная дата' else None
        
        # Создание нового объекта Schedule
        new_schedule = Schedule(name=name, description=description, type=schedule_type)
        
        if schedule_type == 'специальная дата':
            datetime_str = request.form.get('datetime')
            if not datetime_str:
                flash('Укажите дату и время для специальной даты.')
                return render_template('edit_schedule.html', schedule=None)
            try:
                new_schedule.datetime = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Неверный формат даты и времени. Используйте формат ГГГГ-ММ-ДД ЧЧ:ММ.')
                return render_template('edit_schedule.html', schedule=None)
            
        else:
            new_schedule.datetime = None  # Обнуляем дату и время для не-специальных дат    
            
        db.session.add(new_schedule)
        db.session.commit()
        flash('Новое расписание создано.')
        return redirect(url_for('super_admin_page'))
    # Передаем None для schedule, чтобы шаблон знал, что это создание, а не редактирование
    return render_template('edit_schedule.html', schedule=None)

#Маршрут для редактирования существующего расписания:
@app.route('/schedule/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(schedule_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.events:  # Проверяем, связано ли расписание с какими-либо событиями
        flash('Расписание уже используется в событиях и не может быть отредактировано.', 'error')
        return redirect(url_for('super_admin_page'))
    # Логика редактирования расписания
    if request.method == 'POST':
        name = request.form.get('name')  # Извлекаем имя из формы
        
        # Проверяем, существует ли другое расписание с таким же именем
        existing_schedule = Schedule.query.filter(Schedule.id != schedule_id, Schedule.name == name).first()
        if existing_schedule:
            flash('Расписание с таким названием уже существует.')
            return render_template('edit_schedule.html', schedule=schedule)
        
        schedule.description = request.form.get('description')
        schedule.type = request.form.get('type')
        
        if schedule.type == 'специальная дата':
            datetime_str = request.form.get('datetime')
            schedule.datetime = datetime.strptime(request.form.get('datetime'), '%Y-%m-%dT%H:%M')
        else:
            schedule.datetime = None  # Обнуляем дату и время для не-специальных дат
        
        db.session.commit()
        flash('Расписание успешно обновлено.')
        return redirect(url_for('super_admin_page'))
    
    return render_template('edit_schedule.html', schedule=schedule)

#Маршрут для удаления расписания:
@app.route('/schedule/delete/<int:schedule_id>', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.events:  # Проверка на наличие связанных событий
        flash('Расписание используется в одном или нескольких событиях и не может быть удалено. Пожалуйста, удалите связанные события перед удалением расписания.', 'error')
        return redirect(url_for('super_admin_page'))
    db.session.delete(schedule)
    db.session.commit()
    return redirect(url_for('super_admin_page'))


@app.route('/event/new', methods=['GET', 'POST'])
@login_required
def new_event():
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    event = None
    if request.method == 'POST':
        # Здесь будет логика обработки данных формы для создания нового события
        schedule_id = request.form.get('schedule_id')
        media_id = request.form.get('media_id')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        
        # Получаем информацию о расписании
        schedule = Schedule.query.get(schedule_id)
        
        # Проверка на перекрытие времени с другими событиями
        overlapping_events = Event.query.filter(
            db.and_(
                Event.end_time > start_datetime,
                Event.start_time < end_datetime
            )
        ).all()
        
        if overlapping_events:
            flash('Выбранное время перекрывается с другими событиями. Пожалуйста, выберите другое время.')
            return redirect(url_for('new_event'))
        # Если нет перекрытия, создаем новое событие
        
        # Проверка соответствия события выбранному расписанию
        if schedule.type == 'специальная дата' and (schedule.datetime and (start_datetime < schedule.datetime or end_datetime > schedule.datetime)):
            flash('Даты события выходят за рамки даты специального расписания.')
            return redirect(url_for('new_event'))
        # Проверка на корректность введенных данных, создание и сохранение нового события
        # Пример:
        new_event = Event(schedule_id=schedule_id, media_id=media_id, 
                          start_time=datetime.strptime(start_time, '%Y-%m-%dT%H:%M'),
                          end_time=datetime.strptime(end_time, '%Y-%m-%dT%H:%M'))
        
        db.session.add(new_event)
        db.session.commit()
        flash('Новое событие успешно создано.')
        return redirect(url_for('super_admin_page'))
    else:
        schedules = Schedule.query.all()
        media_files = Media.query.all()
        return render_template('edit_event.html', event=None, schedules=schedules, media_files=media_files)


@app.route('/event/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        event.schedule_id = request.form.get('schedule_id')
        event.media_id = request.form.get('media_id')
        event.start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        event.end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        
        schedule = Schedule.query.get(event.schedule_id)
        
        # Проверка соответствия даты и времени события расписанию
        if schedule.type == 'специальная дата' and (schedule.datetime and (start_datetime < schedule.datetime or end_datetime > schedule.datetime)):
            flash('Даты события выходят за рамки даты специального расписания.')
            return redirect(url_for('edit_event', event_id=event_id))
         # Преобразование строк в объекты datetime
        start_datetime = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        
         # Проверка на перекрытие времени с другими событиями
        overlapping_events = Event.query.filter(
            Event.id != event_id,
            Event.schedule_id == event.schedule_id,
            db.or_(
                db.and_(Event.start_time <= start_datetime, Event.end_time > start_datetime),
                db.and_(Event.start_time < end_datetime, Event.end_time >= end_datetime),
                db.and_(Event.start_time >= start_datetime, Event.end_time <= end_datetime)
            )
        ).all()
        
        if overlapping_events:
            flash('Выбранное время перекрывается с другими событиями или с другими событиями на том же расписании. Пожалуйста, выберите другое время.')
            return redirect(url_for('edit_event', event_id=event_id))
        
        # Обновление данных события
        event.start_time = start_datetime
        event.end_time = end_datetime
        
        db.session.commit()
        flash('Событие успешно обновлено.')
        return redirect(url_for('super_admin_page'))
    else:
        schedules = Schedule.query.all()
        media_files = Media.query.all()
        return render_template('edit_event.html', event=event, schedules=schedules, media_files=media_files)


@app.route('/event/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Событие успешно удалено.')
    return redirect(url_for('super_admin_page'))


@app.route('/media/new', methods=['GET', 'POST'])
@login_required
def new_media():
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    if request.method == 'POST':
        if 'media' in request.files:
            file = request.files['media']
            if file.filename != '' and file.filename.endswith(('.mp4', '.avi')):
                tags = request.form.get('tags')  # Получение тегов из формы
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # Определение длительности видео
                try:
                    clip = VideoFileClip(filepath)
                    duration = str(datetime.timedelta(seconds=int(clip.duration)))
                except Exception as e:
                    flash(f'Ошибка при определении длительности файла: {e}')
                    duration = None  # В случае ошибки установить длительность как None
                # Проверка существования файла в БД
                existing_media = Media.query.filter_by(filename=filename).first()
                if existing_media:
                    flash('Файл уже существует в базе данных.')
                    return redirect(url_for('new_media'))
                # Создание нового медиа объекта
                new_media = Media(title=filename, filename=filename, filepath=filepath, duration=duration, tags=tags, status='Активен')
                db.session.add(new_media)
                db.session.commit()
                flash('Файл успешно загружен: {}'.format(filename))
                return redirect(url_for('media_player'))
            else:
                flash('Неподдерживаемый формат файла.')
        else:
            flash('Файл не выбран.')
    return render_template('edit_media.html', action='new')


@app.route('/media/edit/<int:media_id>', methods=['GET', 'POST'])
@login_required
def edit_media(media_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    media = Media.query.get_or_404(media_id)
    if request.method == 'POST':
        # Получаем новые теги из формы
        media.tags = request.form.get('tags')
        # Сохраняем обновленные данные в базе данных
        db.session.commit()
        flash('Информация о медиафайле обновлена.')
        return redirect(url_for('media_player', media_id=media_id))
    else:
        # Отображение формы для редактирования медиафайла
        return render_template('edit_media.html', media=media)


@app.route('/media/delete/<int:media_id>', methods=['POST'])
@login_required
def delete_media(media_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    media = Media.query.get_or_404(media_id)
    # Проверяем, связан ли медиафайл с какими-либо событиями
    if media.events:
        # Если медиафайл используется, предотвращаем его удаление
        flash('Этот медиафайл используется в одном или нескольких событиях и не может быть удалён.', 'error')
        return redirect(url_for('media_player'))
    else:
        # Если медиафайл не используется, удаляем его из базы данных и файловой системы
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], media.filename))
        except OSError as e:
            flash(f'Ошибка при удалении файла: {e}', 'error')
        db.session.delete(media)
        db.session.commit()
        flash('Медиафайл успешно удалён.', 'success')
        return redirect(url_for('media_player'))


@app.route('/media_player')
@login_required
def media_player():
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    media_files = Media.query.all()  # Получаем список всех медиафайлов из базы данных
    return render_template('media_player.html', media_files=media_files)





print("Перед if __name__ == '__main__':")


if __name__ == '__main__':
    try:
        print("Подключаемся к базе данных...")
        with app.app_context():
            print("Создаем таблицы...")
            db.create_all()
            add_media_from_folder('C:/Users/PC/Desktop/Python_Hope/static/videos')
        print("Успешное подключение к базе данных и создание таблиц!")
        
        # Запуск сервера Flask
        print("Запуск сервера Flask...")
        app.run(debug=True, threaded=True, host='0.0.0.0')
        
    except Exception as e:
        # Обработка ошибки при подключении
        print(f"Ошибка при запуске сервера Flask: {str(e)}")


print("После if __name__ == '__main__':")
