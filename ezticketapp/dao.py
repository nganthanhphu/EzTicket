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


def add_user(name, email, password, avatar=None, role_name="CUSTOMER", gender_name=None, preferred_event_type_id=None):
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
        Order.status == OrderStatus.COMPLETED
    ).scalar()
    return count or 0


def add_order(user_id, event_id, order_items, total_price, voucher_id=None, payment_method_id=None):
    auth_code = hashlib.md5(f"{user_id}{event_id}{datetime.now()}".encode("utf-8")).hexdigest()
    auth_face = 'NOT_SET'

    order = Order(
        user_id=user_id,
        authentication_code=auth_code,
        authentication_face=auth_face,
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