import hashlib
import hmac
import os

import cloudinary
from PIL import Image
from flask import jsonify, render_template, request, redirect, url_for, session, flash
from flask_login import logout_user, login_user, current_user, login_required
from ezticketapp import app, dao, db, utils, gemini_client
from ezticketapp.decorator import anonymous_required, run_validations
from cloudinary.uploader import upload
from ezticketapp.models import OrderItem, User, Gender, OrderStatus
from google.genai import types
import base64
from io import BytesIO

from ezticketapp.utils import send_order_email


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

    @app.route("/test")
    def test():
        send_order_email(dao.get_order_by_id(32))
        return render_template("home.html")

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
        return redirect(url_for('home'))

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('home'))


def register_order_routes(app):

    @app.route("/events/<int:event_id>/order", methods=["GET", "POST"])
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
    def payment_result(order_id):
        order = dao.get_order_by_id(order_id)
        if not order:
            flash("Không tìm thấy đơn hàng.")
            return redirect(url_for("home"))

        return render_template(
            "payment_result.html",
            order=order
        )

    @app.route("/api/face-enroll", methods=["POST"])
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

            response = gemini_client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[img],
                config=config
            )

            result_text = response.text.strip().lower()
            has_face = "true" in result_text

            if has_face:
                msg = "Phát hiện khuôn mặt. Xác minh thành công!"
                try:
                    res = cloudinary.uploader.upload(img_bytes)
                    url = res.get("secure_url")
                    dao.update_order(order_id, authentication_face=url)
                    send_order_email(order)
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
                                order_id, status=OrderStatus.COMPLETED)
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
