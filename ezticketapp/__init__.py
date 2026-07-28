import os
from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import cloudinary
import cloudinary.uploader  
load_dotenv()


app = Flask(__name__)
app.secret_key = 'EZT34232'
app.config["SQLALCHEMY_DATABASE_URI"] ='mysql+pymysql://root:123456@localhost/ezticketdb?charset=utf8mb4'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PAGE_SIZE"] = 10

db = SQLAlchemy(app=app)

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
)
