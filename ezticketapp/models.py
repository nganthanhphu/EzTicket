from enum import Enum as PyEnum
from ezticketapp import db, app
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship

class Role(PyEnum):
    CUSTOMER = "CUSTOMER"
    ORGANIZER = "ORGANIZER"
    ADMIN = "ADMIN"


class OrderStatus(PyEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Gender(PyEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)

class User(BaseModel):
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    avatar = Column(String(255), nullable=True, default="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg")
    role = Column(Enum(Role), nullable=False, default=Role.CUSTOMER)
    password = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)
    customer_profile = relationship("CustomerProfile", backref="user", uselist=False, lazy=True)


class CustomerProfile(BaseModel):
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    gender = Column(Enum(Gender), nullable=True)
    preferred_event_type_id = Column(Integer, ForeignKey('event_type.id'), nullable=True)
    preferred_event_type = relationship("EventType", uselist=False)


class EventType(BaseModel):
    name = Column(String(100), nullable=False)
    events = relationship("Event", backref="event_type", lazy=True)


class Event(BaseModel):
    name = Column(String(100), nullable=False)
    location = Column(String(255), nullable=False)
    image = Column(String(255), nullable=False)
    purchase_limit = Column(Integer, nullable=False)
    cancellation_time_limit_by_hours = Column(Integer, nullable=False)
    time = Column(DateTime, nullable=False)
    event_type_id = Column(Integer, ForeignKey('event_type.id'), nullable=False)
    organizer_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    organizer = relationship("User", uselist=False)
    tickets = relationship("EventTicket", backref="event", lazy=True)


class EventTicket(BaseModel):
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    ticket_type_id = Column(Integer, ForeignKey('ticket_type.id'), nullable=False)
    ticket_type = relationship("TicketType", uselist=False)


class TicketType(BaseModel):
    name = Column(String(100), nullable=False)


class Order(BaseModel):
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship("User", uselist=False, lazy=True)
    authentication_code = Column(String(100), nullable=False)
    authentication_face = Column(String(255), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    total_price = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
    order_items = relationship("OrderItem", backref="order", lazy=True)
    voucher_id = Column(Integer, ForeignKey('voucher.id'), nullable=True)
    voucher = relationship("Voucher", uselist=False)
    payment_method_id = Column(Integer, ForeignKey('payment_method.id'), nullable=False)
    payment_method = relationship("PaymentMethod", uselist=False)


class OrderItem(BaseModel):
    order_id = Column(Integer, ForeignKey('order.id'), nullable=False)
    event_ticket_id = Column(Integer, ForeignKey('event_ticket.id'), nullable=False)
    event_ticket = relationship("EventTicket", uselist=False)
    quantity = Column(Integer, nullable=False)


class Voucher(BaseModel):
    code = Column(String(100), unique=True, nullable=False)
    discount_percentage = Column(Float, nullable=False)
    expiration_date = Column(DateTime, nullable=False)
    quantity = Column(Integer, nullable=False)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)


class PaymentMethod(BaseModel):
    name = Column(String(100), nullable=False)


class EventReport(BaseModel):
    reporter_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    reporter = relationship("User", uselist=False)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
    event = relationship("Event", uselist=False)
    description = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()