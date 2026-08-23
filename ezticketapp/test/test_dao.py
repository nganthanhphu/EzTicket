import calendar
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from ezticketapp import dao
from ezticketapp.models import Gender, Order, OrderItem, OrderStatus, Role, User, Voucher
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


def test_create_account_customer_hashes_password_and_creates_profile(test_session):
    user = dao.create_account(
        '  Nguyen Thi C  ', 'new@ezticket.com', 'Strong1!',
    )

    assert user.full_name == 'Nguyen Thi C'
    assert user.password == ''.join(__import__('hashlib').md5(b'Strong1!').hexdigest())
    assert user.role == Role.CUSTOMER
    assert user.customer_profile is not None


def test_create_account_organizer_and_inactive_status(test_session):
    user = dao.create_account(
        'Organizer B', 'organizer_b@ezticket.com', 'Strong1!',
        role_name='ORGANIZER', status='inactive', avatar='avatar.png',
    )

    assert user.role == Role.ORGANIZER
    assert user.active is False
    assert user.avatar == 'avatar.png'
    assert user.customer_profile is None


@pytest.mark.parametrize('kwargs, message', [
    ({'full_name': ' ', 'email': 'valid@ezticket.com'}, 'Tên người dùng không được để trống'),
    ({'full_name': 'Valid Name', 'email': ''}, 'Email không được để trống'),
    ({'full_name': 'Valid Name', 'email': 'customer_a@ezticket.com'}, 'Email đã tồn tại'),
    ({'full_name': 'Valid Name', 'email': 'valid@ezticket.com', 'password': 'weak'}, 'Mật khẩu phải ít nhất 8 ký tự'),
])
def test_create_account_rejects_invalid_input(test_session, sample_customers, kwargs, message):
    values = {'password': 'Strong1!', **kwargs}
    with pytest.raises(ValueError, match=message):
        dao.create_account(**values)


def test_update_account_updates_fields_hash_and_profile(test_session, sample_customers):
    customer, _ = sample_customers
    result = dao.update_account(
        customer.id, full_name='  Updated Customer ', email='updated@ezticket.com',
        role_name='CUSTOMER', status='inactive', password='NewStrong1!',
    )

    assert result.full_name == 'Updated Customer'
    assert result.email == 'updated@ezticket.com'
    assert result.password == __import__('hashlib').md5(b'NewStrong1!').hexdigest()
    assert result.active is False
    assert result.customer_profile is not None


def test_update_account_rejects_missing_user_and_duplicate_email(test_session, sample_customers):
    customer, other = sample_customers
    with pytest.raises(ValueError, match='Tài khoản không tồn tại'):
        dao.update_account(99999, full_name='Nobody')
    with pytest.raises(ValueError, match='Email đã tồn tại'):
        dao.update_account(customer.id, email=other.email)


def test_add_user_creates_customer_with_profile_and_gender(test_session, sample_event_type):
    user = dao.add_user(
        'Customer C', 'customer_c@ezticket.com', 'Strong1!',
        gender_name='FEMALE', preferred_event_type_id=sample_event_type.id,
    )

    assert user.password == __import__('hashlib').md5(b'Strong1!').hexdigest()
    assert user.role == Role.CUSTOMER
    assert user.customer_profile.gender == Gender.FEMALE
    assert user.customer_profile.preferred_event_type_id == sample_event_type.id


def test_add_user_creates_organizer_without_customer_profile(test_session):
    user = dao.add_user(
        'Organizer C', 'organizer_c@ezticket.com', 'Strong1!',
        role_name='ORGANIZER', active=False,
    )
    assert user.role == Role.ORGANIZER
    assert user.active is False
    assert user.customer_profile is None


def test_get_all_users_filters_keyword_role_and_status(test_session, sample_organizer, sample_customers):
    active_customers = dao.get_all_users(keyword='Tran', role='customer', status='active')
    assert [user.id for user in active_customers] == [sample_customers[0].id]

    organizers = dao.get_all_users(role='ORGANIZER')
    assert organizers == [sample_organizer]
    assert dao.get_all_users(role='unknown')


def test_get_user_lookups_and_unique_email(test_session, sample_customers):
    customer, _ = sample_customers
    assert dao.get_user_by_id(customer.id) == customer
    assert dao.get_user_by_id(99999) is None
    assert dao.get_user_by_email(customer.email) == customer
    assert dao.get_user_by_email('missing@ezticket.com') is None
    assert dao.is_unique_email('new@ezticket.com') == (True, None)
    assert dao.is_unique_email(customer.email) == (False, 'Email đã tồn tại')


def test_toggle_user_status_and_delete_account(test_session, sample_customers):
    customer, _ = sample_customers
    original_status = customer.active
    assert dao.toggle_user_status(customer.id).active is (not original_status)
    assert dao.delete_account(customer.id) is True
    assert dao.get_user_by_id(customer.id) is None
    with pytest.raises(ValueError, match='Tài khoản không tồn tại'):
        dao.delete_account(99999)


def test_update_user_profile_creates_and_updates_profile(test_session, sample_customers, sample_event_type):
    customer, _ = sample_customers
    dao.update_user_profile(customer, Gender.MALE, sample_event_type.id)
    assert customer.customer_profile.gender == Gender.MALE
    assert customer.customer_profile.preferred_event_type_id == sample_event_type.id

    dao.update_user_profile(customer, Gender.OTHER, None)
    assert customer.customer_profile.gender == Gender.OTHER
    assert customer.customer_profile.preferred_event_type_id is None


def test_update_voucher_quantity_decreases_increases_and_handles_missing(test_session, sample_voucher):
    dao.update_voucher_quantity(sample_voucher.id)
    assert sample_voucher.quantity == 49
    dao.update_voucher_quantity(sample_voucher.id, is_increase=True)
    assert sample_voucher.quantity == 50
    dao.update_voucher_quantity(None)

    sample_voucher.quantity = 0
    with pytest.raises(ValueError, match='Số lượng voucher không hợp lệ'):
        dao.update_voucher_quantity(sample_voucher.id)


def test_create_update_load_get_and_delete_voucher(test_session, sample_event, sample_voucher):
    expiration = datetime.now() + timedelta(days=10)
    success, message = dao.create_voucher(
        sample_event.id, 'DISCOUNT20', 20, 10, expiration,
    )
    assert (success, message) == (True, 'Thêm voucher thành công')
    created = dao.get_vouchers_by_event_id(sample_event.id)[0]
    assert created.code == 'DISCOUNT20'
    assert dao.get_voucher(created.id) == created
    assert dao.load_event_vouchers(sample_event.id) == [created, sample_voucher]

    success, message = dao.update_voucher(
        created.id, 'UPDATED20', 25, 5, expiration + timedelta(days=1),
    )
    assert (success, message) == (True, 'Đã cập nhật')
    assert dao.get_voucher(created.id).code == 'UPDATED20'

    assert dao.delete_voucher(created.id) == (True, 'Đã xóa')
    assert dao.get_voucher(created.id) is None


def test_voucher_queries_filter_available_and_handle_missing(test_session, sample_event, sample_voucher):
    expired = Voucher(
        event_id=sample_event.id, code='EXPIRED', discount_percentage=30,
        quantity=10, expiration_date=datetime.now() - timedelta(days=1),
    )
    empty = Voucher(
        event_id=sample_event.id, code='EMPTY', discount_percentage=40,
        quantity=0, expiration_date=datetime.now() + timedelta(days=1),
    )
    test_session.add_all([expired, empty])
    test_session.commit()

    available = dao.get_vouchers_by_event_id(sample_event.id)
    assert available == [sample_voucher]
    assert {voucher.code for voucher in dao.get_vouchers_by_event_id(sample_event.id, only_available=False)} == {
        'DISCOUNT10', 'EXPIRED', 'EMPTY'
    }
    assert dao.load_event_vouchers(99999) == []
    assert dao.get_voucher(99999) is None
    assert dao.update_voucher(99999, 'X', 1, 1, datetime.now()) == (False, 'Không tìm thấy voucher')
    assert dao.delete_voucher(99999) == (False, 'Không tìm thấy voucher')
