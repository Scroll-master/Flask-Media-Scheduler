from flask import Flask, render_template, redirect, url_for, flash, request, make_response, jsonify, current_app
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from moviepy.editor import VideoFileClip, AudioFileClip
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import requests
import pymysql
import secrets, json, os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  # Добавлен для безопасной загрузки файлов
import threading
import re
import subprocess

app = Flask(__name__)

app.secret_key = secrets.token_hex(16)

app.config['SERVER_NAME'] = '192.168.0.29:5000'
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
    
    
def create_users():
    # Проверка наличия пользователей в базе данных
    if not User.query.filter_by(username='Super_Admin').first():
        super_admin = User(
            username='Super_Admin',
            role='master',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        super_admin.set_password('08140215SuPA')  # Установка пароля через метод модели
        db.session.add(super_admin)

    if not User.query.filter_by(username='Admin').first():
        admin = User(
            username='Admin',
            role='admin',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        admin.set_password('08152114MiNA')  # Установка пароля через метод модели
        db.session.add(admin)
    
    # Сохранение изменений в базе данных
    db.session.commit()

# Этот код добавляет дополнительный уровень безопасности, используя методы модели для управления паролями.
    

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
        if filename.endswith((".mp4", ".avi", ".mp3")) and filename not in existing_media:
            filepath = os.path.join(folder_path, filename)
            if filename.endswith((".mp4", ".avi")):  # Это видеофайл
                clip = VideoFileClip(filepath)
            elif filename.endswith(".mp3"):  # Это аудиофайл
                clip = AudioFileClip(filepath)
            else:
                continue  # Пропустить файлы неизвестного формата

            duration_seconds = int(clip.duration)
            duration_formatted = f"{duration_seconds // 3600:02d}:{(duration_seconds % 3600 // 60):02d}:{duration_seconds % 60:02d}"

            new_media = Media(
                title=filename,
                filename=filename,
                filepath=filepath,
                created_at=datetime.now(),
                duration=duration_formatted,
                tags=None,
                status='Активен'
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


class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    ip_address = db.Column(db.String(15), nullable=False)
    location = db.Column(db.String(128))
    status = db.Column(db.Boolean, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey('node_group.id'))

class NodeGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    events = db.relationship('Event', secondary='nodegroup_event', backref='node_groups', lazy='dynamic')
    nodes = db.relationship('Node', backref='group', lazy=True)

    @property
    def active_schedule_type(self):
        now = datetime.now()
        print(f"Checking active schedule type for NodeGroup {self.name} at {now}")

        # Собираем все активные события в текущий момент времени
        active_events = [event for event in self.events if event.start_time <= now <= event.end_time]

        if not active_events:
            print("No active events found for this NodeGroup at the current time.")
            return None
        
        if len(active_events) == 1:
            # Если есть только одно активное событие, возвращаем его тип расписания
            only_event = active_events[0]
            print(f"Active event found: Event ID {only_event.id} with schedule type {only_event.schedule.type}")
            return only_event.schedule.type
        

        # Определяем событие с максимальным приоритетом
        highest_priority_event = max(active_events, key=lambda event: get_priority(event.schedule.type))

        # Проверяем, может ли это событие перекрыть другие активные события
        for event in active_events:
            if event.id != highest_priority_event.id and can_override(highest_priority_event.schedule.type, event.schedule.type):
                print(f"Active event found: Event ID {highest_priority_event.id} with schedule type {highest_priority_event.schedule.type}")
                return highest_priority_event.schedule.type

        print(f"Event with ID {highest_priority_event.id} does not have a higher priority to override other active events.")
        return None


class NodeGroupEvent(db.Model):
    __tablename__ = 'nodegroup_event'
    node_group_id = db.Column(db.Integer, db.ForeignKey('node_group.id'), primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), primary_key=True)



class PlaybackManager:
    def __init__(self):
        self.current_event = None
        self.event_stack = []

    def start_event(self, event_id, media_url):
        if self.current_event:
            self.event_stack.append(self.current_event)
        self.current_event = {'event_id': event_id, 'media_url': media_url}

    def end_current_event(self):
        if self.event_stack:
            self.current_event = self.event_stack.pop()
        else:
            self.current_event = None

    def get_current_media_url(self):
        if self.current_event:
            return self.current_event['media_url']
        return None

    def is_media_ended(self):
        if self.current_event and 'process' in self.current_event:
            ended = self.current_event['process'].poll() is not None
            print(f"Media process ended: {ended}")
            return ended
        print("No media process found")
        return True  # Если процесса нет, считаем медиа завершенным




# Глобальная переменная для управления воспроизведением
playback_manager = PlaybackManager()

def check_and_play_media(app):
    with app.app_context():
        now = datetime.now()
        print(f"Checking for active media to play at {now}")
        node_groups = NodeGroup.query.all()

        if not node_groups:
            print("No node groups found.")
            return

        for group in node_groups:
            print(f"Checking group {group.name}")
            active_type = group.active_schedule_type
            if not active_type:
                print(f"No active schedule type for group {group.name} at {now}")
                continue

            active_events = [event for event in group.events if event.schedule.type == active_type and event.start_time <= now <= event.end_time]
            if active_events:
                highest_priority_event = max(active_events, key=lambda event: get_priority(event.schedule.type))
                current_media_url = playback_manager.get_current_media_url()
                new_media_url = url_for('static', filename='videos/' + highest_priority_event.media.filename, _external=True)

                if current_media_url != new_media_url or playback_manager.is_media_ended():
                    playback_manager.start_event(highest_priority_event.id, new_media_url)
                    for node in group.nodes:
                        print(f"Attempting to send media to {node.ip_address} for event {highest_priority_event.id} with URL: {new_media_url}")
                        response = send_media_command(node.ip_address, new_media_url)
                        if response and response.status_code == 200:
                            print(f"Successfully sent media to {node.ip_address} for event {highest_priority_event.id}")
                        else:
                            print(f"Failed to send media to {node.ip_address} for event {highest_priority_event.id}")
            else:
                if playback_manager.current_event and playback_manager.is_media_ended():
                    playback_manager.end_current_event()
                    if playback_manager.get_current_media_url():
                        for node in group.nodes:
                            send_media_command(node.ip_address, playback_manager.get_current_media_url())



scheduler = BackgroundScheduler()


def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: check_and_play_media(app), 'interval', minutes=1)
    
    # Установите интервал проверки статуса нод в 30 секунд
    scheduler.add_job(lambda: check_node_status(), 'interval', seconds=30)
    
    scheduler.start()

    # Зарегистрируйте функцию shutdown для корректного завершения планировщика при закрытии приложения
    atexit.register(lambda: scheduler.shutdown())


def send_media_command(ip_address, media_url):
    try:
        # Замените URL на актуальный путь к API устройства
        response = requests.post(f"http://{ip_address}:5000/api/play", json={"media_url": media_url})
        response.raise_for_status()  # Это вызовет исключение, если запрос не успешен
        return response
    except requests.RequestException as e:
        print(f"Failed to send command to {ip_address}: {e}")
        return None



@app.route('/')
def hello_world():
    return render_template('index.html')   
#@app.route('/password')
#def passwordgem():
#        return password_hash
        
        
@app.route('/update_status', methods=['POST'])
@login_required  # Требование аутентификации
def update_status():
    data = request.json
    node = Node.query.filter_by(ip_address=data['ip_address']).first()
    if node:
        node.status = data['status']
        db.session.commit()
        return jsonify({'success': True, 'message': 'Status updated'}), 200
    return jsonify({'success': False, 'message': 'Node not found'}), 404        
         
        
@app.route('/api/nodes', methods=['GET'])
@login_required  # Требование аутентификации
def get_nodes_status():
    nodes = Node.query.all()  # Получаем все ноды из базы данных
    node_data = [{
        'ip_address': node.ip_address,
        'status': node.status,
        'group_name': node.group.name if node.group else 'No group',  # Указываем группу, если она есть
        'location': node.location
    } for node in nodes]
    return jsonify(node_data)  # Возвращаем данные в формате JSON        
            
            
@app.route('/node_statuses', methods=['GET'])
@login_required  # Требование аутентификации
def node_statuses():
    nodes = Node.query.filter(Node.group_id.isnot(None)).all()  # Только ноды с группами
    statuses = [{
        'ip_address': node.ip_address,
        'status': node.status,
        'group': node.group.name,
        'location': node.location  # добавлено, если нужно отобразить расположение ноды
    } for node in nodes]
    return jsonify(statuses)            
            
            
def check_node_status():
    with app.app_context():
        nodes = Node.query.filter(Node.group_id.isnot(None)).all()  # Только ноды с группами
        for node in nodes:
            try:
                # Логируем попытку запроса
                print(f"Checking status for {node.ip_address}")
                # Предполагаем, что у ноды есть эндпоинт /status для проверки её состояния
                response = requests.get(f'http://{node.ip_address}:5000/api/status', timeout=3)
                # Логируем успешный ответ
                print(f"Status for {node.ip_address}: {response.status_code}")
                # Устанавливаем статус в True, если нода отвечает корректно
                node.status = response.status_code == 200
            except requests.exceptions.RequestException as e:
                print(f"Failed to check status for {node.ip_address}: {e}")
                node.status = False  # Считаем ноду неактивной, если произошла ошибка
            db.session.commit()  # Сохраняем изменения статуса в базу данных            
           
            
           
        
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

@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('unauthorized.html'), 401



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
        
        schedule.name = name  # Обновляем имя
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

    if request.method == 'POST':
        schedule_id = request.form.get('schedule_id')
        media_id = request.form.get('media_id')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            flash('Указанное расписание не найдено.')
            return redirect(url_for('new_event'))

        current_type = schedule.type
        current_priority = get_priority(current_type)

        # Проверка на перекрытие времени с другими событиями
        overlapping_events = Event.query.filter(
            db.and_(
                Event.end_time > start_datetime,
                Event.start_time < end_datetime
            )
        ).all()

        for event in overlapping_events:
        # Проверяем, может ли текущее событие перекрыть существующее
            if get_priority(event.schedule.type) >= current_priority and not can_override(current_type, event.schedule.type):
                flash(f'Выбранное время перекрывается с событием ID {event.id}, которое не может быть перекрыто.')
                return redirect(url_for('new_event'))

        # Если нет перекрытия, создаем новое событие
        new_event = Event(schedule_id=schedule_id, media_id=media_id, start_time=start_datetime, end_time=end_datetime)
        db.session.add(new_event)
        db.session.commit()
        flash('Новое событие успешно создано.')
        return redirect(url_for('super_admin_page'))

    else:
        schedules = Schedule.query.all()
        media_files = Media.query.all()
        return render_template('edit_event.html', event=None, schedules=schedules, media_files=media_files)

def get_priority(schedule_type):
    priorities = {
        'исключение': 3,
        'специальная дата': 2,
        'повседневное': 1
    }
    return priorities.get(schedule_type, 0)  # Возвращаем 0 для неизвестных типов

def can_override(event_type, other_event_type):
    overriding_rules = {
        'исключение': ['повседневное', 'специальная дата', 'исключение'],
        'специальная дата': ['повседневное'],
        'повседневное': []
    }
    return other_event_type in overriding_rules[event_type]


@app.route('/event/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403

    event = Event.query.get_or_404(event_id)
    
    # Проверяем, связано ли событие с какой-либо группой нодов
    if any(group for group in NodeGroup.query.all() if event in group.events):
        flash('Событие уже используется в одной из групп нодов и не может быть отредактировано.', 'error')
        return redirect(url_for('super_admin_page'))


    if request.method == 'POST':
        schedule_id = request.form.get('schedule_id')
        media_id = request.form.get('media_id')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            flash('Указанное расписание не найдено.')
            return redirect(url_for('edit_event', event_id=event_id))

        current_type = schedule.type
        current_priority = get_priority(current_type)

        # Проверка на перекрытие времени с другими событиями
        overlapping_events = Event.query.filter(
            Event.id != event_id,
            Event.schedule_id == schedule_id,
            db.or_(
                db.and_(Event.start_time <= start_datetime, Event.end_time > start_datetime),
                db.and_(Event.start_time < end_datetime, Event.end_time >= end_datetime),
                db.and_(Event.start_time >= start_datetime, Event.end_time <= end_datetime)
            )
        ).all()

        for ev in overlapping_events:
            if get_priority(ev.schedule.type) >= current_priority and not can_override(current_type, ev.schedule.type):
                flash(f'Выбранное время перекрывается с событием ID {ev.id}, которое не может быть перекрыто.')
                return redirect(url_for('edit_event', event_id=event_id))

        # Обновление данных события
        event.schedule_id = schedule_id
        event.media_id = media_id
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
    
    # Проверяем, связано ли событие с какими-либо группами нодов
    if len(event.node_groups) > 0:  # Используем len() для проверки количества связанных групп нодов
        flash('Событие не может быть удалено, так как оно является частью одной или нескольких групп нодов.', 'error')
        return redirect(url_for('super_admin_page'))
    
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
            if file.filename != '' and file.filename.endswith(('.mp4', '.avi', '.mp3')):
                tags = request.form.get('tags')  # Получение тегов из формы
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # Определение длительности файла
                try:
                    if filename.endswith(('.mp4', '.avi')):
                        clip = VideoFileClip(filepath)
                    else:  # Это аудиофайл
                        clip = AudioFileClip(filepath)
                    duration = str(timedelta(seconds=int(clip.duration)))
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


@app.route('/node/new', methods=['GET', 'POST'])
@login_required
def new_node():
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    
     # Получение всех существующих нодов для отображения на странице
    existing_nodes = Node.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        ip_address = request.form.get('ip_address')
        location = request.form.get('location')
        
        # Проверка уникальности имени и IP-адреса нода
        existing_node_by_name = Node.query.filter_by(name=name).first()
        existing_node_by_ip = Node.query.filter_by(ip_address=ip_address).first()
        
        if existing_node_by_name:
            flash('Нод с таким именем уже существует.')
            return render_template('edit_node.html', node=None)
        
        if existing_node_by_ip:
            flash('Нод с таким IP-адресом уже существует.')
            return render_template('edit_node.html', node=None)
        
        # Добавленная проверка корректности IP-адреса
        if not re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip_address):
            flash('Некорректный формат IP-адреса.')
            return render_template('edit_node.html', node=None)
        
        
        # Создание и сохранение нового нода
        new_node = Node(name=name, ip_address=ip_address, location=location, status=True)  # По умолчанию статус 'включен'
        db.session.add(new_node)
        db.session.commit()
        flash('Новый нод успешно создан.')
        return redirect(url_for('node_interface'))
    return render_template('edit_node.html', node=None, existing_nodes=existing_nodes)


@app.route('/node/edit/<int:node_id>', methods=['GET', 'POST'])
@login_required
def edit_node(node_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    
    node = Node.query.get_or_404(node_id)
    
    # Получение всех существующих нодов кроме редактируемого
    existing_nodes = Node.query.filter(Node.id != node_id).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        ip_address = request.form.get('ip_address')
        
        # Проверка на уникальность имени и IP-адреса
        existing_node = Node.query.filter(Node.id != node_id, db.or_(Node.name == name, Node.ip_address == ip_address)).first()
        if existing_node:
            flash('Другой нод с таким именем или IP-адресом уже существует.')
            return render_template('edit_node.html', node=node)
        
        # Добавленная проверка корректности IP-адреса
        if not re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip_address):
            flash('Некорректный формат IP-адреса.')
            return render_template('edit_node.html', node=node)
        
        
        node.name = name
        node.ip_address = ip_address
        node.location = request.form.get('location')
        
        db.session.commit()
        flash('Нод успешно обновлен.')
        return redirect(url_for('node_interface'))
    
    return render_template('edit_node.html', node=node, existing_nodes=existing_nodes)



@app.route('/node/delete/<int:node_id>', methods=['POST'])
@login_required
def delete_node(node_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    node = Node.query.get_or_404(node_id)
    if node.group:  # Проверка, не является ли нод частью группы нодов
        flash('Нод является частью группы и не может быть удален. Пожалуйста, удалите нод из группы перед удалением.', 'error')
        return redirect(url_for('node_interface'))
    db.session.delete(node)
    db.session.commit()
    flash('Нод успешно удален.')
    return redirect(url_for('node_interface'))


@app.route('/node_interface')
@login_required
def node_interface():
    if current_user.role != 'master':
        return "Доступ запрещен", 403
    saved_presets = get_saved_presets()  # Получаем список сохраненных пресетов
    nodes = Node.query.all()  # Получаем список всех нодов из базы данных
    node_groups = NodeGroup.query.all()  # Получаем список всех групп нодов, если нужно
    events = Event.query.all()  # Получаем список всех событий, если это необходимо для интерфейса
    # Можете добавить другие запросы для получения дополнительных данных
    return render_template('node_interface.html', nodes=nodes, node_groups=node_groups, events=events, saved_presets=saved_presets)


@app.route('/nodegroup/new', methods=['GET', 'POST'])
@login_required
def new_nodegroup():
    if current_user.role != 'master':
        return "Доступ запрещен", 403

    if request.method == 'POST':
        name = request.form.get('name')
        node_ids = request.form.getlist('node_ids')  # Получаем список ID нодов
        event_ids = request.form.getlist('event_ids')  # Получаем список ID событий

        # Проверяем, существует ли уже группа с таким именем
        existing_group = NodeGroup.query.filter_by(name=name).first()
        if existing_group:
            flash('Группа с таким именем уже существует.')
            return redirect(url_for('new_nodegroup'))

        if not name or not node_ids or not event_ids:
            flash('Пожалуйста, заполните все поля.')
            return redirect(url_for('new_nodegroup'))

        new_group = NodeGroup(name=name)

        # Добавляем ноды в группу
        for node_id in node_ids:
            node = Node.query.get(node_id)
            if node and not node.group_id:  # Проверяем, не принадлежит ли нод уже какой-либо группе
                new_group.nodes.append(node)
            elif node:
                flash(f'Нод {node.name} с IP-адресом {node.ip_address} уже принадлежит другой группе.')
                continue  # Продолжаем обрабатывать следующие ноды, не прерывая цикл

        # Добавляем события в группу
        for event_id in event_ids:
            event = Event.query.get(event_id)
            if event:
                new_group.events.append(event)

        db.session.add(new_group)
        db.session.commit()
        flash('Новая группа нодов успешно создана.')
        return redirect(url_for('node_interface'))

    else:
        # Передаем данные для формы
        # Передаем данные для формы: выбираем ноды, которые не принадлежат никакой группе
        available_nodes = Node.query.filter(Node.group_id.is_(None)).all()
        events = Event.query.all()  # Добавляем загрузку всех событий для передачи в шаблон
        return render_template('edit_nodegroup.html',nodegroup=None, nodes=available_nodes, events=events)  # Используйте правильный шаблон для создания


@app.route('/nodegroup/edit/<int:nodegroup_id>', methods=['GET', 'POST'])
@login_required
def edit_nodegroup(nodegroup_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403

    nodegroup = NodeGroup.query.get_or_404(nodegroup_id)

    if request.method == 'POST':
        name = request.form.get('name').strip()
        if not name:
            flash('Название группы не может быть пустым.')
            return redirect(url_for('edit_nodegroup', nodegroup_id=nodegroup_id))

        selected_node_ids = set(request.form.getlist('node_ids'))
        selected_event_ids = set(request.form.getlist('event_ids'))

        # Проверяем, существует ли другая группа с таким же именем
        print(f"Checking for existing groups with name {name} excluding group {nodegroup_id}")
        existing_group = NodeGroup.query.filter(NodeGroup.id != nodegroup_id, NodeGroup.name == name).first()
        if existing_group:
            print(f"Found conflicting group with ID {existing_group.id}")
            flash('Группа нодов с таким именем уже существует.')
            return redirect(url_for('edit_nodegroup', nodegroup_id=nodegroup_id))

        # Обновляем данные группы
        nodegroup.name = name

        # Обновляем ноды и события в группе
        update_nodegroup_members(nodegroup, selected_node_ids, selected_event_ids)

        db.session.commit()
        flash('Группа нодов успешно обновлена.')
        return redirect(url_for('node_interface'))

    else:
        # Фильтрация нодов: выбираем те, что не принадлежат другим группам или уже входят в текущую группу
        available_nodes = Node.query.filter(db.or_(Node.group_id == None, Node.group_id == nodegroup_id)).all()
        all_events = Event.query.all()  # Загрузка всех событий для передачи в шаблон
        return render_template('edit_nodegroup.html', nodegroup=nodegroup, nodes=available_nodes, events=all_events)


def update_nodegroup_members(nodegroup, selected_node_ids, selected_event_ids):
    """Обновляет состав нодов и событий в группе."""
    # Обновляем ноды в группе
    # Получаем текущий список ID нодов в группе
    current_node_ids = {node.id for node in nodegroup.nodes}

    # Добавляем новые ноды к группе
    for node_id in selected_node_ids:
        if node_id not in current_node_ids:
            node = Node.query.get(node_id)
            if node and (node.group_id is None or node.group_id == nodegroup.id):
                nodegroup.nodes.append(node)

    # Удаляем ноды, которые были удалены из группы
    for node in list(nodegroup.nodes):
        if str(node.id) not in selected_node_ids:
            nodegroup.nodes.remove(node)

    # Обновляем события в группе
    # Получаем текущий список ID событий в группе
    current_event_ids = {event.id for event in nodegroup.events}

    # Добавляем новые события к группе
    for event_id in selected_event_ids:
        if event_id not in current_event_ids:
            event = Event.query.get(event_id)
            if event:
                # Проверка на наличие существующей связи между группой и событием
                if not any(e.id == event.id for e in nodegroup.events):
                    nodegroup.events.append(event)

    # Удаляем события, которые были удалены из группы
    for event in list(nodegroup.events):
        if str(event.id) not in selected_event_ids:
            nodegroup.events.remove(event)



@app.route('/nodegroup/delete/<int:nodegroup_id>', methods=['POST'])
@login_required
def delete_nodegroup(nodegroup_id):
    if current_user.role != 'master':
        return "Доступ запрещен", 403

    nodegroup = NodeGroup.query.get_or_404(nodegroup_id)

    # Если удаление инициировано процессом импорта
    if request.headers.get('Referer') and 'import_preset' in request.headers.get('Referer'):
        # Обнуляем group_id у всех нодов, которые принадлежали группе
        for node in nodegroup.nodes:
            node.group_id = None
        # Удаляем связи из промежуточной таблицы NodeGroupEvent
        NodeGroupEvent.query.filter_by(node_group_id=nodegroup_id).delete()
        # Удаляем саму группу
        db.session.delete(nodegroup)
        db.session.commit()
        flash('Группа нодов успешно удалена через импорт.', 'success')
    else:
        # Проверяем, не связаны ли с группой нодов какие-либо события или ноды
        if nodegroup.events.first() is not None or len(nodegroup.nodes) > 0:
            event_ids = ", ".join(str(event.id) for event in nodegroup.events.all())
            node_ids = ", ".join(str(node.id) for node in nodegroup.nodes)
            flash(f'Группа {nodegroup.name} связана с событиями: {event_ids} и нодами: {node_ids}.', 'error')
        else:
            # Удаляем связи из промежуточной таблицы NodeGroupEvent
            NodeGroupEvent.query.filter_by(node_group_id=nodegroup_id).delete()
            # Удаляем саму группу
            db.session.delete(nodegroup)
            db.session.commit()
            flash('Группа нодов успешно удалена.', 'success')

    return redirect(url_for('node_interface'))



@app.route('/add_node_to_group', methods=['POST'])
@login_required
def add_node_to_group():
    if current_user.role != 'master':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('node_interface'))

    node_id = request.form.get('node_id')
    group_id = request.form.get('group_id')

    node = Node.query.get(node_id)
    if node:
        node.group_id = group_id
        db.session.commit()
        flash('Узел успешно добавлен в группу', 'success')
    else:
        flash('Узел не найден', 'danger')

    return redirect(url_for('edit_nodegroup', id=group_id))

@app.route('/remove_node_from_group', methods=['POST'])
@login_required
def remove_node_from_group():
    if current_user.role != 'master':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('node_interface'))

    node_id = request.form.get('node_id')
    node = Node.query.get(node_id)
    if node:
        group_id = node.group_id
        node.group_id = None
        db.session.commit()
        flash('Узел успешно удален из группы', 'success')
    else:
        flash('Узел не найден', 'danger')

    return redirect(url_for('edit_nodegroup', id=group_id if group_id else None))

@app.route('/add_event_to_group', methods=['POST'])
@login_required
def add_event_to_group():
    if current_user.role != 'master':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    event_id = request.form.get('event_id')
    group_id = request.form.get('group_id')

    # Создаем новую связь между событием и группой
    node_group_event = NodeGroupEvent(node_group_id=group_id, event_id=event_id)
    db.session.add(node_group_event)
    db.session.commit()
    flash('Событие успешно добавлено в группу', 'success')
    return redirect(url_for('edit_nodegroup', id=group_id))

@app.route('/remove_event_from_group', methods=['POST'])
@login_required
def remove_event_from_group():
    if current_user.role != 'master':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    event_id = request.form.get('event_id')
    group_id = request.form.get('group_id')

    # Удаляем связь между событием и группой
    node_group_event = NodeGroupEvent.query.filter_by(node_group_id=group_id, event_id=event_id).first()
    if node_group_event:
        db.session.delete(node_group_event)
        db.session.commit()
        flash('Событие успешно удалено из группы', 'success')
    else:
        flash('Связь не найдена', 'danger')

    return redirect(url_for('edit_nodegroup', id=group_id))


def export_data_to_json(preset_name):
    data = {'node_groups': []}

    # Получаем все группы нодов
    node_groups = NodeGroup.query.all()

    # Обходим каждую группу нодов
    for group in node_groups:
        group_data = {
            'name': group.name,
            'nodes': [],
            'events': []
        }

        # Добавляем данные о нодах в группе
        for node in group.nodes:
            node_data = {
                'id': node.id,
                'name': node.name,
                'ip_address': node.ip_address,
                'location': node.location,
                'status': node.status
            }
            group_data['nodes'].append(node_data)

        # Добавляем данные о событиях, связанных с группой
        for event in group.events:
            event_data = {
                'id': event.id,
                'schedule_id': event.schedule_id,
                'media_id': event.media_id,
                'start_time': event.start_time.isoformat(),
                'end_time': event.end_time.isoformat()
                # Добавьте любые другие детали о событии, которые вы хотите экспортировать
            }
            group_data['events'].append(event_data)

        data['node_groups'].append(group_data)

    # Путь к файлу JSON
    json_file_path = os.path.join(app.root_path, 'static', 'SaveJson', f'{preset_name}.json')

    # Очищаем файл от информации перед сохранением новых данных
    with open(json_file_path, 'w') as f:
        f.truncate(0)

    # Сохраняем данные в JSON файл
    with open(json_file_path, 'w') as f:
        json.dump(data, f, indent=4)

    return 'Data exported successfully.'


@app.route('/export_preset', methods=['GET', 'POST'])
@login_required
def export_preset_route():
    if request.method == 'POST':
        if current_user.role != 'master':
            return "Доступ запрещен", 403

        preset_name = request.form.get('preset_name')

        # Если пользователь не ввел название пресета, вернем ошибку
        if not preset_name:
            flash('Пожалуйста, введите название пресета.')
            return redirect(url_for('export_preset_route'))

        # Проверяем, существует ли файл с таким же названием
        json_file_path = os.path.join(app.root_path, 'static', 'SaveJson', f'{preset_name}.json')
        if os.path.exists(json_file_path):
            flash(f'Файл с названием "{preset_name}" уже существует.', 'error')
            return redirect(url_for('export_preset_route'))

        # Вызываем функцию экспорта данных
        export_data_to_json(preset_name)

        flash(f'Пресет "{preset_name}" успешно создан.')
        return redirect(url_for('node_interface'))

    # Добавим возврат для случая GET запроса
    return render_template('create_export_preset.html')


def get_saved_presets():
    """Получает список сохраненных пресетов из папки сохранений."""
    save_json_dir = os.path.join(app.root_path, 'static', 'SaveJson')
    saved_presets = [f for f in os.listdir(save_json_dir) if f.endswith('.json')]
    return saved_presets



def import_data_from_json(json_file_path):
    try:
        # Удаляем существующие группы
        print("Deleting existing node groups...")
        delete_existing_groups()

        # Читаем данные из JSON файла
        print(f"Reading data from {json_file_path}...")
        with open(json_file_path, 'r') as file:
            data = json.load(file)

        # Создаем новые группы, ноды и события из данных JSON
        for group_data in data['node_groups']:
            print(f"Creating or updating node group '{group_data['name']}'...")
            group = NodeGroup.query.filter_by(name=group_data['name']).first()
            if not group:
                group = NodeGroup(name=group_data['name'])
                db.session.add(group)

            for node_data in group_data['nodes']:
                node = Node.query.filter_by(name=node_data['name']).first()
                if node:
                    # Обновляем существующий нод, если IP адрес изменился
                    if node.ip_address != node_data['ip_address']:
                        print(f"Updating IP address for node '{node_data['name']}' from {node.ip_address} to {node_data['ip_address']}")
                        node.ip_address = node_data['ip_address']
                    node.location = node_data['location']
                    node.status = node_data.get('status', True)
                else:
                    # Создаем новый нод, если он еще не существует
                    if not Node.query.filter_by(ip_address=node_data['ip_address']).first():
                        print(f"Adding new node '{node_data['name']}' with IP {node_data['ip_address']}")
                        node = Node(
                            name=node_data['name'],
                            ip_address=node_data['ip_address'],
                            location=node_data['location'],
                            status=node_data.get('status', True)
                        )
                        db.session.add(node)
                    else:
                        print(f"Node with IP {node_data['ip_address']} already exists and will not be added again.")
                group.nodes.append(node)

            for event_data in group_data['events']:
                event = Event.query.filter_by(
                    schedule_id=event_data.get('schedule_id'),
                    media_id=event_data.get('media_id'),
                    start_time=datetime.strptime(event_data['start_time'], '%Y-%m-%dT%H:%M:%S'),
                    end_time=datetime.strptime(event_data['end_time'], '%Y-%m-%dT%H:%M:%S')
                ).first()
                if not event:
                    print(f"Adding new event '{event_data['start_time']}' to group '{group.name}'...")
                    event = Event(
                        schedule_id=event_data['schedule_id'],
                        media_id=event_data['media_id'],
                        start_time=datetime.strptime(event_data['start_time'], '%Y-%m-%dT%H:%M:%S'),
                        end_time=datetime.strptime(event_data['end_time'], '%Y-%m-%dT%H:%M:%S')
                    )
                    db.session.add(event)
                else:
                    print(f"Updating event '{event_data['start_time']}' in group '{group.name}'...")
                    event.schedule_id = event_data['schedule_id']
                    event.media_id = event_data['media_id']
                group.events.append(event)

        db.session.commit()
        print("Data imported successfully.")
        return 'Data imported successfully.'
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f'Error importing data: {str(e)}')
        return f'Error importing data: {str(e)}'
    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        return f'Unexpected error: {str(e)}'






def delete_existing_groups():
    # Обнуляем group_id у всех нод, которые принадлежали любой группе
    Node.query.update({Node.group_id: None})
    
    # Если есть связующая таблица NodeGroupEvent, удаляем все связи
    NodeGroupEvent.query.delete()

    # Удаляем все группы нодов
    NodeGroup.query.delete()
    db.session.commit()


@app.route('/import_preset', methods=['GET', 'POST'])
@login_required
def import_preset_route():
    if request.method == 'GET':
        print("GET request received - this should not happen for import!")
        return "GET requests are not supported on this URL.", 405

    if current_user.role != 'master':
        return "Доступ запрещен", 403

    preset_name = request.form.get('preset_name')
    if preset_name.endswith('.json'):
        preset_name = preset_name[:-5]  # Убираем расширение .json

    json_file_path = os.path.join(app.root_path, 'static', 'SaveJson', f'{preset_name}.json')
    print(f"Attempting to import from {json_file_path}")  # Логирование пути файла

    import_data_from_json(json_file_path)

    if NodeGroup.query.count() > 0:
        flash('Data imported successfully.', 'success')
    else:
        flash('Failed to import data.', 'error')
        
    return redirect(url_for('node_interface'))


@app.route('/delete_preset', methods=['POST'])
@login_required
def delete_preset_route():
    if current_user.role != 'master':
        return "Доступ запрещен", 403

    preset_name = request.form.get('preset_name')
    file_path = os.path.join(app.root_path, 'static', 'SaveJson', preset_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            flash('Файл успешно удален.', 'success')
        except Exception as e:
            flash(f'Ошибка при удалении файла: {str(e)}', 'error')
    else:
        flash('Файл не найден.', 'error')

    return redirect(url_for('node_interface'))




print("Перед if __name__ == '__main__':")


if __name__ == '__main__':
    try:
        print("Подключаемся к базе данных...")
        with app.app_context():
            print("Создаем таблицы...")
            db.create_all()
            
            print("Добавляем начальные данные в базу...")
            create_users()  # Вызов функции для создания пользователей
            add_media_from_folder('C:/Users/PC/Desktop/Python_Hope/static/videos')
            
        print("Успешное подключение к базе данных и создание таблиц!")
        
        # Запуск сервера Flask
        print("Запуск сервера Flask...")
        start_scheduler(app) # Передаем экземпляр app в функцию start_scheduler
        app.run(debug=True, threaded=True, host='0.0.0.0')
        
    except Exception as e:
        # Обработка ошибки при подключении
        print(f"Ошибка при запуске сервера Flask: {str(e)}")


print("После if __name__ == '__main__':")
