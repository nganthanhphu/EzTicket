import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
import cloudinary
from google import genai
from firebase_admin import credentials
import firebase_admin
load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 6
db = SQLAlchemy(app=app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, "firebase", "serviceAccountKey.json")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH") or DEFAULT_FIREBASE_CREDENTIALS_PATH
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    from ezticketapp.dao import get_user_by_id
    return get_user_by_id(int(user_id))


login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    from ezticketapp.dao import get_user_by_id
    return get_user_by_id(int(user_id))


cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
)

FACE_VERIFICATION_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]


gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

mail = Mail(app)


if os.path.exists(FIREBASE_CREDENTIALS_PATH):
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DATABASE_URL
    })
