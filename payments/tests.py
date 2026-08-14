import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from Foodcourt.models import Order

from .models import Payment
from .services import (
    PaystackError,
    handle_webhook_event,
    initialize_payment,
    verify_payment,
)
from .utils import from_kobo, generate_reference, to_kobo

PAYSTACK_TEST_SETTINGS = dict(
    PAYSTACK_PUBLIC_KEY='pk_test_valid',
    PAYSTACK_SECRET_KEY='sk_test_valid',
)

FAKE_INITIALIZE = {
    'status': True,
    'message': 'Authorization URL created',
    'data': {
        'authorization_url': 'https://checkout.paystack.com/faketxn',
        'access_code': 'fakecode',
        'reference': 'FC-TEST-REF',
    },
}


class UtilsTest(TestCase):
    def test_to_kobo_rounds_correctly(self):
        self.assertEqual(to_kobo(Decimal('10.50')), 1050)
        self.assertEqual(to_kobo(Decimal('0.01')), 1)
        self.assertEqual(to_kobo(1), 100)

    def test_from_kobo(self):
        self.assertEqual(from_kobo(100), Decimal('1.00'))

    def test_generate_reference_is_unique(self):
        refs = {generate_reference() for _ in range(100)}
        self.assertEqual(len(refs), 100)


@override_settings(**PAYSTACK_TEST_SETTINGS)
class PaymentFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tester', email='tester@example.com', password='pass'
        )
        self.order = Order.objects.create(
            user=self.user,
            order_id='FC-TEST-001',
            restaurant_name='Test Kitchen',
            delivery_address='1 Main St, Lagos',
            payment_method='card',
            subtotal=Decimal('10.00'),
            delivery_fee=Decimal('2.00'),
            discount=Decimal('0.00'),
            total=Decimal('12.00'),
            status='pending',
        )

    def _build_request(self):
        request = mock.Mock()
        request.build_absolute_uri.return_value = 'http://testserver/payments/callback/'
        return request

    @mock.patch('payments.services.requests.post')
    def test_initialize_creates_payment_and_returns_url(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=200,
            json=lambda: FAKE_INITIALIZE,
        )
        result = initialize_payment(self.order, self._build_request())

        self.assertTrue(result['authorization_url'].startswith('https://checkout.paystack.com/'))
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.amount, Decimal('12.00'))
        self.assertEqual(payment.paystack_reference, 'FC-TEST-REF')

        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['amount'], 1200)
        self.assertEqual(payload['email'], 'tester@example.com')
        self.assertEqual(payload['reference'], payment.transaction_reference)

    @mock.patch('payments.services.requests.post')
    def test_initialize_raises_on_paystack_error(self, mock_post):
        mock_post.return_value = mock.Mock(
            status_code=400,
            json=lambda: {'status': False, 'message': 'Invalid key'},
        )
        with self.assertRaises(PaystackError):
            initialize_payment(self.order, self._build_request())

    def test_webhook_success_fulfils_order(self):
        payment = Payment.objects.create(
            order=self.order,
            customer=self.user,
            amount=Decimal('12.00'),
            currency='NGN',
            transaction_reference=generate_reference(),
            paystack_reference='FC-WEBHOOK-REF',
        )
        payload = {
            'event': 'charge.success',
            'data': {'reference': 'FC-WEBHOOK-REF', 'amount': 1200, 'status': 'success'},
        }
        self.assertTrue(handle_webhook_event(payload))

        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESSFUL)
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(self.order.status, 'confirmed')
        self.assertTrue(self.order.is_paid)

    def test_webhook_is_idempotent(self):
        payment = Payment.objects.create(
            order=self.order,
            customer=self.user,
            amount=Decimal('12.00'),
            currency='NGN',
            transaction_reference=generate_reference(),
            paystack_reference='FC-WEBHOOK-REF2',
        )
        payload = {
            'event': 'charge.success',
            'data': {'reference': 'FC-WEBHOOK-REF2', 'amount': 1200, 'status': 'success'},
        }
        self.assertTrue(handle_webhook_event(payload))
        self.assertTrue(handle_webhook_event(payload))

        self.assertEqual(
            Payment.objects.filter(status=Payment.Status.SUCCESSFUL).count(), 1
        )

    def test_webhook_unknown_reference_ignored(self):
        payload = {
            'event': 'charge.success',
            'data': {'reference': 'UNKNOWN', 'amount': 1200, 'status': 'success'},
        }
        self.assertFalse(handle_webhook_event(payload))

    @mock.patch('payments.services.requests.get')
    def test_verify_marks_failed_when_not_found(self, mock_get):
        payment = Payment.objects.create(
            order=self.order,
            customer=self.user,
            amount=Decimal('12.00'),
            currency='NGN',
            transaction_reference=generate_reference(),
            paystack_reference='FC-NOT-FOUND',
        )
        mock_get.return_value = mock.Mock(status_code=404, json=lambda: {})
        result = verify_payment(payment)
        self.assertEqual(result.status, Payment.Status.FAILED)

    @mock.patch('payments.services.requests.get')
    def test_verify_success(self, mock_get):
        payment = Payment.objects.create(
            order=self.order,
            customer=self.user,
            amount=Decimal('12.00'),
            currency='NGN',
            transaction_reference=generate_reference(),
            paystack_reference='FC-VERIFY-REF',
        )
        mock_get.return_value = mock.Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'data': {'reference': 'FC-VERIFY-REF', 'amount': 1200, 'status': 'success'},
            },
        )
        result = verify_payment(payment)
        self.assertEqual(result.status, Payment.Status.SUCCESSFUL)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.order.order_id, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [self.user.email])


@override_settings(**PAYSTACK_TEST_SETTINGS)
class WebhookViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tester2', email='tester2@example.com', password='pass'
        )
        self.order = Order.objects.create(
            user=self.user,
            order_id='FC-TEST-002',
            restaurant_name='Test Kitchen',
            delivery_address='2 Main St, Lagos',
            payment_method='card',
            subtotal=Decimal('5.00'),
            delivery_fee=Decimal('1.00'),
            discount=Decimal('0.00'),
            total=Decimal('6.00'),
            status='pending',
        )
        self.payment = Payment.objects.create(
            order=self.order,
            customer=self.user,
            amount=Decimal('6.00'),
            currency='NGN',
            transaction_reference=generate_reference(),
            paystack_reference='FC-HOOK-VIEW',
        )

    def test_webhook_rejects_bad_signature(self):
        payload = json.dumps({
            'event': 'charge.success',
            'data': {'reference': 'FC-HOOK-VIEW', 'amount': 600, 'status': 'success'},
        })
        response = self.client.post(
            reverse('payments:payments_webhook'),
            data=payload,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='wrongsignature',
        )
        self.assertEqual(response.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    @mock.patch('payments.webhooks.secret_key')
    def test_webhook_accepts_valid_signature(self, mock_secret):
        mock_secret.return_value = 'sk_test_valid'
        payload = json.dumps({
            'event': 'charge.success',
            'data': {'reference': 'FC-HOOK-VIEW', 'amount': 600, 'status': 'success'},
        })
        import hashlib
        import hmac
        signature = hmac.new(b'sk_test_valid', payload.encode('utf-8'), hashlib.sha512).hexdigest()
        response = self.client.post(
            reverse('payments:payments_webhook'),
            data=payload,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCESSFUL)


@override_settings(**PAYSTACK_TEST_SETTINGS)
class PlaceOrderIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer', email='buyer@example.com', password='pass'
        )

    def _post_order(self, payment_method):
        self.client.login(username='buyer', password='pass')
        return self.client.post(
            reverse('place_order'),
            data=json.dumps({
                'items': [{'name': 'Burger', 'price': 10, 'qty': 1}],
                'delivery_address': '3 Main St, Lagos',
                'payment_method': payment_method,
                'subtotal': 10.0,
                'delivery_fee': 2.0,
                'discount': 0.0,
                'total': 12.0,
                'restaurant_name': 'Test Kitchen',
            }),
            content_type='application/json',
        )

    @mock.patch('payments.services.requests.post')
    def test_card_order_returns_payment_url(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=200, json=lambda: FAKE_INITIALIZE)
        response = self._post_order('card')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['payment_url'].startswith('https://checkout.paystack.com/'))

        order = Order.objects.get(order_id=data['order_id'])
        self.assertEqual(order.status, 'pending')
        self.assertTrue(hasattr(order, 'payment'))

    def test_cash_order_confirms_immediately(self):
        response = self._post_order('cash')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertNotIn('payment_url', data)

        order = Order.objects.get(order_id=data['order_id'])
        self.assertEqual(order.status, 'confirmed')
        self.assertTrue(order.is_accepted)
        self.assertFalse(hasattr(order, 'payment'))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.order_id, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_restaurant_notification_email(self):
        from Foodcourt.models import Restaurant

        restaurant = Restaurant.objects.create(
            name='Email Kitchen', owner=self.user, email='kitchen@example.com'
        )
        order = Order.objects.create(
            user=self.user,
            order_id='FC-REST-001',
            restaurant=restaurant,
            restaurant_name=restaurant.name,
            delivery_address='5 Main St, Lagos',
            payment_method='cash',
            subtotal=Decimal('10.00'),
            delivery_fee=Decimal('2.00'),
            discount=Decimal('0.00'),
            total=Decimal('12.00'),
            status='pending',
        )
        order.items.create(name='Pizza', quantity=2, price=Decimal('5.00'))

        from Foodcourt.notifications import send_order_confirmation_emails

        send_order_confirmation_emails(order)

        self.assertEqual(len(mail.outbox), 2)
        recipients = {m.to[0] for m in mail.outbox}
        self.assertEqual(recipients, {self.user.email, 'kitchen@example.com'})
        restaurant_email = next(m for m in mail.outbox if m.to == ['kitchen@example.com'])
        self.assertIn('New order received', restaurant_email.subject)
        self.assertIn('2x Pizza', restaurant_email.body)
