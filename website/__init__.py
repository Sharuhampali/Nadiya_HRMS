from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_uploads import UploadSet, configure_uploads, IMAGES, DOCUMENTS, UploadNotAllowed
import os
from flask_mail import Mail, Message
from datetime import datetime,time
from dotenv import load_dotenv
load_dotenv()
import os
from .oauth import oauth, configure_oauth
from flask_cors import CORS



db = SQLAlchemy()
DB_NAME = "database.db"
mail = Mail()




def create_app():
    load_dotenv()

    app = Flask(__name__)
    CORS(app,
     supports_credentials=True,
     origins=["https://high-essence-464010-f6.web.app"])


    # General config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['GOOGLE_API_KEY'] = os.getenv("GOOGLE_MAPS_API_KEY")

    # Uploads
    app.config['UPLOADS_DEFAULT_DEST'] = os.getenv('UPLOADS_DEFAULT_DEST')
    app.config['UPLOADED_PHOTOS_DEST'] = os.getenv('UPLOADED_PHOTOS_DEST')
    app.config['UPLOADED_DOCS_DEST'] = os.getenv('UPLOADED_DOCS_DEST')

    # Mail config
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = (os.getenv('MAIL_DEFAULT_SENDER_NAME'), os.getenv('MAIL_DEFAULT_SENDER_EMAIL'))
    app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True,
    REMEMBER_COOKIE_SAMESITE='None',
    REMEMBER_COOKIE_SECURE=True
)
    app.config['SESSION_COOKIE_NAME'] = '__session'

 
    from .auth import oauth
    oauth.init_app(app)


    db.init_app(app)

    photos = UploadSet('photos', IMAGES)
    docs = UploadSet('docs', DOCUMENTS)
    configure_uploads(app, (photos, docs))

    mail.init_app(app)
    configure_oauth(app)



    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User
    
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    

    def extract_area(address):
        if not address:
            return ''
        parts = address.split(',')
        if len(parts) > 1:
            return parts[1].strip()  # Assuming the second last part is the area
        return address

    app.jinja_env.filters['extract_area'] = extract_area

    def generate_maps_url(address):
        return f"https://www.google.com/maps/search/?api=1&query={address}"

    app.jinja_env.filters['maps_url'] = generate_maps_url

    

    def time_diff(start_time, end_time):
        fmt = "%H:%M"
        start = datetime.strptime(start_time, fmt)
        if end_time is None:
            return "Not Closed"
        end = datetime.strptime(end_time, fmt)
        diff = end - start
        return f"{diff.seconds // 3600}h {(diff.seconds % 3600) // 60}m"

    def convert_to_str(time_obj):
        if isinstance(time_obj, time):
            return time_obj.strftime("%H:%M")
        elif time_obj is None:
            return None
        return time_obj

    def calculate_entry_early(entry_time, ideal_entry="09:30"):
        entry_time = convert_to_str(entry_time)
        entry = datetime.strptime(entry_time, "%H:%M")
        ideal = datetime.strptime(ideal_entry, "%H:%M")
        if entry < ideal:
            return time_diff(entry_time, ideal.strftime("%H:%M"))
        return "0"

    def calculate_entry_late(entry_time, ideal_entry="09:30"):
        entry_time = convert_to_str(entry_time)
        entry = datetime.strptime(entry_time, "%H:%M")
        ideal = datetime.strptime(ideal_entry, "%H:%M")
        if entry > ideal:
            return time_diff(ideal.strftime("%H:%M"), entry_time)
        return "0"

    def calculate_exit_early(exit_time, ideal_exit="18:00"):
        exit_time = convert_to_str(exit_time)
        if exit_time is None:
            return "Exit time not set"
        exit = datetime.strptime(exit_time, "%H:%M")
        ideal = datetime.strptime(ideal_exit, "%H:%M")
        if exit < ideal:
            return time_diff(exit_time, ideal.strftime("%H:%M"))
        return "0"

    def calculate_exit_late(exit_time, ideal_exit="18:00"):
        exit_time = convert_to_str(exit_time)
        if exit_time is None:
            return "Exit time not set"
        exit = datetime.strptime(exit_time, "%H:%M")
        ideal = datetime.strptime(ideal_exit, "%H:%M")
        if exit > ideal:
            return time_diff(ideal.strftime("%H:%M"), exit_time)
        return "0"

  

    def determine_shift(entry_time, ideal_entry="18:00"):
        if entry_time is None:
            return "Invalid entry time"
        entry_time = convert_to_str(entry_time) 
        try:
            entry = datetime.strptime(entry_time, "%H:%M")  
        except ValueError:
            return "Invalid entry time format"
        ideal = datetime.strptime(ideal_entry, "%H:%M") 
        return "General" if entry < ideal else "Night"
    
    
    def is_late(entry_time, ideal_entry="09:30"):
        entry_time = convert_to_str(entry_time)
        entry = datetime.strptime(entry_time, "%H:%M")
        ideal = datetime.strptime(ideal_entry, "%H:%M")
        return entry > ideal
    
    def count_late_entries(attendances, ideal_entry="09:30"):
        late_count = 0
        for attendance in attendances:
            if is_late(attendance.entry_time, ideal_entry):
                late_count += 1
        return late_count




# Register custom filters
    app.jinja_env.filters['calculate_entry_early'] = calculate_entry_early
    app.jinja_env.filters['calculate_entry_late'] = calculate_entry_late
    app.jinja_env.filters['calculate_exit_early'] = calculate_exit_early
    app.jinja_env.filters['calculate_exit_late'] = calculate_exit_late
    app.jinja_env.filters['determine_shift'] = determine_shift
    app.jinja_env.filters['is_late'] = is_late
    app.jinja_env.filters['count_late_entries'] = count_late_entries

    
    @app.route('/healthz')
    def health():
        return "OK", 200


    return app


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')


