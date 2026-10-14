import asyncio
import os
from datetime import time, timedelta

# simplejwt's token_blacklist inserts an OutstandingToken when a refresh token
# is minted (_jwt below runs synchronously inside the async scenarios). Allow
# that single tiny insert; every other DB access in these tests runs in a
# worker thread via database_sync_to_async / asyncio.to_thread.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from bookings.models import Booking
from config.asgi import application
from courts.models import Court
from realtime.models import Message
from vendors.models import Vendor

from realtime.publishers import publish_availability, publish_booking_event


def _jwt(user):
    return str(RefreshToken.for_user(user).access_token)


class RealtimeBaseTestCase(TransactionTestCase):
    """
    TransactionTestCase is used because the Websocket consumers read the DB
    from worker threads; with the default TestCase (single transaction) they
    would not see the test data.
    """

    async def _run(self, scenario):
        from django.db import connections

        layer = get_channel_layer()
        await layer.flush()
        try:
            await scenario()
        finally:
            # Consumers run the ORM in worker threads; close those connections
            # so the SQLite test db does not stay locked on Windows.
            await asyncio.to_thread(connections.close_all)


class CourtConsumerTestCase(RealtimeBaseTestCase):
    def setUp(self):
        self.court = Court.objects.create(name='Cancha 1', price_per_hour=50.00)

    def test_anonymous_can_connect_and_receives_snapshot(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, f'/ws/courts/{self.court.id}/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            snapshot = await communicator.receive_json_from(timeout=2)
            self.assertEqual(snapshot['type'], 'court.availability')
            self.assertEqual(snapshot['court_id'], self.court.id)
            self.assertTrue(snapshot['slots'])
            await communicator.disconnect()

        asyncio.run(self._run(scenario))

    def test_broadcast_reaches_group_members(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, f'/ws/courts/{self.court.id}/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from(timeout=2)  # snapshot

            layer = get_channel_layer()
            payload = {
                'court_id': self.court.id,
                'court_name': 'Cancha 1',
                'date': '2026-10-12',
                'slots': [{'hour': 14, 'time': '14:00', 'end_time': '15:00', 'status': 'booked'}],
            }
            await layer.group_send(
                f'court_{self.court.id}',
                {'type': 'court.availability', 'data': payload},
            )
            message = await communicator.receive_json_from(timeout=2)
            self.assertEqual(message['type'], 'court.availability')
            self.assertEqual(message['slots'][0]['status'], 'booked')
            await communicator.disconnect()

        asyncio.run(self._run(scenario))

    def test_publish_availability_sends_valid_payload(self):
        future = timezone.now().date() + timedelta(days=1)
        publish_availability(self.court.id, str(future))

    def test_unknown_court_closes_connection(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, '/ws/courts/9999/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)  # room exists; snapshot is just skipped
            await communicator.disconnect()

        asyncio.run(self._run(scenario))


class NotificationsConsumerTestCase(RealtimeBaseTestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username='client', password='pass123')
        self.admin_user = User.objects.create_user(
            username='admin', password='pass123', role='ADMIN'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor', password='pass123', role='VENDOR'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user, business_name='Vendor SA', is_approved=True
        )
        self.court = Court.objects.create(
            name='Cancha 1', price_per_hour=50.00, vendor=self.vendor
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        self.booking = Booking.objects.create(
            user=self.client_user,
            court=self.court,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            total_price=50.00,
        )

    def test_requires_auth(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, '/ws/notifications/')
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        asyncio.run(self._run(scenario))

    def test_client_receives_own_events(self):
        async def scenario():
            token = _jwt(self.client_user)
            communicator = WebsocketCommunicator(
                application, f'/ws/notifications/?token={token}'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            layer = get_channel_layer()
            data = {'event': 'confirmed', 'booking_id': self.booking.id}
            await layer.group_send(f'user_{self.client_user.id}', {'type': 'booking.event', 'data': data})

            message = await communicator.receive_json_from(timeout=2)
            self.assertEqual(message['type'], 'booking.event')
            self.assertEqual(message['event'], 'confirmed')
            await communicator.disconnect()

        asyncio.run(self._run(scenario))

    def test_admin_receives_admins_channel(self):
        async def scenario():
            token = _jwt(self.admin_user)
            communicator = WebsocketCommunicator(
                application, f'/ws/notifications/?token={token}'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            layer = get_channel_layer()
            data = {'event': 'created', 'booking_id': self.booking.id}
            await layer.group_send('admins', {'type': 'booking.event', 'data': data})

            message = await communicator.receive_json_from(timeout=2)
            self.assertEqual(message['event'], 'created')
            await communicator.disconnect()

        asyncio.run(self._run(scenario))

    def test_vendor_receives_vendor_channel(self):
        async def scenario():
            token = _jwt(self.vendor_user)
            communicator = WebsocketCommunicator(
                application, f'/ws/notifications/?token={token}'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            layer = get_channel_layer()
            data = {'event': 'created', 'booking_id': self.booking.id}
            await layer.group_send(
                f'vendor_{self.vendor.user_id}', {'type': 'booking.event', 'data': data}
            )

            message = await communicator.receive_json_from(timeout=2)
            self.assertEqual(message['event'], 'created')
            await communicator.disconnect()

        asyncio.run(self._run(scenario))


class ChatConsumerTestCase(RealtimeBaseTestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username='client', password='pass123')
        self.other_client = User.objects.create_user(username='other', password='pass123')
        self.vendor_user = User.objects.create_user(
            username='vendor', password='pass123', role='VENDOR'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user, business_name='Vendor SA', is_approved=True
        )
        self.court = Court.objects.create(
            name='Cancha 1', price_per_hour=50.00, vendor=self.vendor
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        self.booking = Booking.objects.create(
            user=self.client_user,
            court=self.court,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            total_price=50.00,
        )
        self.bad_token = _jwt(self.other_client)
        self.token = _jwt(self.client_user)

    def test_non_participant_rejected(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                application,
                f'/ws/bookings/{self.booking.id}/chat/?token={self.bad_token}',
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        asyncio.run(self._run(scenario))

    def test_unauthenticated_rejected(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                application, f'/ws/bookings/{self.booking.id}/chat/'
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        asyncio.run(self._run(scenario))

    def test_participant_send_receives_message_and_persists(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                application, f'/ws/bookings/{self.booking.id}/chat/?token={self.token}'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to({'type': 'chat.send', 'text': 'Hola vendor!'})
            message = await communicator.receive_json_from(timeout=2)
            self.assertEqual(message['type'], 'chat.message')
            self.assertEqual(message['text'], 'Hola vendor!')
            self.assertEqual(message['sender_username'], 'client')

            await communicator.disconnect()

        asyncio.run(self._run(scenario))
        self.assertEqual(Message.objects.filter(booking=self.booking).count(), 1)

    def test_vendor_can_participate(self):
        async def scenario():
            token = _jwt(self.vendor_user)
            communicator = WebsocketCommunicator(
                application, f'/ws/bookings/{self.booking.id}/chat/?token={token}'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.disconnect()

        asyncio.run(self._run(scenario))

    def test_empty_message_is_ignored(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                application, f'/ws/bookings/{self.booking.id}/chat/?token={self.token}'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to({'type': 'chat.send', 'text': '   '})
            nothing_received = await communicator.receive_nothing(timeout=0.3)
            self.assertTrue(nothing_received)
            await communicator.disconnect()

        asyncio.run(self._run(scenario))
        self.assertEqual(Message.objects.count(), 0)

    def test_ping_pong(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                application, f'/ws/bookings/{self.booking.id}/chat/?token={self.token}'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to({'type': 'ping'})
            message = await communicator.receive_json_from(timeout=2)
            self.assertEqual(message['type'], 'pong')
            await communicator.disconnect()

        asyncio.run(self._run(scenario))


class ChatRestTestCase(TransactionTestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username='client', password='pass123')
        self.other_client = User.objects.create_user(username='other', password='pass123')
        self.vendor_user = User.objects.create_user(
            username='vendor', password='pass123', role='VENDOR'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user, business_name='Vendor SA', is_approved=True
        )
        self.court = Court.objects.create(
            name='Cancha 1', price_per_hour=50.00, vendor=self.vendor
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        self.booking = Booking.objects.create(
            user=self.client_user,
            court=self.court,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            total_price=50.00,
        )
        self.url = f'/api/bookings/{self.booking.id}/messages/'

    def test_history_and_create(self):
        Message.objects.create(booking=self.booking, sender=self.client_user, text='Hola')
        client = APIClient()
        client.force_authenticate(user=self.client_user)

        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['text'], 'Hola')

        response = client.post(self.url, {'text': 'Respuesta'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['sender_username'], 'client')

        response = client.get(self.url)
        self.assertEqual(response.json()['count'], 2)

    def test_non_participant_forbidden(self):
        client = APIClient()
        client.force_authenticate(user=self.other_client)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_forbidden(self):
        client = APIClient()
        response = client.get(self.url)
        self.assertEqual(response.status_code, 401)


class BookingEventBroadcastTestCase(TransactionTestCase):
    """End-to-end: creating/confirming a booking publishes to the right rooms."""

    def setUp(self):
        self.client_user = User.objects.create_user(username='client', password='pass123')
        self.vendor_user = User.objects.create_user(
            username='vendor', password='pass123', role='VENDOR'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user, business_name='Vendor SA', is_approved=True
        )
        self.court = Court.objects.create(
            name='Cancha 1', price_per_hour=50.00, vendor=self.vendor
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)

    def _create_booking(self):
        from django.db import connections

        booking = Booking.objects.create(
            user=self.client_user,
            court=self.court,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            total_price=50.00,
        )
        connections.close_all()
        return booking

    def _publish(self, func, *args):
        from django.db import connections

        try:
            return func(*args)
        finally:
            connections.close_all()

    def test_create_booking_publishes_availability_and_event(self):
        async def scenario():
            layer = get_channel_layer()
            await layer.flush()

            court_comm = WebsocketCommunicator(application, f'/ws/courts/{self.court.id}/')
            connected, _ = await court_comm.connect()
            self.assertTrue(connected)
            await court_comm.receive_json_from(timeout=2)  # snapshot

            notif_comm = WebsocketCommunicator(
                application, f'/ws/notifications/?token={_jwt(self.client_user)}'
            )
            connected, _ = await notif_comm.connect()
            self.assertTrue(connected)

            booking = await asyncio.to_thread(self._create_booking)
            await asyncio.to_thread(self._publish, publish_availability, booking.court_id, str(booking.date))
            await asyncio.to_thread(self._publish, publish_booking_event, booking, 'created')

            availability = await court_comm.receive_json_from(timeout=2)
            self.assertEqual(availability['type'], 'court.availability')
            slot = next(s for s in availability['slots'] if s['hour'] == 10)
            self.assertEqual(slot['status'], 'booked')

            event = await notif_comm.receive_json_from(timeout=2)
            self.assertEqual(event['type'], 'booking.event')
            self.assertEqual(event['event'], 'created')

            await court_comm.disconnect()
            await notif_comm.disconnect()

        asyncio.run(scenario())