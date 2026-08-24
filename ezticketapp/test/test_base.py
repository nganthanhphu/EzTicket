import hashlib
from datetime import datetime, timedelta

import pytest
from flask import Flask
from flask_login import LoginManager

from ezticketapp import db
from ezticketapp.models import (
    CustomerProfile,
    Event,
    EventTicket,
    EventType,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Role,
    TicketType,
    User,
    Voucher,
)


def create_test_app():
    app = Flask("ezticketapp")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    app.config["PAGE_SIZE"] = 6
    app.secret_key = "ABCXYZ1234567890"

    app.config["MAIL_SERVER"] = "localhost"
    app.config["MAIL_PORT"] = 25
    app.config["MAIL_USE_TLS"] = False
    app.config["MAIL_USERNAME"] = "test@ezticket.test"
    app.config["MAIL_PASSWORD"] = "test"

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    return app


@pytest.fixture
def test_app():
    app = create_test_app()
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def test_client(test_app):
    return test_app.test_client()


@pytest.fixture
def test_session(test_app):
    yield db.session
    db.session.rollback()
    db.session.remove()


class FakeUser:

    def __init__(self, is_authenticated=True, user_id=None, full_name=None,
                 email=None, role=None, customer_profile=None):
        self.is_authenticated = is_authenticated
        self.id = user_id
        self.full_name = full_name
        self.email = email
        self.role = role
        self.customer_profile = customer_profile


"""
Dữ liệu mẫu bao gồm:
- 1 EventType: "Âm nhạc"
- 2 TicketType: "VIP", "Thường"
- 1 Organizer
- 2 Customer: customer_a, customer_b
- 1 Event: Concert Hà Nội, thuộc EventType "Âm nhạc", do Organizer tạo, còn hạn
- 2 EventTicket: VIP 500.000đ/10 vé, Thường 200.000đ/100 vé
- 2 PaymentMethod: "MoMo", "ZaloPay"
- 1 Voucher: 10%, còn hạn
- 3 Order:
    + order_paid     : customer_a, PAID,      2 vé Thường
    + order_pending  : customer_a, PENDING,   1 vé VIP
    + order_cancelled: customer_b, CANCELLED, 1 vé Thường
"""


@pytest.fixture
def sample_event_type(test_session):
    et = EventType(name="Âm nhạc")
    test_session.add(et)
    test_session.commit()
    return et


@pytest.fixture
def sample_ticket_types(test_session):
    vip = TicketType(name="VIP")
    regular = TicketType(name="Thường")
    test_session.add_all([vip, regular])
    test_session.commit()
    return vip, regular


@pytest.fixture
def sample_organizer(test_session):
    user = User(
        full_name="Nguyen Van A",
        email="organizer@ezticket.com",
        password=hashlib.md5(b"123").hexdigest(),
        role=Role.ORGANIZER,
        active=True,
    )
    test_session.add(user)
    test_session.commit()
    return user


@pytest.fixture
def sample_customers(test_session):
    pw = hashlib.md5(b"123").hexdigest()
    customer_a = User(
        full_name="Tran Thi A",
        email="customer_a@ezticket.com",
        password=pw,
        role=Role.CUSTOMER,
        active=True,
    )
    customer_b = User(
        full_name="Le Van B",
        email="customer_b@ezticket.com",
        password=pw,
        role=Role.CUSTOMER,
        active=True,
    )
    test_session.add_all([customer_a, customer_b])
    test_session.commit()
    return customer_a, customer_b


@pytest.fixture
def sample_event(test_session, sample_event_type, sample_organizer):
    event = Event(
        name="Concert Hà Nội",
        location="Hà Nội",
        image="http://example.com/concert.jpg",
        purchase_limit=5,
        cancellation_time_limit_by_hours=24,
        time=datetime.now() + timedelta(days=30),
        event_type_id=sample_event_type.id,
        organizer_id=sample_organizer.id,
        is_active=True,
    )
    test_session.add(event)
    test_session.commit()
    return event


@pytest.fixture
def sample_event_tickets(test_session, sample_event, sample_ticket_types):
    vip_type, regular_type = sample_ticket_types
    ticket_vip = EventTicket(
        event_id=sample_event.id,
        ticket_type_id=vip_type.id,
        price=500_000.0,
        quantity=10,
    )
    ticket_regular = EventTicket(
        event_id=sample_event.id,
        ticket_type_id=regular_type.id,
        price=200_000.0,
        quantity=100,
    )
    test_session.add_all([ticket_vip, ticket_regular])
    test_session.commit()
    return ticket_vip, ticket_regular


@pytest.fixture
def sample_payment_methods(test_session):
    momo = PaymentMethod(name="MoMo")
    zaloPay = PaymentMethod(name="ZaloPay")
    test_session.add_all([momo, zaloPay])
    test_session.commit()
    return momo, zaloPay


@pytest.fixture
def sample_voucher(test_session, sample_event):
    voucher = Voucher(
        code="DISCOUNT10",
        discount_percentage=10.0,
        expiration_date=datetime.now() + timedelta(days=60),
        quantity=50,
        event_id=sample_event.id,
    )
    test_session.add(voucher)
    test_session.commit()
    return voucher


@pytest.fixture
def sample_orders(test_session, sample_customers, sample_event_tickets, sample_payment_methods):
    customer_a, customer_b = sample_customers
    ticket_vip, ticket_regular = sample_event_tickets
    momo, zaloPay = sample_payment_methods

    order_paid = Order(
        user_id=customer_a.id,
        authentication_code=hashlib.md5(b"auth-paid").hexdigest(),
        total_price=400_000.0,
        date=datetime.now() - timedelta(hours=2),
        payment_method_id=momo.id,
        status=OrderStatus.PAID,
    )
    test_session.add(order_paid)
    test_session.flush()
    test_session.add(OrderItem(
        order_id=order_paid.id,
        event_ticket_id=ticket_regular.id,
        quantity=2,
    ))

    order_pending = Order(
        user_id=customer_a.id,
        authentication_code=hashlib.md5(b"auth-pending").hexdigest(),
        total_price=500_000.0,
        date=datetime.now() - timedelta(minutes=30),
        payment_method_id=momo.id,
        status=OrderStatus.PENDING,
    )
    test_session.add(order_pending)
    test_session.flush()
    test_session.add(OrderItem(
        order_id=order_pending.id,
        event_ticket_id=ticket_vip.id,
        quantity=1,
    ))

    order_cancelled = Order(
        user_id=customer_b.id,
        authentication_code=hashlib.md5(b"auth-cancelled").hexdigest(),
        total_price=200_000.0,
        date=datetime.now() - timedelta(days=1),
        payment_method_id=zaloPay.id,
        status=OrderStatus.CANCELLED,
    )
    test_session.add(order_cancelled)
    test_session.flush()
    test_session.add(OrderItem(
        order_id=order_cancelled.id,
        event_ticket_id=ticket_regular.id,
        quantity=1,
    ))

    test_session.commit()
    return order_paid, order_pending, order_cancelled
