import io
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from flask import app
import pytest

from ezticketapp import utils
from ezticketapp.models import Order, OrderItem, OrderStatus
from ezticketapp.test.test_base import (
    create_test_app,
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


@pytest.mark.parametrize('order_index, expected', [
    (0, True),
    (1, False),
    (2, False),
])
def test_can_cancel_order_by_status(order_index, expected, test_session, sample_orders):
    order = sample_orders[order_index]
    assert utils.can_cancel_order(order) is expected


def test_can_cancel_order_event_already_started(test_session, sample_orders, sample_event):
    order_paid, _, _ = sample_orders
    sample_event.time = datetime.now() - timedelta(hours=1)
    test_session.commit()
    assert utils.can_cancel_order(order_paid) is False


def test_can_cancel_order_past_cancellation_deadline(test_session, sample_customers,
                                                     sample_event, sample_event_tickets,
                                                     sample_payment_methods):
    customer_a, _ = sample_customers
    _, ticket_regular = sample_event_tickets
    momo, _ = sample_payment_methods

    old_order = Order(
        user_id=customer_a.id,
        authentication_code='4456456456456',
        total_price=200_000.0,
        date=datetime.now() - timedelta(hours=30),
        payment_method_id=momo.id,
        status=OrderStatus.PAID,
    )
    test_session.add(old_order)
    test_session.flush()
    test_session.add(OrderItem(order_id=old_order.id,
                     event_ticket_id=ticket_regular.id, quantity=1))
    test_session.commit()

    assert utils.can_cancel_order(old_order) is False


def test_generate_auth_qr_img_success(test_session, sample_orders):
    order_paid, _, _ = sample_orders
    result = utils.generate_auth_qr_img(order_paid)
    assert isinstance(result, io.BytesIO)


def _momo_env():
    return {
        'MOMO_PARTNER_CODE': 'ABCXYZ',
        'MOMO_ACCESS_KEY': 'NAHDKS',
        'MOMO_SECRET_KEY': 'EFSDASDS',
        'MOMO_PAYMENT_URL': 'https://test.momo.vn/pay',
    }


def test_create_momo_payment_link_success(test_app, test_session, sample_orders):
    order_paid, _, _ = sample_orders
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'resultCode': 0, 'payUrl': 'https://momo.vn/pay/abc'}

    with test_app.test_request_context('/'), patch.dict('os.environ', _momo_env()), patch('requests.post', return_value=mock_response):
        result = utils.create_momo_payment_link(
            order_paid, 'https://myapp.com/return')

    assert result == 'https://momo.vn/pay/abc'


def test_create_momo_payment_link_failed(test_app, test_session, sample_orders):
    order_paid, _, _ = sample_orders
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'resultCode': -1, 'message': 'Test error from MOMO'}

    with test_app.test_request_context('/'), patch.dict('os.environ', _momo_env()), patch('requests.post', return_value=mock_response):
        with pytest.raises(Exception, match='MOMo'):
            utils.create_momo_payment_link(
                order_paid, 'https://myapp.com/return')


def test_handle_payment_method_success(test_app, test_session, sample_orders):
    order_paid, _, _ = sample_orders

    with test_app.test_request_context('/'), patch('ezticketapp.utils.create_momo_payment_link',
                                                   return_value='https://pay.url') as mock_momo:
        result = utils.handle_payment_method(order_paid, 'https://return.url')

    mock_momo.assert_called_once_with(order_paid, 'https://return.url')
    assert result == 'https://pay.url'


@pytest.mark.parametrize('payment_name', ['ZaloPay', 'PayPal', 'ABCXYZ'])
def test_handle_payment_method_not_supported(payment_name, test_session, sample_orders):
    order_paid, _, _ = sample_orders
    order_paid.payment_method.name = payment_name

    with pytest.raises(Exception, match='không được hỗ trợ'):
        utils.handle_payment_method(order_paid, 'https://return.url')


def test_send_order_email_success(test_app, test_session, sample_orders, sample_customers):
    order_paid, _, _ = sample_orders
    mock_mail = MagicMock()
    mock_msg = MagicMock()

    with patch('ezticketapp.utils.generate_auth_qr_img', return_value=io.BytesIO(b'png')), patch('ezticketapp.mail', mock_mail), patch('ezticketapp.utils.Message', return_value=mock_msg), patch.dict('os.environ', {'MAIL_USERNAME': 'no-reply@ezticket.com'}):
        utils.send_order_email(order_paid)

    mock_mail.send.assert_called_once_with(mock_msg)


@pytest.mark.parametrize('firebase_side_effect, expected', [
    (None, True),
    (Exception('Firebase error'), False),
])
def test_send_inapp_notification(firebase_side_effect, expected, test_session, sample_customers):
    customer_a, _ = sample_customers

    if firebase_side_effect:
        with patch('firebase_admin.db.reference', side_effect=firebase_side_effect):
            result = utils.send_inapp_notification(
                user_ids=[customer_a.id], title='Thông báo', message='Nội dung'
            )
    else:
        with patch('firebase_admin.db.reference'):
            result = utils.send_inapp_notification(
                user_ids=[customer_a.id], title='Thông báo', message='Nội dung'
            )

    assert result is expected


def test_get_firebase_custom_token_success(test_session, sample_customers):
    customer_a, _ = sample_customers
    fake_token = b'eyJhbGciOiJSUzI1NiJ9.fake.token'

    with patch('firebase_admin.auth.create_custom_token', return_value=fake_token) as mock_auth:
        result = utils.get_firebase_custom_token(user_id=customer_a.id)

    assert isinstance(result, str)
    assert result == 'eyJhbGciOiJSUzI1NiJ9.fake.token'
    mock_auth.assert_called_once_with(str(customer_a.id))


def test_handle_event_info_change_notification_success(test_session, sample_event,
                                                       sample_customers, sample_orders):
    customer_a, _ = sample_customers

    with patch('ezticketapp.utils.send_inapp_notification', return_value=True) as mock_noti:
        utils.handle_event_info_change_notification(sample_event)

    mock_noti.assert_called_once()
    user_ids, title, message = mock_noti.call_args[0]
    assert customer_a.id in user_ids
    assert sample_event.name in message
