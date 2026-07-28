import hashlib
import re

from flask_login import current_user
from sqlalchemy import or_

from . import db
from .models import (
    User,
    Event,
    EventType,
    TicketType,
    EventTicket,
    Order,
    OrderItem,
    OrderStatus,
    Role
)
from sqlalchemy.exc import SQLAlchemyError


#tim kiem su kien
def load_events(keyword=None, location=None, event_type_id=None, ticket_type_id=None, page=1, per_page=6):
    query = db.session.query(Event).join(Event.event_type, isouter=True)

    if keyword:
        query = query.filter(
            Event.name.ilike(f"%{keyword}%") |
            Event.location.ilike(f"%{keyword}%")
        )

    if location:
        query = query.filter(Event.location.ilike(f"%{location}%"))

    if event_type_id:
        query = query.filter(Event.event_type_id == event_type_id)

    if ticket_type_id:
        query = query.join(Event.tickets).filter(EventTicket.ticket_type_id == ticket_type_id).distinct()

    return query.order_by(Event.time.desc()).paginate(page=page, per_page=per_page, error_out=False)

#lay the loai sk da tim kiem
def get_event_types():
    return EventType.query.order_by(EventType.name).all()

#lay the loai ve da tim kiem
def get_ticket_types():
    return TicketType.query.order_by(TicketType.name).all()


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



#rang buoc anh dai dien
def is_valid_avatar(file):
    if not file or file.filename == "":
        return True, None  

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
def load_user(user_id):
    return User.query.get(int(user_id))


def get_event_by_id(event_id):
    return Event.query.filter_by(id=event_id).first()

def get_event_ticket(ticket_id):
    return EventTicket.query.filter_by(id=ticket_id).first()

def get_order(order_id):
    return Order.query.filter_by(id=order_id).first()

def get_order_items(order_id):
    return OrderItem.query.filter_by(order_id=order_id).all()

def get_order_detail(order_id):
    return Order.query.filter_by(id=order_id).first()

#Lay danh sach tat ca ve
def load_orders(page=1,
                keyword=None,
                status=None,
                per_page=10):

    query = Order.query

    if keyword:
        query = query.join(User).filter(
            or_(
                User.full_name.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%"),
                Order.authentication_code.ilike(f"%{keyword}%")
            )
        )

    if status:
        query = query.filter(Order.status == status)

    query = query.order_by(Order.date.desc())

    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

#danh sach cac order dang cho duyet
def load_pending_orders(page=1,
                        keyword=None,
                        per_page=10):

    query = Order.query.filter(
        Order.status == OrderStatus.PENDING
    )

    if keyword:
        query = query.join(User).filter(
            or_(
                User.full_name.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%")
            )
        )

    query = query.order_by(Order.date.desc())

    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

#check organizer co quyen xem don khong
def is_owner_order(order):

    if current_user.role != Role.ORGANIZER:
        return False

    for item in order.order_items:
        if item.event_ticket.event.organizer_id == current_user.id:
            return True

    return False

#duyet ve
def approve_order(order_id):

    order = get_order(order_id)

    if order is None:
        return False, "Không tìm thấy đơn hàng."

    if order.status != OrderStatus.PENDING:
        return False, "Đơn hàng đã được xử lý."

    order.status = OrderStatus.COMPLETED

    db.session.commit()

    return True, "Duyệt vé thành công."

#tu choi ve
def cancel_order(order_id):

    order = get_order(order_id)

    if order is None:
        return False, "Không tìm thấy đơn hàng."

    if order.status != OrderStatus.PENDING:
        return False, "Đơn hàng đã được xử lý."

    order.status = OrderStatus.CANCELLED

    db.session.commit()

    return True, "Đã hủy vé."

def count_orders():
    return Order.query.count()

def count_pending_orders():

    return Order.query.filter(
        Order.status == OrderStatus.PENDING
    ).count()

def count_completed_orders():

    return Order.query.filter(
        Order.status == OrderStatus.COMPLETED
    ).count()

def count_cancelled_orders():

    return Order.query.filter(
        Order.status == OrderStatus.CANCELLED
    ).count()

def ticket_statistics():

    return {
        "total": count_orders(),
        "pending": count_pending_orders(),
        "completed": count_completed_orders(),
        "cancelled": count_cancelled_orders()
    }

def load_my_events():

    return Event.query.filter(
        Event.organizer_id == current_user.id
    ).order_by(Event.time.desc()).all()

def load_orders_by_event(event_id):

    return (
        Order.query
        .join(OrderItem)
        .join(EventTicket)
        .filter(EventTicket.event_id == event_id)
        .order_by(Order.date.desc())
        .all()
    )

def get_order_by_authentication_code(code):

    return Order.query.filter(
        Order.authentication_code == code
    ).first()

def is_pending(order_id):

    order = get_order(order_id)

    if order is None:
        return False

    return order.status == OrderStatus.PENDING

def load_event_tickets(keyword=None, event_id=None, page=1, per_page=10):
    query = (
        EventTicket.query
        .join(Event)
        .join(TicketType)
    )

    if keyword:
        query = query.filter(
            Event.name.ilike(f"%{keyword}%")
        )

    if event_id:
        query = query.filter(
            EventTicket.event_id == event_id
        )

    return query.order_by(
        Event.time.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

def get_event_ticket_by_id(ticket_id):
    return EventTicket.query.get(ticket_id)

def load_events_for_select():
    return Event.query.order_by(
        Event.name
    ).all()

def load_ticket_types():
    return TicketType.query.order_by(
        TicketType.name
    ).all()

def validate_ticket(price, quantity):

    if price <= 0:
        return False, "Giá vé phải lớn hơn 0."

    if quantity <= 0:
        return False, "Số lượng phải lớn hơn 0."

    return True, None

def check_duplicate_ticket(event_id, ticket_type_id, ignore_id=None):
    query = EventTicket.query.filter(
        EventTicket.event_id == event_id,
        EventTicket.ticket_type_id == ticket_type_id
    )

    if ignore_id:
        query = query.filter(
            EventTicket.id != ignore_id
        )

    return query.first() is not None

def create_event_ticket(event_id, ticket_type_id, price, quantity):
    valid, msg = validate_ticket(price, quantity)

    if not valid:
        return False, msg

    if check_duplicate_ticket(event_id, ticket_type_id):
        return False, "Loại vé này đã tồn tại."

    ticket = EventTicket(event_id=event_id, ticket_type_id=ticket_type_id, price=float(price), quantity=int(quantity))

    try:
        db.session.add(ticket)
        db.session.commit()

        return True, "Tạo vé thành công."

    except SQLAlchemyError:

        db.session.rollback()

        return False, "Không thể tạo vé."

def update_event_ticket( ticket_id, event_id, ticket_type_id, price, quantity ):
    ticket = get_event_ticket_by_id(ticket_id)

    if ticket is None:
        return False, "Không tìm thấy vé."

    valid, msg = validate_ticket(price, quantity)

    if not valid:
        return False, msg

    if check_duplicate_ticket( event_id, ticket_type_id, ticket.id ):
        return False, "Loại vé đã tồn tại."

    ticket.event_id = event_id
    ticket.ticket_type_id = ticket_type_id
    ticket.price = float(price)
    ticket.quantity = int(quantity)

    try:
        db.session.commit()

        return True, "Cập nhật thành công."

    except SQLAlchemyError:

        db.session.rollback()

        return False, "Không thể cập nhật."

def is_owner_event_ticket(ticket_id):

    ticket = get_event_ticket_by_id(ticket_id)

    if ticket is None:
        return False

    if not current_user.is_authenticated:
        return False

    if current_user.role != Role.ORGANIZER:
        return False

    return ticket.event.organizer_id == current_user.id