import hashlib
from datetime import datetime

from flask import current_app
from flask_login import current_user
from sqlalchemy import case, func

from ezticketapp import db
from .models import Order, Order, OrderItem, OrderStatus, PaymentMethod, User, CustomerProfile, Event, EventType, TicketType, EventTicket, Role, Gender, Voucher
from .utils import is_valid_password


def load_events(keyword=None, location=None, event_type_id=None, min_price=None, max_price=None, page=1, per_page=None):
    if per_page is None:
        per_page = current_app.config.get("PAGE_SIZE", 6)

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

    if min_price is not None or max_price is not None:
        query = query.join(Event.tickets)
        if min_price is not None:
            query = query.filter(EventTicket.price >= min_price)
        if max_price is not None:
            query = query.filter(EventTicket.price <= max_price)
        query = query.distinct()

    is_organizer = current_user.is_authenticated and current_user.role == Role.ORGANIZER
    is_customer = current_user.is_authenticated and current_user.role == Role.CUSTOMER

    if is_customer:
        query = query.filter(Event.time >= datetime.now())
        query = query.filter(Event.tickets.any(EventTicket.quantity > 0))

    if is_organizer:
        query = query.filter(Event.organizer_id == current_user.id)

    if is_customer and current_user.customer_profile and current_user.customer_profile.preferred_event_type_id:
        order_case = case(
            (Event.event_type_id ==
             current_user.customer_profile.preferred_event_type_id, 1),
            else_=2
        )
        query = query.order_by(order_case, Event.time.asc())
    else:
        query = query.order_by(Event.time.asc())

    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_event_types():
    return EventType.query.order_by(EventType.name).all()


def get_event_by_id(event_id):
    return Event.query.filter_by(id=event_id).first()


def get_ticket_types():
    return TicketType.query.order_by(TicketType.name).all()


def get_user_by_id(user_id):
    return User.query.filter_by(id=user_id).first()


def get_user_by_email(email):
    return User.query.filter_by(email=email).first()


def is_unique_email(email):
    if get_user_by_email(email):
        return False, "Email đã tồn tại"
    return True, None


def add_user(name, email, password, avatar=None, role_name="CUSTOMER", gender_name=None, preferred_event_type_id=None, active=True):
    valid, err_msg = is_valid_password(password)
    if not valid:
        raise ValueError(err_msg)

    password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()

    role = Role.CUSTOMER
    if role_name == "ORGANIZER":
        role = Role.ORGANIZER

    u = User(
        full_name=name,
        email=email,
        password=password_hash,
        role=role,
        active=active,
    )
    if avatar:
        u.avatar = avatar

    if role == Role.CUSTOMER:
        gender = None
        if gender_name:
            try:
                gender = Gender[gender_name]
            except KeyError:
                pass

        u.customer_profile = CustomerProfile(
            preferred_event_type_id=preferred_event_type_id,
            gender=gender
        )

    db.session.add(u)
    db.session.commit()

    return u


def update_user_profile(user, gender=None, preferred_event_type_id=None):
    if not user.customer_profile:
        user.customer_profile = CustomerProfile(
            gender=gender,
            preferred_event_type_id=preferred_event_type_id,
        )
    else:
        user.customer_profile.gender = gender
        user.customer_profile.preferred_event_type_id = preferred_event_type_id

    db.session.add(user)
    db.session.commit()


def get_payment_methods():
    return PaymentMethod.query.all()


def get_vouchers_by_event_id(event_id, only_available=True):
    query = Voucher.query.filter(Voucher.event_id == event_id)

    if only_available:
        query = query.filter(Voucher.expiration_date >= datetime.now(), Voucher.quantity > 0)

    return query.order_by(Voucher.discount_percentage.desc()).all()


def count_ordered_tickets(user_id, event_id):
    count = db.session.query(func.sum(OrderItem.quantity)).join(OrderItem.order).join(OrderItem.event_ticket).filter(
        Order.user_id == user_id,
        EventTicket.event_id == event_id,
        Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED])
    ).scalar()
    return count or 0


def add_order(user_id, event_id, order_items, total_price, voucher_id=None, payment_method_id=None):
    auth_code = hashlib.md5(f"{user_id}{event_id}{datetime.now()}".encode("utf-8")).hexdigest()

    order = Order(
        user_id=user_id,
        authentication_code=auth_code,
        total_price=total_price,
        date=datetime.now(),
        voucher_id=voucher_id,
        payment_method_id=payment_method_id,
        order_items = order_items
    )
    db.session.add(order)
    return order


def get_order_by_id(order_id):
    return Order.query.get(order_id)

def update_order(order_id, status=None, authentication_face=None):
    order = get_order_by_id(order_id)
    if not order:
        raise RuntimeError("Đơn hàng không tồn tại")

    if status:
        order.status = status
    if authentication_face:
        order.authentication_face = authentication_face

    return order

def update_tickets_quantity(order_items, is_increase=False):
    for item in order_items:
        ticket = EventTicket.query.get(item.event_ticket_id)
        if ticket:
            if is_increase:
                ticket.quantity += item.quantity
            else:
                if ticket.quantity >= item.quantity:
                    ticket.quantity -= item.quantity
                else:
                    raise ValueError("Số lượng vé không hợp lệ!")


def update_voucher_quantity(voucher_id, is_increase=False):
    if not voucher_id:
        return
    voucher = Voucher.query.get(voucher_id)
    if voucher:
        if is_increase:
            voucher.quantity += 1
        else:
            if voucher.quantity > 0:
                voucher.quantity -= 1
            else:
                raise ValueError("Số lượng voucher không hợp lệ!")

def load_my_events():
    if not current_user.is_authenticated:
        return []

    return Event.query.filter(Event.organizer_id == current_user.id).order_by(Event.time.asc()).all()


def create_event(name, location, image, purchase_limit, cancel_limit, event_time, event_type_id, organizer_id):
    name = (name or "").strip()
    location = (location or "").strip()

    if not name or not location:
        return False, "Tên sự kiện và địa điểm không được để trống"

    if purchase_limit < 1:
        return False, "Giới hạn mua phải lớn hơn 0"

    if cancel_limit < 0:
        return False, "Thời gian hủy phải >= 0"

    try:
        event_datetime = datetime.strptime(event_time, "%Y-%m-%dT%H:%M")
    except Exception:
        return False, "Thời gian tổ chức không hợp lệ"

    event = Event(
        name=name,
        location=location,
        image=image or "https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg",
        purchase_limit=int(purchase_limit),
        cancellation_time_limit_by_hours=int(cancel_limit),
        time=event_datetime,
        event_type_id=int(event_type_id),
        organizer_id=int(organizer_id),
    )

    try:
        db.session.add(event)
        db.session.commit()
        return True, "Tạo sự kiện thành công"
    except Exception:
        db.session.rollback()
        return False, "Không thể tạo sự kiện"


def load_event_tickets(event_id):
    return EventTicket.query.filter_by(event_id=event_id).order_by(EventTicket.id.asc()).all()


def get_event_ticket(ticket_id):
    return EventTicket.query.filter_by(id=ticket_id).first()


def create_event_ticket(event_id, ticket_type_id, price, quantity):
    if quantity < 1:
        return False, "Số lượng vé phải lớn hơn 0"

    ticket = EventTicket(
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        price=price,
        quantity=quantity,
    )

    try:
        db.session.add(ticket)
        db.session.commit()
        return True, "Tạo loại vé thành công"
    except Exception:
        db.session.rollback()
        return False, "Không thể tạo loại vé"


def update_event_ticket(ticket_id, ticket_type_id, price, quantity):
    ticket = get_event_ticket(ticket_id)
    if ticket is None:
        return False, "Không tìm thấy vé"

    if quantity < 1:
        return False, "Số lượng vé phải lớn hơn 0"

    ticket.ticket_type_id = ticket_type_id
    ticket.price = price
    ticket.quantity = quantity

    try:
        db.session.commit()
        return True, "Đã cập nhật"
    except Exception:
        db.session.rollback()
        return False, "Không thể cập nhật"


def delete_event_ticket(ticket_id):
    ticket = get_event_ticket(ticket_id)
    if ticket is None:
        return False, "Không tìm thấy vé"

    try:
        db.session.delete(ticket)
        db.session.commit()
        return True, "Đã xóa"
    except Exception:
        db.session.rollback()
        return False, "Không thể xóa"


def load_event_vouchers(event_id):
    return Voucher.query.filter_by(event_id=event_id).order_by(Voucher.expiration_date.asc()).all()


def get_voucher(voucher_id):
    return Voucher.query.filter_by(id=voucher_id).first()


def create_voucher(event_id, code, discount, quantity, expiration):
    voucher = Voucher(
        event_id=event_id,
        code=code,
        discount_percentage=discount,
        quantity=quantity,
        expiration_date=expiration,
    )

    try:
        db.session.add(voucher)
        db.session.commit()
        return True, "Thêm voucher thành công"
    except Exception:
        db.session.rollback()
        return False, "Không thể thêm voucher"


def update_voucher(voucher_id, code, discount, quantity, expiration):
    voucher = get_voucher(voucher_id)
    if voucher is None:
        return False, "Không tìm thấy voucher"

    voucher.code = code
    voucher.discount_percentage = discount
    voucher.quantity = quantity
    voucher.expiration_date = expiration

    try:
        db.session.commit()
        return True, "Đã cập nhật"
    except Exception:
        db.session.rollback()
        return False, "Không thể cập nhật"


def delete_voucher(voucher_id):
    voucher = get_voucher(voucher_id)
    if voucher is None:
        return False, "Không tìm thấy voucher"

    try:
        db.session.delete(voucher)
        db.session.commit()
        return True, "Đã xóa"
    except Exception:
        db.session.rollback()
        return False, "Không thể xóa"


def update_event(event, form, image_url=None):
    event.name = (form.get("name") or "").strip()
    event.location = (form.get("location") or "").strip()

    if image_url:
        event.image = image_url
    elif (form.get("image") or "").strip():
        event.image = (form.get("image") or "").strip()

    event.purchase_limit = int(form.get("purchase_limit", event.purchase_limit))
    event.cancellation_time_limit_by_hours = int(form.get("cancel_limit", event.cancellation_time_limit_by_hours))

    if form.get("time"):
        event.time = datetime.strptime(form.get("time"), "%Y-%m-%dT%H:%M")

    if not event.name or not event.location:
        return False, "Tên sự kiện và địa điểm không được để trống"

    if event.purchase_limit < 1:
        return False, "Giới hạn mua phải lớn hơn 0"

    if event.cancellation_time_limit_by_hours < 0:
        return False, "Thời gian hủy phải >= 0"

    try:
        db.session.commit()
        return True, "Cập nhật sự kiện thành công"
    except Exception:
        db.session.rollback()
        return False, "Không thể cập nhật"


# Lay so ve da ban cua 1 su kien
def get_total_sold_ticket(ticket_id):
    return (
        db.session.query(func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            OrderItem.event_ticket_id == ticket_id,
            Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED])
        )
        .scalar()
        or 0
    )


# Ham goi y gia ve cho nha to chuc
def suggest_ticket_price(ticket_id):
    ticket = get_event_ticket(ticket_id)
    if ticket is None:
        return None

    event = get_event_by_id(ticket.event_id)
    if not event or not event.time:
        return ticket.price

    total_sold = get_total_sold_ticket(ticket_id)
    total_ticket = ticket.quantity + total_sold

    if total_ticket <= 0:
        return ticket.price

    remaining_percent = (ticket.quantity / total_ticket) * 100
    days_left = (event.time - datetime.now()).days

    # Con hon 30% ve va con duoi 7 ngay -> Goi y giam 30% gia ve
    if remaining_percent > 30 and 0 <= days_left <= 7:
        return round(ticket.price * 0.7, -3)
        
    # Con hon 30% ve va con duoi  20 ngay -> Goi y giam 30% gia ve
    if remaining_percent > 30 and 0 <= days_left <= 20:
        return round(ticket.price * 0.85, -3)
    
    return ticket.price

def has_order(event_id):
    return (
        db.session.query(Order.id)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(EventTicket, EventTicket.id == OrderItem.event_ticket_id)
        .filter(
            EventTicket.event_id == event_id,
            Order.status != OrderStatus.CANCELLED
        )
        .first()
        is not None
    )
def delete_event(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        return False, "Không tìm thấy sự kiện"

    if has_order(event_id):
        return False, "Không thể xóa sự kiện đã có đã bán được vé"
    
    try:
        db.session.delete(event)
        db.session.commit()
        return True, "Đã xóa"
    except Exception:
        db.session.rollback()
        return False, "Không thể xóa"