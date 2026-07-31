import datetime
import hashlib
import hmac
import re
import os
import uuid

import requests
from flask import request


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
        return True, None

    allowed_ext = ["jpg", "jpeg", "png", "webp"]
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext not in allowed_ext:
        return False, "Ảnh đại diện không hợp lệ"

    return True, None


def create_momo_payment_link(order, redirect_url):
    partner_code = os.getenv("MOMO_PARTNER_CODE")
    access_key = os.getenv("MOMO_ACCESS_KEY")
    secret_key = os.getenv("MOMO_SECRET_KEY")
    payment_url = os.getenv("MOMO_PAYMENT_URL")
    request_id = str(uuid.uuid4())
    amount = int(order.total_price)
    order_id = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{order.id}"
    order_info = f"Thanh toan don hang ma {order.id}"
    ipn_url = f"{request.host_url}callback/momo"
    request_type = "captureWallet"
    extra_data = ""
    lang = "vi"

    raw_signature = (
        f"accessKey={access_key}&amount={amount}&extraData={extra_data}"
        f"&ipnUrl={ipn_url}&orderId={order_id}&orderInfo={order_info}"
        f"&partnerCode={partner_code}&redirectUrl={redirect_url}"
        f"&requestId={request_id}&requestType={request_type}"
    )
    signature = hmac.new(
        secret_key.encode(), raw_signature.encode(), hashlib.sha256
    ).hexdigest()

    data = {
        "partnerCode": partner_code,
        "requestId": request_id,
        "amount": str(amount),
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": redirect_url,
        "ipnUrl": ipn_url,
        "requestType": request_type,
        "extraData": extra_data,
        "lang": lang,
        "signature": signature,
    }

    response = requests.post(payment_url, json=data)
    result = response.json()

    if result.get("resultCode") != 0:
        raise Exception(
            "Lỗi khi thực hiện thanh toánn bằng MOMo: "
            + result.get("message")
        )

    return result.get("payUrl")


def handle_payment_method(order, redirect_url):
    PAYMENT_METHOD = {
        "MoMo": create_momo_payment_link,
    }

    if order.payment_method.name in PAYMENT_METHOD:
        return PAYMENT_METHOD[order.payment_method.name](order, redirect_url)
    else:
        raise Exception("Phương thức thanh toán không được hỗ trợ")
