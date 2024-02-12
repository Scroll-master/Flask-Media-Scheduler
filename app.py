from flask import Flask, render_template, redirect, url_for, flash ,request, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from moviepy.editor import VideoFileClip
import pymysql
import secrets, json, os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import threading

app = Flask(__name__)

app.secret_key = secrets.token_hex(16)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:20120512LiBuN@localhost/Users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    

def add_media_from_folder(folder_path):
    existing_titles = {media.title for media in Media.query.all()}  # Собираем названия уже добавленных записей
    for filename in os.listdir(folder_path):
        if filename.endswith((".mp4", ".avi")) and filename not in existing_titles:
            filepath = os.path.join(folder_path, filename)
            clip = VideoFileClip(filepath)
            duration_seconds = int(clip.duration)
            duration_formatted = f"{duration_seconds // 3600:02d}:{(duration_seconds % 3600 // 60):02d}:{duration_seconds % 60:02d}"

            media = Media(
                title=filename,
                filename=filename,
                filepath=filepath,
                created_at=datetime.now(),
                duration=duration_formatted,
                tags=None  # Изначально теги отсутствуют
            )
            db.session.add(media)
    db.session.commit()



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    type = db.Column(db.String(50))  # Например, 'периодическое', 'исключение', 'специальная дата'
    events = db.relationship('Event', backref='schedule', lazy=True)



class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)  # Связь с медиафайлом
    start_time = db.Column(db.DateTime, nullable=False)  # Время начала события
    end_time = db.Column(db.DateTime, nullable=False)  # Время окончания события


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
    # Логика страницы Super_Admin
    return render_template('super_admin.html')




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
