from datetime import datetime
import hashlib
from .models import User, CustomerProfile, Event, EventType, TicketType, EventTicket, Role, Gender
from .utils import is_not_blank, is_valid_length, is_valid_name, is_valid_email, is_valid_password, is_valid_confirm, is_valid_avatar
from flask_login import current_user
from ezticketapp import db


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
        query = query.join(Event.tickets).filter(
            EventTicket.ticket_type_id == ticket_type_id).distinct()

    return query.order_by(Event.time.desc()).paginate(page=page, per_page=per_page, error_out=False)


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


def add_user(name, email, password, avatar, role_name="CUSTOMER", gender_name=None, preferred_event_type_id=None):
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
        avatar=avatar,
        role=role,
    )

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
