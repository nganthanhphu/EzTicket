import hashlib
import hmac
import os
from datetime import datetime, timedelta

import cloudinary
import requests
from PIL import Image
from flask import jsonify, render_template, request, redirect, url_for, session, flash
from flask_login import logout_user, login_user, current_user, login_required
from flask_mail import Message
from ezticketapp import app, dao, db, utils, gemini_client, mail, FACE_VERIFICATION_MODELS
from ezticketapp.decorator import anonymous_required, run_validations, role_required
from cloudinary.uploader import upload
from ezticketapp.models import Order, OrderItem, User, Gender, OrderStatus, Role
from google.genai import types
import base64
from io import BytesIO
from ezticketapp.admin import init_admin

init_admin(app)


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

    @app.context_processor
    def common_attributes():
        if current_user.is_authenticated:
            token = utils.get_firebase_custom_token(current_user.id)
            return dict(firebase_custom_token=token)
        return dict(firebase_custom_token=None)


def register_auth_route(app):
    @app.route("/login", methods=["GET"])
    @anonymous_required
    def login():
        return render_template("auth/login.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    @anonymous_required
    def admin_login():
        if current_user.is_authenticated and current_user.role == Role.ADMIN:
            return redirect(url_for("admin.index"))

        if request.method == "POST":
            email = (request.form.get("email") or "").strip()
            password = (request.form.get("password") or "").strip()

            if not email or not password:
                flash("Thiếu thông tin đăng nhập.")
                return render_template("admin/login.html")

            user = User.query.filter(User.email.ilike(email)).first()
            if not user:
                flash("Tài khoản không tồn tại.")
                return render_template("admin/login.html")

            pwd_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
            if user.password != password and user.password != pwd_hash:
                flash("Mật khẩu không đúng.")
                return render_template("admin/login.html")

            if user.role != Role.ADMIN:
                flash("Tài khoản của bạn không có quyền Quản trị viên (Admin).")
                return render_template("admin/login.html")

            if not user.active:
                flash("Tài khoản của bạn đang chờ duyệt.")
                return render_template("admin/login.html")

            login_user(user)
            flash("Đăng nhập Admin thành công.")
            next_url = request.args.get("next") or url_for("admin.index")
            return redirect(next_url)

        return render_template("admin/login.html")

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
        orders = Order.query.filter_by(
            user_id=current_user.id).order_by(Order.date.desc()).all()
        return render_template("profile.html", event_types=event_types, genders=genders, orders=orders)

    @app.route("/my-tickets")
    @login_required
    def my_tickets():
        orders = (Order.query.filter_by(
            user_id=current_user.id).order_by(Order.date.desc()).all())

        return render_template("my_tickets.html", orders=orders)

    @app.route("/orders/<int:order_id>/cancel", methods=["POST"])
    @login_required
    def cancel_order(order_id):
        order = dao.get_order_by_id(order_id)
        if not order:
            flash("Không tìm thấy đơn hàng.")
            return redirect(url_for('my_tickets'))

        if order.user_id != current_user.id:
            flash("Bạn không có quyền hủy đơn hàng này.")
            return redirect(url_for('my_tickets'))

        if not utils.can_cancel_order(order):
            flash("Đơn hàng này không thể hủy ở trạng thái hiện tại hoặc đã quá hạn hủy.")
            return redirect(url_for('my_tickets'))

        order_items = getattr(order, "order_items", None) or []
        event = None

        if order_items:
            first_item = order_items[0]
            event_ticket = getattr(first_item, "event_ticket", None)
            if event_ticket:
                event = getattr(event_ticket, "event", None)

        if not event:
            flash("Không xác định được sự kiện của đơn hàng.")
            return redirect(url_for('my_tickets'))

        try:
            with db.session.begin_nested():
                dao.update_order(order_id, status=OrderStatus.CANCELLED)
                dao.update_tickets_quantity(
                    order.order_items, is_increase=True)
                dao.update_voucher_quantity(order.voucher_id, is_increase=True)
                db.session.commit()

            try:
                msg = Message(
                    subject=f"EzTicket - Hủy vé thành công (Đơn hàng #{order.id})",
                    sender=os.getenv("MAIL_USERNAME"),
                    recipients=[order.user.email],
                    body=(
                        f"Xin chào {order.user.full_name},\n\n"
                        f"Bạn đã hủy thành công đơn hàng #{order.id}.\n"
                        f"Sự kiện: {event.name}\n"
                        f"Thời gian hủy: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                        f"Trân trọng,\nEZTicket Team"
                    )
                )
                mail.send(msg)
            except Exception as email_error:
                print(email_error)

            flash("Hủy vé thành công.")
        except Exception as e:
            print(e)
            db.session.rollback()
            flash("Hủy vé thất bại. Vui lòng thử lại.")

        return redirect(url_for('my_tickets'))

    @app.route("/organizer/dashboard")
    @login_required
    @role_required("ORGANIZER")
    def organizer_dashboard():
        filter_type = request.args.get("filter_type", "").strip()
        date_val = request.args.get("date_val", "").strip()
        week_date = request.args.get("week_date", "").strip()
        year = request.args.get("year", type=int)
        quarter = request.args.get("quarter", type=int)
        month = request.args.get("month", type=int)
        # loc mạc dinh la theo ngay hien tai
        if not filter_type and not any([week_date, year, quarter, month]):
            filter_type = "date"
            if not date_val:
                date_val = datetime.now().strftime("%Y-%m-%d")
        elif filter_type == "date" and not date_val:
            date_val = datetime.now().strftime("%Y-%m-%d")

        events = dao.load_my_events()

        # Lấy Top 5 sự kiện có doanh thu cao nhất theo bộ lọc
        top_5_events = dao.get_top_revenue_events(
            limit=5,
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        )
        labels = [item['event'].name for item in top_5_events]
        revenues = [item['revenue'] for item in top_5_events]

        # Tính tổng doanh thu tất cả sự kiện trong khoảng thời gian đã chọn
        all_revenues = [
            float(
                dao.revenue_event(
                    e.id,
                    filter_type=filter_type,
                    date_val=date_val,
                    week_date=week_date,
                    month=month,
                    quarter=quarter,
                    year=year
                ) or 0
            ) for e in events
        ]
        total_revenue = sum(all_revenues)

        years = dao.get_revenue_years()

        # Thống kê doanh thu tất cả sự kiện (Line Chart)
        all_event_labels, all_event_revenues = dao.get_all_events_revenue(
            organizer_id=current_user.id,
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        )

        # Thống kê doanh thu theo ngày (Line Chart)
        daily_labels, daily_revenues = dao.get_daily_revenue_stats(
            organizer_id=current_user.id,
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        )

        return render_template("organizer/dashboard.html",
                               total_events=len(events),
                               labels=labels,
                               revenues=revenues,
                               all_event_labels=all_event_labels,
                               all_event_revenues=all_event_revenues,
                               daily_labels=daily_labels,
                               daily_revenues=daily_revenues,
                               selected_filter_type=filter_type,
                               selected_date_val=date_val,
                               selected_week_date=week_date,
                               selected_year=year,
                               selected_quarter=quarter,
                               selected_month=month,
                               total_revenue=total_revenue,
                               years=years)

    @app.route("/organizer/verify-ticket", methods=["GET"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_verify_ticket():
        return render_template("organizer/verify_ticket.html")

    @app.route("/organizer/verify-ticket/qr", methods=["POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_verify_ticket_qr():
        payload = request.get_json(silent=True) or {}
        image_data = payload.get("image")
        if not image_data:
            return jsonify({"success": False, "message": "Không nhận được dữ liệu ảnh."}), 400

        try:
            from pyzbar.pyzbar import decode
            import numpy as np
            from PIL import Image as PILImage

            img_bytes = base64.b64decode(image_data)
            img = PILImage.open(BytesIO(img_bytes)).convert("RGB")
            arr = np.array(img)
            decoded = decode(arr)
            if not decoded:
                return jsonify({"success": False, "message": "Không đọc được mã QR. Vui lòng chụp lại."}), 400

            auth_code = decoded[0].data.decode(
                "utf-8", errors="ignore").strip()
            order = Order.query.filter_by(
                authentication_code=auth_code).first()
            if not order:
                return jsonify({"success": False, "message": "Mã QR không khớp với đơn hàng hợp lệ."}), 404

            event = utils.get_order_event(order)
            if not event:
                return jsonify({"success": False, "message": "Không tìm thấy sự kiện của đơn hàng."}), 404
            if getattr(event, "organizer_id", None) != current_user.id:
                return jsonify({"success": False, "message": "Đơn hàng không thuộc sự kiện bạn quản lý."}), 403

            order_status = getattr(
                getattr(order, "status", None), "name", getattr(order, "status", None))
            if order_status != OrderStatus.PAID.name:
                return jsonify({"success": False, "message": "Đơn hàng chưa ở trạng thái PAID nên chưa thể xác thực."}), 400

            order_items = getattr(order, "order_items", None) or []
            ticket_summary = []
            total_tickets = 0
            for item in order_items:
                ticket = getattr(item, "event_ticket", None)
                ticket_type = getattr(
                    getattr(ticket, "ticket_type", None), "name", "Không xác định")
                quantity = getattr(item, 'quantity', 0)
                total_tickets += quantity
                ticket_summary.append(f"{ticket_type}: x{quantity}")

            order_date = order.date.strftime(
                "%d/%m/%Y %H:%M") if order.date else "Không xác định"
            customer_name = getattr(
                order.user, "full_name", "Không xác định") if order.user else "Không xác định"
            customer_email = getattr(
                order.user, "email", "Không xác định") if order.user else "Không xác định"

            summary = """
            <div class="row">
                <div class="col-md-6">
                    <div><strong>Sự kiện:</strong> {}</div>
                    <div><strong>Mã đơn:</strong> #{}</div>
                    <div><strong>Ngày đặt:</strong> {}</div>
                </div>
                <div class="col-md-6">
                    <div><strong>Khách hàng:</strong> {}</div>
                    <div><strong>Email:</strong> {}</div>
                </div>
            </div>
            <hr>
            <div><strong>Vé đã đặt ({} vé):</strong></div>
            <div>{}</div>
            """.format(
                getattr(event, "name", "Không xác định"),
                order.id,
                order_date,
                customer_name,
                customer_email,
                total_tickets,
                "<br>".join(
                    ticket_summary) if ticket_summary else "Không có thông tin vé"
            )

            return jsonify({
                "success": True,
                "message": "Quét QR thành công. Vui lòng xác thực khuôn mặt.",
                "order_id": order.id,
                "authentication_code": auth_code,
                "summary": summary,
                "qr_image": image_data,
            })
        except Exception as e:
            print(e)
            return jsonify({"success": False, "message": "Không thể xử lý ảnh QR."}), 500

    @app.route("/organizer/verify-ticket/face", methods=["POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_verify_ticket_face():
        payload = request.get_json(silent=True) or {}
        image_data = payload.get("image")
        order_id = payload.get("order_id")
        if not image_data or not order_id:
            return jsonify({"success": False, "message": "Thiếu dữ liệu ảnh hoặc đơn hàng."}), 400

        try:
            order = dao.get_order_by_id(int(order_id))
            if not order:
                return jsonify({"success": False, "message": "Đơn hàng không tồn tại."}), 404

            event = utils.get_order_event(order)
            if not event or getattr(event, "organizer_id", None) != current_user.id:
                return jsonify({"success": False, "message": "Đơn hàng không thuộc sự kiện bạn quản lý."}), 403

            if not getattr(order, "authentication_face", None):
                return jsonify({"success": False, "message": "Khách hàng chưa có ảnh xác minh khuôn mặt trong hệ thống."}), 400

            try:
                face_url = getattr(order, "authentication_face", None)
                stored_image = requests.get(face_url, timeout=20)
                stored_image.raise_for_status()
            except Exception as url_err:
                print(f"Error fetching stored face image: {url_err}")
                return jsonify({"success": False, "message": "Không thể tải ảnh xác minh khuôn mặt từ hệ thống."}), 400

            try:
                img_bytes = base64.b64decode(image_data)
                live_image = Image.open(BytesIO(img_bytes))
                stored_image_obj = Image.open(BytesIO(stored_image.content))
            except Exception as img_err:
                print(f"Error processing images: {img_err}")
                return jsonify({"success": False, "message": "Lỗi xử lý ảnh. Vui lòng chụp lại."}), 400

            try:
                config = types.GenerateContentConfig(
                    system_instruction="Bạn là chuyên gia nhận diện khuôn mặt. Hãy so sánh hai ảnh: ảnh gốc đã lưu trong hệ thống và ảnh chụp mới. Nếu là cùng một người và đủ điều kiện nhận diện, hãy trả về đúng dòng 'MATCH'. Nếu không khớp, trả về 'NO_MATCH'."
                )

                response = None
                last_error = None

                for model_name in FACE_VERIFICATION_MODELS:
                    try:
                        print(f"Trying model: {model_name}")
                        response = gemini_client.models.generate_content(
                            model=model_name,
                            contents=[stored_image_obj, live_image],
                            config=config,
                        )
                        print(f"Model {model_name} succeeded")
                        break
                    except Exception as model_err:
                        print(f"Model {model_name} failed: {model_err}")
                        last_error = model_err
                        continue

                if response is None:
                    raise Exception(
                        f"All models failed. Last error: {last_error}")

                result = (response.text or "").strip().upper()
                print(f"Face verification result: {result}")

                if result == "MATCH":
                    return jsonify({"success": True, "message": "Khuôn mặt khớp. Bạn có thể xác nhận vé."})
                else:
                    return jsonify({"success": False, "message": "Khuôn mặt không khớp. Vui lòng thử lại."}), 400
            except Exception as ai_err:
                print(f"Error during face recognition: {ai_err}")
                return jsonify({"success": False, "message": "Lỗi trong quá trình nhận diện khuôn mặt. Vui lòng thử lại."}), 400

        except Exception as e:
            print(f"Unexpected error in face verification: {e}")
            return jsonify({"success": False, "message": "Không thể xử lý ảnh khuôn mặt."}), 500

    @app.route("/organizer/verify-ticket/confirm", methods=["POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_verify_ticket_confirm():
        payload = request.get_json(silent=True) or {}
        order_id = payload.get("order_id")
        if not order_id:
            return jsonify({"success": False, "message": "Thiếu thông tin đơn hàng."}), 400

        order = dao.get_order_by_id(int(order_id))
        if not order:
            return jsonify({"success": False, "message": "Đơn hàng không tồn tại."}), 404

        event = utils.get_order_event(order)
        if not event or getattr(event, "organizer_id", None) != current_user.id:
            return jsonify({"success": False, "message": "Đơn hàng không thuộc sự kiện bạn quản lý."}), 403

        if getattr(getattr(order, "status", None), "name", getattr(order, "status", None)) != OrderStatus.PAID.name:
            return jsonify({"success": False, "message": "Đơn hàng không còn ở trạng thái PAID."}), 400

        try:
            with db.session.begin_nested():
                dao.update_order(int(order_id), status=OrderStatus.COMPLETED)
                db.session.commit()
            return jsonify({"success": True, "message": "Xác thực vé thành công. Đơn hàng đã chuyển sang COMPLETED."})
        except Exception as e:
            print(e)
            db.session.rollback()
            return jsonify({"success": False, "message": "Không thể cập nhật trạng thái vé."}), 500

    @app.route("/organizer/events/<int:event_id>/delete", methods=["GET", "POST", "DELETE"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_delete_event(event_id):
        event = dao.get_event_by_id(event_id)
        if not event:
            flash("Không tìm thấy sự kiện.")
            return redirect(url_for("organizer_events"))

        if dao.has_order(event_id):
            flash("Không thể xóa sự kiện này vì đã có đơn hàng liên quan.")
            return redirect(url_for("organizer_events"))

        if event.organizer_id != current_user.id:
            flash("Bạn không có quyền xóa sự kiện này.")
            return redirect(url_for("organizer_events"))

        success, message = dao.delete_event(event_id)
        flash(message)
        return redirect(url_for("organizer_events"))

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
            image_url = None

            if image_file and image_file.filename:
                try:
                    res = cloudinary.uploader.upload(image_file)
                    image_url = res.get("url")
                except Exception as e:
                    print(e)
                    flash("Tải ảnh lên thất bại.")
                    return render_template("organizer/event_edit.html", event=None, event_types=event_types, mode="create")

            success, message = dao.create_event(
                name=request.form.get("name"),
                location=request.form.get("location"),
                image=image_url,
                purchase_limit=int(request.form.get("purchase_limit", 1)),
                cancel_limit=int(request.form.get("cancel_limit", 0)),
                event_time=request.form.get("time"),
                event_type_id=int(request.form.get(
                    "event_type_id", event_types[0].id)),
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
        for t in tickets:
            t.suggested_price = dao.suggest_ticket_price(t.id)
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
            image_url = None

            if image_file and image_file.filename:
                res = cloudinary.uploader.upload(image_file)
                image_url = res.get("secure_url")

            if image_file and image_file.filename and not image_url:
                flash("Tải ảnh lên thất bại.")
                return redirect(url_for("organizer_edit_event", event_id=event.id))

            success, message = dao.update_event(
                event, request.form, image_url=image_url)
            flash(message)
            if success:
                utils.handle_event_info_change_notification(event)
                return redirect(url_for("organizer_event_detail", event_id=event.id))

        tickets = dao.load_event_tickets(event.id)
        for t in tickets:
            t.suggested_price = dao.suggest_ticket_price(t.id)
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

        if request.method == "POST":
            image_file = request.files.get("image")
            image_url = None

            if image_file and image_file.filename:
                res = cloudinary.uploader.upload(image_file)
                image_url = res.get("secure_url")

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

    @app.route("/organizer/events/<int:event_id>/vouchers/create", methods=["POST"])
    @login_required
    @role_required("ORGANIZER")
    def organizer_create_voucher(event_id):
        event = dao.get_event_by_id(event_id)

        if event is None or event.organizer_id != current_user.id:
            flash("Bạn không có quyền.")
            return redirect(url_for("organizer_events"))
        # lấy input từ form
        code = (request.form.get("code") or "").strip().upper()
        discount = float(request.form.get("discount_amount", 0))
        quantity = int(request.form.get("quantity", 0))
        expiration_date_text = request.form.get("expiration_date")
        # bắt buộc nhập mã voucher và ngày hết hạn
        if not code or not expiration_date_text:
            flash("Vui lòng nhập mã voucher và ngày hết hạn.")
            return redirect(url_for("organizer_edit_event", event_id=event_id))

        voucher_quantity = int(request.form.get("quantity", 0))
        tickets = dao.load_event_tickets(event_id)
        event_tickets_quantity = sum(ticket.quantity for ticket in tickets)

        # số lượng voucher hok đc nhiều hơn số lượng vé sự kiện đó
        if (discount <= 1 or discount > 100):
            flash("Giảm giá phải lớn hơn 0 và nhỏ hơn hoặc bằng 100.")
            return redirect(url_for("organizer_edit_event", event_id=event_id))
        if voucher_quantity > event_tickets_quantity or voucher_quantity <= 0:
            flash(
                "Số lượng voucher không được vượt quá số lượng vé hoặc không được nhỏ hơn 0.")
            return redirect(url_for("organizer_edit_event", event_id=event_id))
        if datetime.strptime(expiration_date_text, "%Y-%m-%d") < datetime.now():
            flash("Ngày hết hạn không được nhỏ hơn ngày hiện tại.")
            return redirect(url_for("organizer_edit_event", event_id=event_id))
        try:
            expiration_date = datetime.strptime(
                expiration_date_text, "%Y-%m-%d")
        except ValueError:
            flash("Ngày hết hạn không hợp lệ.")
            return redirect(url_for("organizer_edit_event", event_id=event_id))

        success, message = dao.create_voucher(
            event_id,
            code,
            discount,
            quantity,
            expiration_date,
        )

        flash(message)
        return redirect(url_for("organizer_edit_event", event_id=event_id))

    @app.route("/api/register", methods=["POST"])
    @anonymous_required
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
            (utils.is_valid_name, [full_name]),
            (utils.is_valid_email, [email]),
            (dao.is_unique_email, [email]),
            (utils.is_valid_password, [password]),
            (utils.is_valid_confirm, [password, confirm]),
            (utils.is_valid_avatar, [avatar_file]),
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

        active = role != "ORGANIZER"
        try:
            dao.add_user(
                name=full_name,
                email=email,
                password=password,
                avatar=avatar_url,
                role_name=role,
                gender_name=gender,
                preferred_event_type_id=preferred_event_type_id,
                active=active,
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
    @anonymous_required
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

        if user.role == Role.ADMIN:
            flash("Tài khoản Admin không được phép đăng nhập ở trang Khách hàng.")
            return redirect(url_for('login'))

        if not user.active:
            flash("Tài khoản của bạn đang chờ duyệt.")
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
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('home'))


def register_order_routes(app):

    @app.route("/events/<int:event_id>/order", methods=["GET", "POST"])
    @login_required
    @role_required("CUSTOMER")
    def ticket_order(event_id):
        event = dao.get_event_by_id(event_id)
        max_available_tickets = 0

        if event.tickets:
            for ticket in event.tickets:
                max_available_tickets += ticket.quantity

        num_ordered_tickets = dao.count_ordered_tickets(
            current_user.id, event_id)

        num_limit_order = min(max_available_tickets,
                              event.purchase_limit) - num_ordered_tickets

        vouchers = dao.get_vouchers_by_event_id(event_id)

        payment_methods = dao.get_payment_methods()

        if request.method == "POST":
            voucher_id = request.form.get("voucher_id")
            try:
                voucher_id = int(voucher_id) if voucher_id else None
            except ValueError:
                flash("Mã giảm giá không hợp lệ.")
                return redirect(url_for('ticket_order', event_id=event_id))
            payment_method_id = request.form.get("payment_method_id")
            try:
                payment_method_id = int(payment_method_id)
            except ValueError:
                flash("Phương thức thanh toán không hợp lệ.")
                return redirect(url_for('ticket_order', event_id=event_id))

            order_items = []
            total_price = 0
            for ticket in event.tickets:
                quantity_str = request.form.get(f"ticket_{ticket.id}")
                try:
                    quantity = int(quantity_str) if quantity_str else 0
                except ValueError:
                    quantity = 0

                if quantity < 0 or quantity > ticket.quantity:
                    flash(
                        f"Số lượng vé cho loại '{ticket.ticket_type.name}' không hợp lệ.")
                    return redirect(url_for('ticket_order', event_id=event_id))

                if quantity > 0:
                    item = OrderItem(
                        event_ticket_id=ticket.id, quantity=quantity)
                    total_price += quantity * ticket.price
                    order_items.append(item)
            # cho thang momo lay gia sau khi app voucher neu co
            if voucher_id:
                voucher = dao.get_voucher(voucher_id)
                if voucher:
                    total_price = total_price * \
                        (1 - voucher.discount_percentage / 100)

            if order_items:
                try:
                    with db.session.begin_nested():
                        order = dao.add_order(
                            user_id=current_user.id,
                            event_id=event_id,
                            order_items=order_items,
                            total_price=total_price,
                            voucher_id=voucher_id,
                            payment_method_id=payment_method_id
                        )

                        dao.update_tickets_quantity(order_items)

                        dao.update_voucher_quantity(voucher_id)

                        db.session.commit()

                    payment_url = utils.handle_payment_method(
                        order, redirect_url=url_for('payment_result', order_id=order.id, _external=True))
                    return redirect(payment_url)

                except Exception as e:
                    print(e)
                    db.session.rollback()
                    flash("Đặt vé thất bại. Vui lòng thử lại.")
                    return redirect(url_for('ticket_order', event_id=event_id))

        return render_template("ticket_order.html", event=event, num_limit_order=num_limit_order, vouchers=vouchers, payment_methods=payment_methods)

    @app.route("/order/<int:order_id>/result")
    @login_required
    @role_required("CUSTOMER")
    def payment_result(order_id):
        order = dao.get_order_by_id(order_id)
        if not order:
            flash("Không tìm thấy đơn hàng.")
            return redirect(url_for("home"))

        if order.user_id != current_user.id:
            flash("Bạn không có quyền xem đơn hàng này.")
            return redirect(url_for("home"))

        return render_template(
            "payment_result.html",
            order=order
        )

    @app.route("/api/face-enroll", methods=["POST"])
    @login_required
    @role_required("CUSTOMER")
    def face_enroll_api():
        try:
            order_id = request.json.get("order_id")
            try:
                order_id = int(order_id)
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": "Đơn hàng không hợp lệ."}), 400

            order = dao.get_order_by_id(order_id)
            if not order:
                return jsonify({"success": False, "message": "Đơn hàng không tồn tại."}), 404

            if order.user_id != current_user.id:
                return jsonify({"success": False, "message": "Bạn không có quyền xác minh khuôn mặt cho đơn hàng này."}), 403

            if order.status != OrderStatus.PAID:
                return jsonify({"success": False, "message": "Đơn hàng không thể xác minh khuôn mặt."}), 400

            if order.authentication_face is not None and order.authentication_face != "":
                return jsonify({"success": False, "message": "Đơn hàng đã được xác minh khuôn mặt."}), 400

            image = request.json.get("image")
            if not image:
                return jsonify({"success": False, "message": "Ảnh không hợp lệ."}), 400

            img_bytes = base64.b64decode(image)
            img = Image.open(BytesIO(img_bytes))

            config = types.GenerateContentConfig(
                system_instruction="Bạn là một chuyên gia nhận diện khuôn mặt. Hãy phân tích bức ảnh được gửi và xác định xem có khuôn mặt nào trong ảnh không, và có nhìn trực diện vào camera không, và có đầy đủ khu vực khuôn mặt không. Nếu có, hãy trả về duy nhất dòng chứa từ True. Nếu không có khuôn mặt nào, hãy trả về duy nhất dòng chứa từ False."
            )

            response = None
            last_error = None
            for model_name in FACE_VERIFICATION_MODELS:
                try:
                    response = gemini_client.models.generate_content(
                        model=model_name,
                        contents=[img],
                        config=config
                    )
                    break
                except Exception as model_err:
                    last_error = model_err
                    continue

            if response is None:
                raise RuntimeError(
                    f"All supported Gemini models failed. Last error: {last_error}")

            result_text = response.text.strip().lower()
            has_face = "true" in result_text

            if has_face:
                msg = "Phát hiện khuôn mặt. Xác minh thành công!"
                try:
                    res = cloudinary.uploader.upload(img_bytes)
                    url = res.get("secure_url")
                    dao.update_order(order_id, authentication_face=url)
                    utils.send_order_email(order)
                    db.session.commit()
                except Exception as e:
                    print(e)
                    return jsonify({"success": False, "message": "Đã xảy ra lỗi khi lưu thông tin xác minh."}), 500

            else:
                msg = "Không phát hiện khuôn mặt trong ảnh. Vui lòng chụp lại."

            return jsonify({
                "success": True,
                "has_face": has_face,
                "message": msg
            })

        except Exception as e:
            print(e)
            return jsonify({"success": False, "message": "Đã xảy ra lỗi khi xử lý ảnh."}), 500


def register_payment_routes(app):

    @app.route("/callback/momo", methods=["POST"])
    def momo_callback():
        ipn = request.get_json()
        order_id_str = ipn.get("orderId", "")
        try:
            order_id = int(order_id_str[14:])
        except (ValueError, IndexError):
            return '', 204

        order = dao.get_order_by_id(order_id)
        if order and order.status == OrderStatus.PENDING:

            access_key = os.getenv("MOMO_ACCESS_KEY")
            secret_key = os.getenv("MOMO_SECRET_KEY")
            partner_code = os.getenv("MOMO_PARTNER_CODE")

            raw_signature = (
                f"accessKey={access_key}"
                f"&amount={int(order.total_price)}"
                f"&extraData={ipn.get('extraData', '')}"
                f"&message={ipn.get('message', '')}"
                f"&orderId={order_id_str}"
                f"&orderInfo={ipn.get('orderInfo', '')}"
                f"&orderType={ipn.get('orderType', '')}"
                f"&partnerCode={partner_code}"
                f"&payType={ipn.get('payType', '')}"
                f"&requestId={ipn.get('requestId', '')}"
                f"&responseTime={ipn.get('responseTime', '')}"
                f"&resultCode={ipn.get('resultCode')}"
                f"&transId={ipn.get('transId', '')}"
            )
            signature = hmac.new(
                secret_key.encode(), raw_signature.encode(), hashlib.sha256
            ).hexdigest()

            if signature == ipn.get("signature"):
                try:
                    with db.session.begin_nested():
                        if ipn.get("resultCode") == 0:
                            dao.update_order(
                                order_id, status=OrderStatus.PAID)
                        else:
                            dao.update_order(
                                order_id, status=OrderStatus.CANCELLED)
                            dao.update_tickets_quantity(
                                order.order_items, is_increase=True)
                            dao.update_voucher_quantity(
                                order.voucher_id, is_increase=True)

                        db.session.commit()
                except Exception as e:
                    print(e)
                    db.session.rollback()
        return '', 204


if __name__ == "__main__":
    register_routes(app)
    register_auth_route(app)
    register_order_routes(app)
    register_payment_routes(app)

    app.run(debug=True)
