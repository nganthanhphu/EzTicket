import hashlib
from datetime import datetime, timedelta, date

from flask import current_app
from flask_login import current_user
from sqlalchemy import case, func,extract

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

#doanh thu cua mot su kien 
#cach su ly xuat phat tu => orderItem => EventTicket =>event
def revenue_event(event_id, filter_type=None, date_val=None, week_date=None, month=None, quarter=None, year=None):
    event = get_event_by_id(event_id)
    if event is None:
        return None

    query = (
        OrderItem.query
        .with_entities(
            func.sum(OrderItem.quantity * EventTicket.price)
        )
        .join(
            EventTicket,
            OrderItem.event_ticket_id == EventTicket.id
        )
        .join(
            Order,
            OrderItem.order_id == Order.id
        )
        #do momo bị lỗi để trang thái Pending đỡ
        .filter(
            EventTicket.event_id == event_id,
            Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.PENDING])
        )
    )

    if filter_type == 'date' and date_val:
        try:
            if isinstance(date_val, str):
                d = datetime.strptime(date_val, "%Y-%m-%d").date()
            else:
                d = date_val
            start_dt = datetime.combine(d, datetime.min.time())
            end_dt = datetime.combine(d, datetime.max.time())
            query = query.filter(Order.date >= start_dt, Order.date <= end_dt)
        except Exception:
            pass
    elif filter_type == 'week' and week_date:
        try:
            if isinstance(week_date, str):
                w_d = datetime.strptime(week_date, "%Y-%m-%d").date()
            else:
                w_d = week_date
            start_of_week = w_d - timedelta(days=w_d.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_dt = datetime.combine(start_of_week, datetime.min.time())
            end_dt = datetime.combine(end_of_week, datetime.max.time())
            query = query.filter(Order.date >= start_dt, Order.date <= end_dt)
        except Exception:
            pass
    elif filter_type == 'month':
        if month:
            query = query.filter(extract("month", Order.date) == month)
        if year:
            query = query.filter(extract("year", Order.date) == year)
    elif filter_type == 'quarter':
        if quarter:
            query = query.filter(extract("quarter", Order.date) == quarter)
        if year:
            query = query.filter(extract("year", Order.date) == year)
    elif filter_type == 'year':
        if year:
            query = query.filter(extract("year", Order.date) == year)
    else:
        if month:
            query = query.filter(extract("month", Order.date) == month)
        if quarter:
            query = query.filter(extract("quarter", Order.date) == quarter)
        if year:
            query = query.filter(extract("year", Order.date) == year)

    return query.scalar() or 0


#dành cho admin 

# Lay top 5 su kien co doanh thu cao nhat
def get_top_revenue_events(limit=5, filter_type=None, date_val=None, week_date=None, month=None, quarter=None, year=None):
    events = load_my_events()
    event_list = []
    for e in events:
        rev = revenue_event(
            e.id,
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        ) or 0
        event_list.append({
            'event': e,
            'revenue': float(rev)
        })
    event_list.sort(key=lambda x: x['revenue'], reverse=True)
    return event_list[:limit]




# Lay tat ca su kien trong he thong cho Admin
def get_all_events():
    return Event.query.order_by(Event.time.asc()).all()

# Lay top 5 su kien co doanh thu cao nhat toan he thong cho Admin
def get_admin_top_revenue_events(limit=5, filter_type=None, date_val=None, week_date=None, month=None, quarter=None, year=None):
    events = get_all_events()
    event_list = []
    for e in events:
        rev = revenue_event(
            e.id,
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        ) or 0
        event_list.append({
            'event': e,
            'revenue': float(rev)
        })
    event_list.sort(key=lambda x: x['revenue'], reverse=True)
    return event_list[:limit]


# Lay danh sach cac nam co don hang
def get_revenue_years():
    years = db.session.query(extract('year', Order.date)).distinct().all()
    year_list = [int(y[0]) for y in years if y[0] is not None]
    current_yr = datetime.now().year
    if current_yr not in year_list:
        year_list.append(current_yr)
    year_list.sort(reverse=True)
    return year_list


# Lấy doanh thu của tất cả sự kiện theo bộ lọc cho Line Chart
def get_all_events_revenue(organizer_id=None, filter_type=None, date_val=None, week_date=None, month=None, quarter=None, year=None):
    if organizer_id:
        events = load_my_events()
    else:
        events = get_all_events()

    labels = []
    revenues = []
    for e in events:
        rev = revenue_event(
            e.id,
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        ) or 0
        labels.append(e.name)
        revenues.append(float(rev))

    return labels, revenues


#doanh thu Line Chart  theo kiểu lọc (Năm, Quý, Tháng, Tuần, Ngày)
def get_daily_revenue_stats(organizer_id=None, filter_type=None, date_val=None, week_date=None, month=None, quarter=None, year=None):
    import calendar

    valid_statuses = [OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.PENDING]

    # 1.Thống kê 12 Tháng trong Năm
    if filter_type == 'year' or (year and not month and not quarter and not filter_type):
        target_year = year or datetime.now().year
        query = (
            db.session.query(
                extract("month", Order.date).label('m'),
                func.sum(OrderItem.quantity * EventTicket.price).label('revenue')
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(EventTicket, OrderItem.event_ticket_id == EventTicket.id)
            .join(Event, EventTicket.event_id == Event.id)
            .filter(
                Order.status.in_(valid_statuses),
                extract("year", Order.date) == target_year
            )
        )
        if organizer_id:
            query = query.filter(Event.organizer_id == organizer_id)
        results = query.group_by(extract("month", Order.date)).all()
        month_map = {int(r.m): float(r.revenue or 0) for r in results if r.m is not None}
        
        labels = [f"Tháng {m}" for m in range(1, 13)]
        revenues = [month_map.get(m, 0.0) for m in range(1, 13)]
        return labels, revenues

    # 2. KIỂU LỌC: QUÝ -> Thống kê 3 Tháng trong Quý
    elif filter_type == 'quarter' or (quarter and not month and not filter_type):
        target_quarter = quarter or 1
        target_year = year or datetime.now().year
        start_m = (target_quarter - 1) * 3 + 1
        quarter_months = [start_m, start_m + 1, start_m + 2]
        
        query = (
            db.session.query(
                extract("month", Order.date).label('m'),
                func.sum(OrderItem.quantity * EventTicket.price).label('revenue')
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(EventTicket, OrderItem.event_ticket_id == EventTicket.id)
            .join(Event, EventTicket.event_id == Event.id)
            .filter(
                Order.status.in_(valid_statuses),
                extract("year", Order.date) == target_year,
                extract("month", Order.date).in_(quarter_months)
            )
        )
        if organizer_id:
            query = query.filter(Event.organizer_id == organizer_id)
        results = query.group_by(extract("month", Order.date)).all()
        month_map = {int(r.m): float(r.revenue or 0) for r in results if r.m is not None}
        
        labels = [f"Tháng {m}" for m in quarter_months]
        revenues = [month_map.get(m, 0.0) for m in quarter_months]
        return labels, revenues

    # 3. KIỂU LỌC: TUẦN -> Thống kê 7 Ngày trong Tuần
    elif filter_type == 'week' and week_date:
        try:
            if isinstance(week_date, str):
                w_d = datetime.strptime(week_date, "%Y-%m-%d").date()
            else:
                w_d = week_date
            start_of_week = w_d - timedelta(days=w_d.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            query = (
                db.session.query(
                    func.date(Order.date).label('day'),
                    func.sum(OrderItem.quantity * EventTicket.price).label('revenue')
                )
                .join(OrderItem, OrderItem.order_id == Order.id)
                .join(EventTicket, OrderItem.event_ticket_id == EventTicket.id)
                .join(Event, EventTicket.event_id == Event.id)
                .filter(
                    Order.status.in_(valid_statuses),
                    func.date(Order.date) >= start_of_week,
                    func.date(Order.date) <= end_of_week
                )
            )
            if organizer_id:
                query = query.filter(Event.organizer_id == organizer_id)
            results = query.group_by(func.date(Order.date)).all()
            day_map = {str(r.day): float(r.revenue or 0) for r in results if r.day is not None}

            day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
            labels = []
            revenues = []
            for i in range(7):
                curr_day = start_of_week + timedelta(days=i)
                day_str = curr_day.strftime("%Y-%m-%d")
                labels.append(f"{day_names[i]} ({curr_day.strftime('%d/%m')})")
                revenues.append(day_map.get(day_str, 0.0))

            return labels, revenues
        except Exception:
            pass

    # 4. Thống kê các Ngày trong Tháng
    if filter_type == 'date' and date_val:
        try:
            if isinstance(date_val, str):
                d = datetime.strptime(date_val, "%Y-%m-%d").date()
            else:
                d = date_val
            target_month = d.month
            target_year = d.year
        except Exception:
            target_month = month or datetime.now().month
            target_year = year or datetime.now().year
    else:
        target_month = month or datetime.now().month
        target_year = year or datetime.now().year

    _, num_days = calendar.monthrange(target_year, target_month)

    query = (
        db.session.query(
            extract("day", Order.date).label('d'),
            func.sum(OrderItem.quantity * EventTicket.price).label('revenue')
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(EventTicket, OrderItem.event_ticket_id == EventTicket.id)
        .join(Event, EventTicket.event_id == Event.id)
        .filter(
            Order.status.in_(valid_statuses),
            extract("month", Order.date) == target_month,
            extract("year", Order.date) == target_year
        )
    )
    if organizer_id:
        query = query.filter(Event.organizer_id == organizer_id)
    results = query.group_by(extract("day", Order.date)).all()
    day_map = {int(r.d): float(r.revenue or 0) for r in results if r.d is not None}

    labels = [f"Ngày {d}" for d in range(1, num_days + 1)]
    revenues = [day_map.get(d, 0.0) for d in range(1, num_days + 1)]

    return labels, revenues



