import hashlib
import cloudinary
from ezticketapp import login_manager

from flask import (
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from cloudinary.uploader import upload
from ezticketapp import app, dao

from ezticketapp.decorator import (
    anonymous_required,
    run_validations,
)

from ezticketapp.models import (
    User
)

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

    @app.route("/events/<int:event_id>")
    def event_detail(event_id):
        event = dao.get_event_by_id(event_id)

        if event is None:
            flash("Không tìm thấy sự kiện.")
            return redirect(url_for("home"))

        return render_template(
            "event_detail.html",
            event=event
        )

    @app.route("/tickets")
    def ticket_list():
        page = request.args.get("page", 1, type=int)

        keyword = (
                request.args.get("keyword") or ""
        ).strip()

        status = request.args.get("status")

        tickets = dao.load_orders(
            page=page,
            keyword=keyword,
            status=status,
            per_page=10
        )

        stats = dao.ticket_statistics()

        return render_template(
            "ticket/list.html",
            tickets=tickets,
            stats=stats,
            keyword=keyword,
            status=status
        )

    @app.route("/tickets/<int:order_id>")
    def ticket_detail(order_id):
        order = dao.get_order_detail(order_id)

        if order is None:
            flash("Không tìm thấy vé.")
            return redirect(url_for("ticket_list"))

        return render_template(
            "ticket/detail.html",
            order=order
        )

    @app.route("/tickets/pending")
    def pending_ticket():
        page = request.args.get(
            "page",
            1,
            type=int
        )

        keyword = (
                request.args.get("keyword") or ""
        ).strip()

        tickets = dao.load_pending_orders(
            page=page,
            keyword=keyword
        )

        stats = dao.ticket_statistics()

        return render_template(
            "ticket/list.html",
            tickets=tickets,
            stats=stats,
            keyword=keyword,
            status="PENDING"
        )

    @app.route(
        "/tickets/<int:order_id>/approve",
        methods=["POST"]
    )
    def approve_ticket(order_id):
        success, msg = dao.approve_order(order_id)

        flash(msg)

        return redirect(
            url_for(
                "ticket_detail",
                order_id=order_id
            )
        )

    @app.route(
        "/tickets/<int:order_id>/cancel",
        methods=["POST"]
    )
    def cancel_ticket(order_id):
        success, msg = dao.cancel_order(order_id)

        flash(msg)

        return redirect(
            url_for(
                "ticket_detail",
                order_id=order_id
            )
        )

    @app.route("/tickets/search")
    def search_ticket():
        keyword = (
                request.args.get("keyword") or ""
        ).strip()

        return redirect(
            url_for(
                "ticket_list",
                keyword=keyword
            )
        )

    @app.route("/tickets/filter")
    def filter_ticket():
        status = request.args.get("status")

        return redirect(
            url_for(
                "ticket_list",
                status=status
            )
        )

    @app.route("/api/tickets/<int:order_id>")
    def api_ticket_detail(order_id):

        order = dao.get_order_detail(order_id)

        if order is None:
            return jsonify({
                "success": False
            })

        return jsonify({

            "id": order.id,

            "customer": order.user.full_name,

            "email": order.user.email,

            "status": order.status.value,

            "date": order.date.strftime(
                "%d/%m/%Y %H:%M"
            ),

            "total_price": order.total_price

        })

    @app.route(
        "/api/tickets/<int:order_id>/approve",
        methods=["POST"]
    )
    def api_approve(order_id):

        success, msg = dao.approve_order(order_id)

        return jsonify({

            "success": success,

            "message": msg

        })

    @app.route(
        "/api/tickets/<int:order_id>/cancel",
        methods=["POST"]
    )
    def api_cancel(order_id):

        success, msg = dao.cancel_order(order_id)

        return jsonify({

            "success": success,

            "message": msg

        })

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

        avatar = getattr(user, 'avatar', None) or ''
        full_name = getattr(user, 'full_name', email)
        session['user_avatar'] = avatar
        session['user_full_name'] = full_name
        session['user_email'] = email

        flash("Đăng nhập thành công.")
        return redirect(url_for('home'))

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('home'))

@login_manager.user_loader
def load_user(user_id):
    return dao.load_user(user_id)

register_routes(app)
register_auth_route(app)

if __name__ == "__main__":
    app.run(debug=True)