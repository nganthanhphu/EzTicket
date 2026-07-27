import cloudinary
from flask import jsonify, render_template, request, redirect, url_for, session, flash
from flask_login import logout_user, login_user, current_user, login_required
from ezticketapp import app, dao
from ezticketapp.decorator import anonymous_required, run_validations
from cloudinary.uploader import upload  
from ezticketapp.models import User, Gender
import hashlib
def register_routes(app):
    @app.route("/")
    def home():
        page = request.args.get('page', 1, type=int)
        per_page = 10
        keyword = (request.args.get('keyword') or '').strip()
        location = (request.args.get('location') or '').strip()
        event_type_id = request.args.get('event_type', type=int)
        ticket_type_id = request.args.get('ticket_type', type=int)
        events = dao.load_events(
            keyword=keyword,
            location=location,
            event_type_id=event_type_id,
            ticket_type_id=ticket_type_id,
            page=page,
            per_page=per_page,
        )
        event_types = dao.get_event_types()
        ticket_types = dao.get_ticket_types()
        return render_template(
            "home.html",
            events=events,
            event_types=event_types,
            ticket_types=ticket_types,
        )

    @app.route('/events-partial')
    def events_partial():
        page = request.args.get('page', 1, type=int)
        per_page = 10
        keyword = (request.args.get('keyword') or '').strip()
        location = (request.args.get('location') or '').strip()
        event_type_id = request.args.get('event_type', type=int)
        ticket_type_id = request.args.get('ticket_type', type=int)
        events = dao.load_events(
            keyword=keyword,
            location=location,
            event_type_id=event_type_id,
            ticket_type_id=ticket_type_id,
            page=page,
            per_page=per_page,
        )
        return render_template("_event_list.html", events=events)

def register_auth_route(app):
    @app.route("/login", methods=["GET"])
    @anonymous_required
    def login():
        return render_template("auth/login.html")
    @app.route("/register", methods=["GET"])
    @anonymous_required
    def register():
        event_types = dao.get_event_types()
        return render_template("auth/register.html", event_types=event_types)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            preferred_event_type_id = request.form.get("preferred_event_type")
            gender_value = request.form.get("gender")

            if preferred_event_type_id:
                try:
                    preferred_event_type_id = int(preferred_event_type_id)
                except ValueError:
                    preferred_event_type_id = None
            else:
                preferred_event_type_id = None

            gender = None
            if gender_value:
                try:
                    gender = Gender[gender_value]
                except KeyError:
                    gender = None

            dao.update_user_profile(current_user, gender=gender, preferred_event_type_id=preferred_event_type_id)
            flash("Cập nhật hồ sơ thành công.")
            return redirect(url_for('profile'))

        event_types = dao.get_event_types()
        genders = list(Gender)
        return render_template("profile.html", event_types=event_types, genders=genders)


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
        preferred_event_type_id = request.form.get("preferred_event_type")
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

        if preferred_event_type_id:
            try:
                preferred_event_type_id = int(preferred_event_type_id)
            except ValueError:
                preferred_event_type_id = None
        else:
            preferred_event_type_id = None

        try:
            dao.add_user(
                name=full_name,
                email=email,
                password=password,
                avatar=avatar_url,
                preferred_event_type_id=preferred_event_type_id,
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