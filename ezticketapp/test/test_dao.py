import calendar
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from ezticketapp import dao
from ezticketapp.models import Event, Order, OrderItem, OrderStatus
from ezticketapp.test.test_base import (
    test_app,
    test_session,
    sample_event_type,
    sample_ticket_types,
    sample_organizer,
    sample_customers,
    sample_event,
    sample_event_tickets,
    sample_payment_methods,
    sample_voucher,
    sample_orders,
)


def test_get_payment_methods(test_session, sample_payment_methods):
    result = dao.get_payment_methods()
    names = {pm.name for pm in result}
    assert len(result) == 2
    assert 'MoMo' in names
    assert 'ZaloPay' in names


def test_get_order_by_id_success(test_session, sample_orders):
    order_paid, _, _ = sample_orders
    result = dao.get_order_by_id(order_paid.id)
    assert result is not None
    assert result.id == order_paid.id
    assert result.status == OrderStatus.PAID


def test_get_order_by_id_not_found(test_session):
    result = dao.get_order_by_id(99999)
    assert result is None


def test_update_order_status_success(test_session, sample_orders):
    order_paid, _, _ = sample_orders
    result = dao.update_order(order_paid.id, status=OrderStatus.COMPLETED)
    assert result is not None
    assert result.status == OrderStatus.COMPLETED


def test_update_order_multiple_fields(test_session, sample_orders):
    order_paid, _, _ = sample_orders
    result = dao.update_order(
        order_paid.id,
        status=OrderStatus.COMPLETED,
        authentication_face='img.jpg',
    )
    assert result.status == OrderStatus.COMPLETED
    assert result.authentication_face == 'img.jpg'


def test_update_order_not_found(test_session):
    with pytest.raises(RuntimeError, match='Đơn hàng không tồn tại'):
        dao.update_order(99999, status=OrderStatus.COMPLETED)


def test_update_order_no_changed(test_session, sample_orders):
    order_paid, _, _ = sample_orders
    original_status = order_paid.status
    result = dao.update_order(order_paid.id)
    assert result.status == original_status


def test_add_order_success(test_session, sample_customers, sample_event,
                           sample_event_tickets, sample_payment_methods):
    customer_a, _ = sample_customers
    ticket_vip, _ = sample_event_tickets
    momo, _ = sample_payment_methods

    items = [OrderItem(event_ticket_id=ticket_vip.id, quantity=1)]
    order = dao.add_order(
        user_id=customer_a.id,
        event_id=sample_event.id,
        order_items=items,
        total_price=500_000.0,
        payment_method_id=momo.id,
    )
    test_session.commit()

    assert order is not None
    assert order.user_id == customer_a.id
    assert order.total_price == 500_000.0
    assert order.status == OrderStatus.PENDING
    assert order.authentication_code is not None
    assert len(order.authentication_code) == 32


def test_add_order_with_voucher(test_session, sample_customers, sample_event,
                                sample_event_tickets, sample_payment_methods,
                                sample_voucher):
    customer_a, _ = sample_customers
    _, ticket_regular = sample_event_tickets
    momo, _ = sample_payment_methods

    items = [OrderItem(event_ticket_id=ticket_regular.id, quantity=2)]
    order = dao.add_order(
        user_id=customer_a.id,
        event_id=sample_event.id,
        order_items=items,
        total_price=360_000.0,
        voucher_id=sample_voucher.id,
        payment_method_id=momo.id,
    )
    test_session.commit()

    assert order is not None
    assert order.voucher_id == sample_voucher.id


def test_count_ordered_tickets_paid_order(test_session, sample_customers,
                                          sample_event, sample_orders):
    customer_a, _ = sample_customers
    count = dao.count_ordered_tickets(customer_a.id, sample_event.id)
    assert count == 2


def test_count_ordered_tickets_no_orders(test_session, sample_customers, sample_event):
    customer_a, _ = sample_customers
    count = dao.count_ordered_tickets(customer_a.id, sample_event.id)
    assert count == 0


def test_count_ordered_tickets_event_not_found(test_session, sample_customers, sample_orders):
    customer_a, _ = sample_customers
    count = dao.count_ordered_tickets(customer_a.id, 99999)
    assert count == 0


def test_get_paid_user_by_event_success(test_session, sample_customers,
                                        sample_event, sample_orders):
    customer_a, customer_b = sample_customers
    users = dao.get_paid_user_by_event(sample_event.id)
    user_ids = {u.id for u in users}
    assert customer_a.id in user_ids
    assert customer_b.id not in user_ids


def test_get_paid_user_by_event_event_not_found(test_session, sample_orders):
    users = dao.get_paid_user_by_event(99999)
    assert users == []


def test_revenue_event_event_not_found(test_session):
    result = dao.revenue_event(99999)
    assert result is None


def test_revenue_event_success(test_session, sample_event, sample_orders):
    result = dao.revenue_event(sample_event.id)
    assert result == 900_000.0


def test_revenue_event_filter_by_date(test_session, sample_event, sample_orders):
    today = datetime.now().strftime('%Y-%m-%d')
    result = dao.revenue_event(
        sample_event.id, filter_type='date', date_val=today)
    assert result == 900_000.0


def test_revenue_event_filter_by_week(test_session, sample_event, sample_orders):
    today = datetime.now().strftime('%Y-%m-%d')
    result = dao.revenue_event(
        sample_event.id, filter_type='week', week_date=today)
    assert result == 900_000.0


def test_revenue_event_filter_by_month(test_session, sample_event, sample_orders):
    now = datetime.now()
    result = dao.revenue_event(
        sample_event.id, filter_type='month', month=now.month, year=now.year
    )
    assert result == 900_000.0


def test_revenue_event_filter_by_year(test_session, sample_event, sample_orders):
    result = dao.revenue_event(
        sample_event.id, filter_type='year', year=datetime.now().year
    )
    assert result == 900_000.0


def test_get_revenue_years_success(test_session):
    result = dao.get_revenue_years()
    assert datetime.now().year in result


def test_get_daily_revenue_stats_success(test_session):
    labels, revenues = dao.get_daily_revenue_stats()
    assert isinstance(labels, list)
    assert isinstance(revenues, list)
    assert len(labels) == len(revenues)


def test_get_daily_revenue_stats_filter_year(test_session):
    labels, revenues = dao.get_daily_revenue_stats(
        filter_type='year', year=datetime.now().year
    )
    assert len(labels) == 12
    assert all(label.startswith('Tháng') for label in labels)
    assert all(r >= 0 for r in revenues)


def test_get_daily_revenue_stats_filter_quarter_1(test_session):
    labels, _ = dao.get_daily_revenue_stats(
        filter_type='quarter', quarter=1, year=datetime.now().year
    )
    assert labels == ['Tháng 1', 'Tháng 2', 'Tháng 3']


def test_get_daily_revenue_stats_filter_quarter_2(test_session):
    labels, _ = dao.get_daily_revenue_stats(
        filter_type='quarter', quarter=2, year=datetime.now().year
    )
    assert labels == ['Tháng 4', 'Tháng 5', 'Tháng 6']


def test_get_daily_revenue_stats_filter_week(test_session):
    today = datetime.now().strftime('%Y-%m-%d')
    labels, _ = dao.get_daily_revenue_stats(
        filter_type='week', week_date=today)
    assert len(labels) == 7


def test_get_daily_revenue_stats_filter_date(test_session):
    today = datetime.now().strftime('%Y-%m-%d')
    labels, _ = dao.get_daily_revenue_stats(filter_type='date', date_val=today)
    assert len(labels) == 24
    assert labels[0] == '00:00'
    assert labels[23] == '23:00'


def test_get_daily_revenue_stats_filter_by_organizer_id(test_session, sample_organizer):
    labels, revenues = dao.get_daily_revenue_stats(
        organizer_id=sample_organizer.id,
        filter_type='year',
        year=datetime.now().year,
    )
    assert len(labels) == 12
    assert all(r >= 0 for r in revenues)


def test_get_top_revenue_events_success(test_session):
    event_a, event_b, event_c = MagicMock(
        id=1), MagicMock(id=2), MagicMock(id=3)
    event_a.name, event_b.name, event_c.name = 'Event A', 'Event B', 'Event C'
    revenues_map = {1: 300_000, 2: 900_000, 3: 600_000}

    with patch('ezticketapp.dao.load_my_events', return_value=[event_a, event_b, event_c]), patch('ezticketapp.dao.revenue_event', side_effect=lambda eid, **kw: revenues_map[eid]):
        result = dao.get_top_revenue_events(limit=3)

    assert len(result) == 3
    assert result[0]['revenue'] == 900_000.0
    assert result[1]['revenue'] == 600_000.0
    assert result[2]['revenue'] == 300_000.0


def test_get_top_revenue_events_no_events(test_session):
    with patch('ezticketapp.dao.load_my_events', return_value=[]):
        result = dao.get_top_revenue_events()
    assert result == []

    event = MagicMock(id=1)
    event.name = 'Event A'

    with patch('ezticketapp.dao.load_my_events', return_value=[event]), patch('ezticketapp.dao.revenue_event', return_value=None):
        result = dao.get_top_revenue_events()

    assert result[0]['revenue'] == 0.0


def test_get_admin_top_revenue_events_e(test_session):
    event_a, event_b, event_c = MagicMock(
        id=1), MagicMock(id=2), MagicMock(id=3)
    event_a.name, event_b.name, event_c.name = 'Event A', 'Event B', 'Event C'
    revenues_map = {1: 300_000, 2: 900_000, 3: 600_000}

    with patch('ezticketapp.dao.get_all_events', return_value=[event_a, event_b, event_c]), patch('ezticketapp.dao.revenue_event', side_effect=lambda eid, **kw: revenues_map[eid]):
        result = dao.get_admin_top_revenue_events(limit=3)

    assert len(result) == 3
    assert result[0]['revenue'] == 900_000.0
    assert result[1]['revenue'] == 600_000.0
    assert result[2]['revenue'] == 300_000.0


def test_get_admin_top_revenue_events_no_events(test_session):
    with patch('ezticketapp.dao.get_all_events', return_value=[]):
        result = dao.get_admin_top_revenue_events()
    assert result == []


def test_get_all_events_revenue_success(test_session):
    event_a, event_b = MagicMock(id=1), MagicMock(id=2)
    event_a.name, event_b.name = 'Concert A', 'Festival B'
    revenues_map = {1: 200_000, 2: 400_000}

    with patch('ezticketapp.dao.get_all_events', return_value=[event_a, event_b]), patch('ezticketapp.dao.revenue_event', side_effect=lambda eid, **kw: revenues_map[eid]):
        labels, revenues = dao.get_all_events_revenue(organizer_id=None)

    assert labels == ['Concert A', 'Festival B']
    assert revenues == [200_000.0, 400_000.0]


def test_get_all_events_revenue_success_organizer(test_session):
    event = MagicMock(id=5)
    event.name = 'My Event'

    with patch('ezticketapp.dao.load_my_events', return_value=[event]), patch('ezticketapp.dao.revenue_event', return_value=750_000):
        labels, revenues = dao.get_all_events_revenue(organizer_id=1)

    assert labels == ['My Event']
    assert revenues == [750_000.0]


def test_get_all_events_revenue_no_events(test_session):
    with patch('ezticketapp.dao.get_all_events', return_value=[]):
        labels, revenues = dao.get_all_events_revenue()
    assert labels == []
    assert revenues == []


# Unit test - Quản lý Sự kiện & Vé


def test_get_event_types_dao(test_session, sample_event_type):
    result = dao.get_event_types()
    assert len(result) >= 1
    assert any(et.id == sample_event_type.id for et in result)



def test_get_event_by_id_dao(test_session, sample_event):
    event = dao.get_event_by_id(sample_event.id)
    assert event is not None
    assert event.name == sample_event.name


def test_get_event_by_id_not_found_dao(test_session):
    event = dao.get_event_by_id(99999)
    assert event is None



def test_get_ticket_types_dao(test_session, sample_ticket_types):
    result = dao.get_ticket_types()
    assert len(result) >= 2

#loc lay danh sach ve theo su kien
def test_load_event_tickets_dao(test_session, sample_event, sample_event_tickets):
    tickets = dao.load_event_tickets(sample_event.id)
    assert len(tickets) == 2


def test_get_event_ticket_dao(test_session, sample_event_tickets):
    ticket_vip, _ = sample_event_tickets
    ticket = dao.get_event_ticket(ticket_vip.id)
    assert ticket is not None
    assert ticket.price == ticket_vip.price



def test_get_event_ticket_not_found_dao(test_session):
    ticket = dao.get_event_ticket(99999)
    assert ticket is None

#loc tao su kien
def test_create_event_success_dao(test_session, sample_event_type, sample_organizer):
    success, msg = dao.create_event(
        name="New Concert",
        location="TPHCM",
        image="http://example.com/img.jpg",
        purchase_limit=5,
        cancel_limit=24,
        event_time="2026-12-31T20:00",
        event_type_id=sample_event_type.id,
        organizer_id=sample_organizer.id,
    )
    assert success is True
    assert msg == "Tạo sự kiện thành công"


#loc tao su kien => sai du lieu dau vao
def test_create_event_invalid_inputs_dao(test_session, sample_event_type, sample_organizer):
    success, msg = dao.create_event("", "HCM", "", 5, 24, "2026-12-31T20:00", sample_event_type.id, sample_organizer.id)
    assert success is False

    success, msg = dao.create_event("Event Name", "HCM", "", 0, 24, "2026-12-31T20:00", sample_event_type.id, sample_organizer.id)
    assert success is False

    success, msg = dao.create_event("Event Name", "HCM", "", 5, -1, "2026-12-31T20:00", sample_event_type.id, sample_organizer.id)
    assert success is False

    success, msg = dao.create_event("Event Name", "HCM", "", 5, 24, "invalid-time", sample_event_type.id, sample_organizer.id)
    assert success is False


#loc update su kien => thanh cong
def test_update_event_success_dao(test_session, sample_event):
    form = {
        "name": "Concert Hà Nội Updated",
        "location": "Sân vận động Mỹ Đình",
        "purchase_limit": "10",
        "cancel_limit": "12",
        "time": "2026-11-11T19:00",
    }
    success, msg = dao.update_event(sample_event, form)
    assert success is True
    assert sample_event.name == "Concert Hà Nội Updated"
    assert sample_event.purchase_limit == 10


#loc update su kien => sai du lieu dau vao
def test_update_event_invalid_inputs_dao(test_session, sample_event):
    form = {
        "name": "",
        "location": "Sân vận động Mỹ Đình",
    }
    success, msg = dao.update_event(sample_event, form)
    assert success is False


#loc xoa su kien => ko the xoa vi co don hang
def test_delete_event_with_order_fails_dao(test_session, sample_event, sample_orders):
    success, msg = dao.delete_event(sample_event.id)
    assert success is False
    assert "Không thể xóa" in msg


#loc xoa su kien => ko ton tai
def test_delete_event_not_found_dao(test_session):
    success, msg = dao.delete_event(99999)
    assert success is False
    assert msg == "Không tìm thấy sự kiện"


#loc xoa su kien => thanh cong
def test_delete_event_success_dao(test_session, sample_event_type, sample_organizer):
    event = Event(
        name="Event To Delete",
        location="Location",
        image="",
        purchase_limit=5,
        cancellation_time_limit_by_hours=24,
        time=datetime.now() + timedelta(days=5),
        event_type_id=sample_event_type.id,
        organizer_id=sample_organizer.id,
    )
    test_session.add(event)
    test_session.commit()

    success, msg = dao.delete_event(event.id)
    assert success is True
    assert msg == "Đã xóa"


#loc them loai ve
def test_create_event_ticket_success_dao(test_session, sample_event, sample_ticket_types):
    vip_type, _ = sample_ticket_types
    success, msg = dao.create_event_ticket(sample_event.id, vip_type.id, price=300000.0, quantity=50)
    assert success is True
    assert msg == "Tạo loại vé thành công"


#loc them loai ve => sai du lieu dau vao
def test_create_event_ticket_invalid_quantity_dao(test_session, sample_event, sample_ticket_types):
    vip_type, _ = sample_ticket_types
    success, msg = dao.create_event_ticket(sample_event.id, vip_type.id, price=300000.0, quantity=0)
    assert success is False


#loc update loai ve => thanh cong
def test_update_event_ticket_success_dao(test_session, sample_event_tickets):
    ticket_vip, _ = sample_event_tickets
    success, msg = dao.update_event_ticket(ticket_vip.id, ticket_vip.ticket_type_id, price=600000.0, quantity=20)
    assert success is True
    assert ticket_vip.price == 600000.0
    assert ticket_vip.quantity == 20


#loc update loai ve => ko ton tai
def test_update_event_ticket_not_found_dao(test_session):
    success, msg = dao.update_event_ticket(99999, 1, 100000.0, 10)
    assert success is False


#loc update loai ve => sai du lieu dau vao
def test_update_event_ticket_invalid_quantity_dao(test_session, sample_event_tickets):
    ticket_vip, _ = sample_event_tickets
    success, msg = dao.update_event_ticket(ticket_vip.id, ticket_vip.ticket_type_id, price=600000.0, quantity=0)
    assert success is False


#loc xoa loai ve => thanh cong
def test_delete_event_ticket_success_dao(test_session, sample_event_tickets):
    ticket_vip, _ = sample_event_tickets
    success, msg = dao.delete_event_ticket(ticket_vip.id)
    assert success is True


#loc xoa loai ve => ko ton tai
def test_delete_event_ticket_not_found_dao(test_session):
    success, msg = dao.delete_event_ticket(99999)
    assert success is False



def test_update_tickets_quantity_decrease_dao(test_session, sample_event_tickets):
    ticket_vip, _ = sample_event_tickets
    initial_qty = ticket_vip.quantity
    item = MagicMock(event_ticket_id=ticket_vip.id, quantity=2)

    dao.update_tickets_quantity([item], is_increase=False)
    assert ticket_vip.quantity == initial_qty - 2



def test_update_tickets_quantity_increase_dao(test_session, sample_event_tickets):
    ticket_vip, _ = sample_event_tickets
    initial_qty = ticket_vip.quantity
    item = MagicMock(event_ticket_id=ticket_vip.id, quantity=5)

    dao.update_tickets_quantity([item], is_increase=True)
    assert ticket_vip.quantity == initial_qty + 5


#loc update so luong ve => sai du lieu dau vao
def test_update_tickets_quantity_invalid_raises_dao(test_session, sample_event_tickets):
    ticket_vip, _ = sample_event_tickets
    item = MagicMock(event_ticket_id=ticket_vip.id, quantity=9999)

    with pytest.raises(ValueError, match="Số lượng vé không hợp lệ"):
        dao.update_tickets_quantity([item], is_increase=False)


#loc tinh tong so ve da ban => thanh cong
def test_get_total_sold_ticket_dao(test_session, sample_event_tickets, sample_orders):
    _, ticket_regular = sample_event_tickets
    total_sold = dao.get_total_sold_ticket(ticket_regular.id)
    assert total_sold == 2


#loc goi y gia ve => ko ton tai
def test_suggest_ticket_price_not_found_dao(test_session):
    price = dao.suggest_ticket_price(99999)
    assert price is None


#loc goi y gia ve => thanh cong
def test_suggest_ticket_price_success_dao(test_session, sample_event_tickets, sample_event):
    ticket_vip, _ = sample_event_tickets
    price = dao.suggest_ticket_price(ticket_vip.id)
    assert price == ticket_vip.price


def test_load_events_all_filters_dao(test_app, test_session, sample_event, sample_event_type, sample_event_tickets, sample_organizer):
    with test_app.test_request_context():
        # ko can dang nhap
        anon = MagicMock(is_authenticated=False)
        with patch('ezticketapp.dao.current_user', anon):
            
            p = dao.load_events()
            assert len(p.items) >= 1

            
            p_kw = dao.load_events(keyword=sample_event.name)
            assert len(p_kw.items) >= 1

            
            p_loc = dao.load_events(location=sample_event.location)
            assert len(p_loc.items) >= 1

            
            p_type = dao.load_events(event_type_id=sample_event_type.id)
            assert len(p_type.items) >= 1

            
            p_price = dao.load_events(min_price=100000.0, max_price=600000.0)
            assert len(p_price.items) >= 1

            # Lọc theo khoảng giá không khớp
            p_price_none = dao.load_events(min_price=900000.0)
            assert len(p_price_none.items) == 0

        # 2. Vai trò Admin (xem được tất cả sự kiện)
        admin = MagicMock(is_authenticated=True, role=dao.Role.ADMIN)
        with patch('ezticketapp.dao.current_user', admin):
            p_admin = dao.load_events()
            assert len(p_admin.items) >= 1

        # 3. Vai trò Organizer => (chỉ xem sự kiện của mình)
        org = MagicMock(is_authenticated=True, role=dao.Role.ORGANIZER, id=sample_organizer.id)
        with patch('ezticketapp.dao.current_user', org):
            p_org = dao.load_events()
            assert len(p_org.items) >= 1
            assert all(e.organizer_id == sample_organizer.id for e in p_org.items)

        # 4.    ưu tiên loại sự kiện
        cust_profile = MagicMock(preferred_event_type_id=sample_event_type.id)
        cust = MagicMock(is_authenticated=True, role=dao.Role.CUSTOMER, customer_profile=cust_profile)
        with patch('ezticketapp.dao.current_user', cust):
            p_cust = dao.load_events()
            assert len(p_cust.items) >= 1



def test_load_my_events_unauthenticated_dao(test_session):
    with patch('ezticketapp.dao.current_user', MagicMock(is_authenticated=False)):
        events = dao.load_my_events()
        assert events == []



def test_load_my_events_authenticated_dao(test_session, sample_organizer, sample_event):
    with patch('ezticketapp.dao.current_user', sample_organizer):
        events = dao.load_my_events()
        assert len(events) >= 1
        assert events[0].id == sample_event.id


#loc lay tat ca su kien => thanh cong
def test_get_all_events_dao(test_session, sample_event):
    events = dao.get_all_events()
    assert len(events) >= 1
    assert any(e.id == sample_event.id for e in events)


#loc bat su kien => ko ton tai
def test_toggle_event_active_not_found_dao(test_session):
    success, msg = dao.toggle_event_active(99999)
    assert success is False
    assert msg == "Không tìm thấy sự kiện"


#loc bat su kien => thanh cong
def test_toggle_event_active_success_dao(test_session, sample_event):
    initial_status = sample_event.is_active
    success, msg = dao.toggle_event_active(sample_event.id)
    assert success is True
    assert sample_event.is_active == (not initial_status)


#loc kiem tra su kien da co don hang => co don hang
def test_has_order_dao(test_session, sample_event, sample_orders):
    assert dao.has_order(sample_event.id) is True


#loc kiem tra su kien da co don hang => ko co don hang
def test_has_order_no_orders_dao(test_session, sample_event_type, sample_organizer):
    event = Event(
        name="No Order Event",
        location="Loc",
        image="",
        purchase_limit=5,
        cancellation_time_limit_by_hours=24,
        time=datetime.now() + timedelta(days=10),
        event_type_id=sample_event_type.id,
        organizer_id=sample_organizer.id,
    )
    test_session.add(event)
    test_session.commit()

    assert dao.has_order(event.id) is False

