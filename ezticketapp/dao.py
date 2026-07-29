import hashlib
from datetime import datetime

from flask import current_app
from flask_login import current_user
from sqlalchemy import case

from ezticketapp import db
from .models import User, CustomerProfile, Event, EventType, TicketType, EventTicket, Role, Gender
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

    if current_user.is_authenticated and current_user.role == Role.CUSTOMER:
        query = query.filter(Event.time >= datetime.now())
        if current_user.customer_profile and current_user.customer_profile.preferred_event_type_id:
            order_case = case(
                (Event.event_type_id == current_user.customer_profile.preferred_event_type_id, 1),
                else_=2
            )
            query = query.order_by(order_case, Event.time.asc())
        else:
            query = query.order_by(Event.time.asc())
    else:
        query = query.order_by(Event.time.asc())


    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_event_types():
    return EventType.query.order_by(EventType.name).all()


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
