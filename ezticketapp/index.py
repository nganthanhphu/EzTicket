import os
import cloudinary
from flask import jsonify, render_template, request, redirect, url_for, session, flash
from flask_login import logout_user, login_user, current_user, login_required
from werkzeug.utils import secure_filename
from ezticketapp import app, dao
from ezticketapp.decorator import anonymous_required, run_validations, role_required
from cloudinary.uploader import upload
from ezticketapp.models import User, Gender, Role
import hashlib


def upload_event_image(image_file):
    if not image_file or not getattr(image_file, "filename", None):
        return None

    try:
        result = cloudinary.uploader.upload(image_file, folder="ezticket/events")
        return result.get("secure_url")
    except Exception as e:
        print("Cloudinary upload failed:", e)

    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        filename = secure_filename(image_file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(save_path)
        return f"/static/uploads/events/{filename}"
    except Exception as e:
        print("Local upload fallback failed:", e)
        return None


def register_routes(app):
    @app.route("/")
    def home():
        page = request.args.get('page', 1, type=int)
        keyword = (request.args.get('keyword') or '').strip()
        location = (request.args.get('location') or '').strip()
        event_type_id = request.args.get('event_type', type=int)
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        events = dao.load_events(
            keyword=keyword,
            location=location,
            event_type_id=event_type_id,
            min_price=min_price,
            max_price=max_price,
            page=page,
        )
        event_types = dao.get_event_types()
        return render_template(
            "home.html",
            events=events,
            event_types=event_types,
        )

    @app.route("/events/<int:event_id>")
    def event_detail(event_id):
        event = dao.get_event_by_id(event_id)

        if not event:
            flash("Không tìm thấy sự kiện.")
            return redirect(url_for("home"))

        return render_template(
            "event_detail.html",
            event=event
        )


def register_auth_route(app):
    @app.route("/login", methods=["GET"])
    @anonymous_required
    def login():
        return render_template("auth/login.html")

    @app.route("/register", methods=["GET"])
    @anonymous_required
    def register():
        event_types = dao.get_event_types()
        genders = list(Gender)
        return render_template("auth/register.html", event_types=event_types, genders=genders)

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

            dao.update_user_profile(
                current_user, gender=gender, preferred_event_type_id=preferred_event_type_id)
            flash("Cập nhật hồ sơ thành công.")
            return redirect(url_for('profile'))

        event_types = dao.get_event_types()
        genders = list(Gender)
        return render_template("profile.html", event_types=event_types, genders=genders)

    @app.route("/organizer/dashboard")
    @login_required
    @role_required("ORGANIZER")
    def organizer_dashboard():
        events = dao.load_my_events()
        return render_template("organizer/dashboard.html", total_events=len(events))

    @app.route("/organizer/events")
    @login_required
    @role_required("ORGANIZER")
    def organizer_events():
        events = dao.load_my_events()
        return render_template("organizer/events.html", events=events)

    @app.route("/organizer/events/create", methods=["GET", "POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_create_event():
        event_types = dao.get_event_types()

        if request.method == "POST":
            image_file = request.files.get("image")
            image_url = upload_event_image(image_file)

            if image_file and image_file.filename and not image_url:
                flash("Tải ảnh lên thất bại.")
                return render_template("organizer/event_edit.html", event=None, event_types=event_types, mode="create")

            success, message = dao.create_event(
                name=request.form.get("name"),
                location=request.form.get("location"),
                image=image_url,
                purchase_limit=int(request.form.get("purchase_limit", 1)),
                cancel_limit=int(request.form.get("cancel_limit", 0)),
                event_time=request.form.get("time"),
                event_type_id=int(request.form.get("event_type_id", event_types[0].id)),
                organizer_id=current_user.id,
            )

            flash(message)
            if success:
                created_event = dao.load_my_events()[-1]
                return redirect(url_for("organizer_edit_event", event_id=created_event.id))

        return render_template("organizer/event_edit.html", event=None, event_types=event_types, mode="create")

    @app.route("/organizer/events/<int:event_id>")
    @login_required
    @role_required("ORGANIZER")
    def organizer_event_detail(event_id):
        event = dao.get_event_by_id(event_id)
        if event is None:
            flash("Không tìm thấy sự kiện.")
            return redirect(url_for("organizer_events"))

        if event.organizer_id != current_user.id:
            flash("Bạn không có quyền.")
            return redirect(url_for("organizer_events"))

        tickets = dao.load_event_tickets(event.id)
        vouchers = dao.load_event_vouchers(event.id)
        return render_template(
            "organizer/event_detail.html",
            event=event,
            tickets=tickets,
            vouchers=vouchers,
        )

    @app.route("/organizer/events/<int:event_id>/edit", methods=["GET", "POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_edit_event(event_id):
        event = dao.get_event_by_id(event_id)
        if event is None:
            flash("Không tìm thấy sự kiện.")
            return redirect(url_for("organizer_events"))

        if event.organizer_id != current_user.id:
            flash("Bạn không có quyền.")
            return redirect(url_for("organizer_events"))

        if request.method == "POST":
            image_file = request.files.get("image")
            image_url = upload_event_image(image_file)

            if image_file and image_file.filename and not image_url:
                flash("Tải ảnh lên thất bại.")
                return redirect(url_for("organizer_edit_event", event_id=event.id))

            success, message = dao.update_event(event, request.form, image_url=image_url)
            flash(message)
            if success:
                return redirect(url_for("organizer_event_detail", event_id=event.id))

        tickets = dao.load_event_tickets(event.id)
        vouchers = dao.load_event_vouchers(event.id)
        ticket_types = dao.get_ticket_types()
        event_types = dao.get_event_types()
        return render_template(
            "organizer/event_edit.html",
            event=event,
            tickets=tickets,
            vouchers=vouchers,
            ticket_types=ticket_types,
            event_types=event_types,
            mode="edit",
        )

    @app.route("/organizer/events/<int:event_id>/tickets/create", methods=["POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_create_ticket(event_id):
        event = dao.get_event_by_id(event_id)
        if event is None or event.organizer_id != current_user.id:
            flash("Bạn không có quyền.")
            return redirect(url_for("organizer_events"))

        success, message = dao.create_event_ticket(
            event_id,
            int(request.form["ticket_type"]),
            float(request.form["price"]),
            int(request.form["quantity"]),
        )
        flash(message)
        return redirect(url_for("organizer_edit_event", event_id=event_id))

    @app.route("/organizer/tickets/<int:ticket_id>/edit", methods=["POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_edit_ticket(ticket_id):
        ticket = dao.get_event_ticket(ticket_id)
        if ticket is None:
            flash("Không tìm thấy vé.")
            return redirect(url_for("organizer_events"))

        event = dao.get_event_by_id(ticket.event_id)
        if event is None or event.organizer_id != current_user.id:
            flash("Bạn không có quyền.")
            return redirect(url_for("organizer_events"))

        success, message = dao.update_event_ticket(
            ticket.id,
            int(request.form["ticket_type"]),
            float(request.form["price"]),
            int(request.form["quantity"]),
        )
        flash(message)
        return redirect(url_for("organizer_edit_event", event_id=ticket.event_id))

    @app.route("/organizer/tickets/<int:ticket_id>/delete")
    @login_required
    @role_required("ORGANIZER")
    def organizer_delete_ticket(ticket_id):
        ticket = dao.get_event_ticket(ticket_id)
        if ticket is None:
            flash("Không tìm thấy vé.")
            return redirect(url_for("organizer_events"))

        event = dao.get_event_by_id(ticket.event_id)
        if event is None or event.organizer_id != current_user.id:
            flash("Bạn không có quyền.")
            return redirect(url_for("organizer_events"))

        success, message = dao.delete_event_ticket(ticket_id)
        flash(message)
        return redirect(url_for("organizer_edit_event", event_id=ticket.event_id))

    @app.route("/api/register", methods=["POST"])
    def api_register():
        data = request.form

        def get_safe(field):
            return (data.get(field) or "").strip()

        full_name = get_safe("name")
        email = get_safe("email")
        password = get_safe("password")
        confirm = get_safe("confirm")
        role = get_safe("role")
        gender = get_safe("gender")
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

        avatar_url = None
        if avatar_file and avatar_file.filename != "":
            try:
                res = cloudinary.uploader.upload(avatar_file)
                avatar_url = res.get("secure_url")
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
                role_name=role,
                gender_name=gender,
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
        if user.role == Role.ORGANIZER:
            return redirect(url_for("organizer_dashboard"))
        return redirect(url_for('home'))

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('home'))


if __name__ == "__main__":
    register_routes(app)
    register_auth_route(app)

    app.run(debug=True)