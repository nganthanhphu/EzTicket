from datetime import datetime
import hashlib
import re
from ezticketapp.models import User
from flask_login import current_user    
from ezticketapp import db

def get_user_by_id(user_id):
    return User.query.filter_by(id=user_id).first()


def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def is_not_blank(value, field_name="Trường"):
    if not value or not value.strip():
        return False, f"{field_name} không được để trống"
    return True, None
    
def is_valid_length(value, min_len=0, max_len=255, field_name="Trường"):
    if len(value) < min_len:
        return False, f"{field_name} phải có ít nhất {min_len} ký tự"
    if len(value) > max_len:
        return False, f"{field_name} không được vượt quá {max_len} ký tự"
    return True, None


def is_valid_name(name):
    valid, msg = is_not_blank(name, "Tên")
    if not valid:
        return False, msg

    if not re.fullmatch(r"^[A-Za-zÀ-ỹ\s]+$", name):
        return False, "Tên chỉ được chứa chữ cái và khoảng trắng"

    return is_valid_length(name, 1, 50, "Tên")


def is_valid_email(email):
    if not email:
        return False, "Email không được để trống"

    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(pattern, email):
        return False, "Email không hợp lệ"

    return True, None

def is_unique_email(email):
    if get_user_by_email(email):
        return False, "Email đã tồn tại"
    return True, None

def is_valid_password(password):
    valid, msg = is_not_blank(password, "Mật khẩu")
    if not valid:
        return False, msg

    if len(password) < 8:
        return False, "Mật khẩu phải ít nhất 8 ký tự"
    if not re.search(r"[A-Z]", password):
        return False, "Mật khẩu phải có chữ hoa"
    if not re.search(r"[a-z]", password):
        return False, "Mật khẩu phải có chữ thường"
    if not re.search(r"[0-9]", password):
        return False, "Mật khẩu phải có số"
    if not re.search(r"[!@#$%^&*]", password):
        return False, "Mật khẩu phải có ký tự đặc biệt"

    return True, None


def is_valid_confirm(password, confirm):
    if password != confirm:
        return False, "Mật khẩu xác nhận không khớp."
    return True, None




def is_valid_avatar(file):
    if not file or file.filename == "":
        return True, None  # optional

    allowed_ext = ["jpg", "jpeg", "png", "webp"]
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext not in allowed_ext:
        return False, "Ảnh đại diện không hợp lệ"

    return True, None




def add_user(name, email,  password, avatar):

    valid, err_msg = is_valid_password(password)
    if not valid:
        raise ValueError("password is valid")
    password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
    u = User(
        full_name=name,
        email=email,
        password=password_hash,
        avatar=avatar,
    )

    print(u)
    db.session.add(u)
    db.session.commit()
