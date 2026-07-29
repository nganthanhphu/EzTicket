import cloudinary
from flask import jsonify, render_template, request, redirect, url_for, session, flash
from flask_login import logout_user ,login_user
from ezticketapp import app, dao
from ezticketapp.decorator import anonymous_required, run_validations
from cloudinary.uploader import upload  
from ezticketapp.models import User
import hashlib
def register_routes(app):
    @app.route("/")
    def home():
        return render_template("home.html")

def register_auth_route(app):
    @app.route("/login", methods=["GET"])
    @anonymous_required
    def login():
        return render_template("auth/login.html")
    @app.route("/register", methods=["GET"])
    @anonymous_required
    def register():
        return render_template("auth/register.html")




    @app.route("/api/register", methods=["POST"])
    def api_register():
        data = request.form

        print(data)
        def get_safe(field):
            return (data.get(field) or "").strip()


        full_name = get_safe("name")
        email = get_safe("email")
        password = get_safe("password")
        confirm = get_safe("confirm")
        avatar_file = request.files.get("avatar")


        valid, err_msg = run_validations([
            (dao.is_valid_name, [full_name]),
            (dao.is_valid_email, [email]),
            (dao.is_unique_email, [email]),
            (dao.is_valid_password, [password]),
            (dao.is_valid_confirm, [password, confirm]),
            (dao.is_valid_avatar, [avatar_file]),
        ])
        if not valid:
            flash(err_msg)
            return redirect(url_for('register'))

        DEFAULT_AVATAR = "https://res.cloudinary.com/dpxsbyyey/image/upload/v1775650754/avatar_user_nzinrm.webp"

        avatar_url = DEFAULT_AVATAR

        if avatar_file and avatar_file.filename != "":
            try:
                res = cloudinary.uploader.upload(avatar_file)
                avatar_url = res.get("secure_url", DEFAULT_AVATAR)
            except Exception as e:
                print(e)

        try:
            dao.add_user(
                name=full_name,
                email=email,
                password=password,
                avatar=avatar_url
            )

            flash("Đăng ký thành công. Vui lòng đăng nhập.")
            return redirect(url_for('login'))

        except Exception as e:
            print(e)
            return jsonify({
                "success": False,
                "err_msg": "Lỗi server"
            }), 500

    @app.route('/api/login', methods=['POST'])
    def api_login():
        data = request.form
        email = (data.get('email') or '').strip()
        password = (data.get('password') or '').strip()

        if not email or not password:
            flash("Thiếu thông tin đăng nhập.")
            return redirect(url_for('login'))

        user = None
        try:
            user = User.query.filter(User.email == email).first()
        except Exception as e:
            print(e)

        if not user:
            flash("Tài khoản không tồn tại.")
            return redirect(url_for('login'))

        pwd_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        if user.password != password and user.password != pwd_hash:
            flash("Mật khẩu không đúng.")
            return redirect(url_for('login'))
        login_user(user)
        avatar = getattr(user, 'avatar', None) or ''
        full_name = getattr(user, 'full_name', email)
        user.full_name = full_name
        user.avatar = avatar
        flash("Đăng nhập thành công.")
        return redirect(url_for('home'))


    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('home'))



    








if __name__ == "__main__":
    register_routes(app)
    register_auth_route(app)

    app.run(debug=True)