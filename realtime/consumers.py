from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from realtime.auth import get_user_from_scope, is_allowed_origin
from realtime.serializers import MessageSerializer


def _load_booking_raw(booking_id):
    from bookings.models import Booking

    return (
        Booking.objects.select_related('court__vendor', 'user')
        .filter(pk=booking_id, deleted_at__isnull=True)
        .first()
    )


def _is_participant_raw(user, booking):
    from realtime.services import is_booking_participant

    return is_booking_participant(user, booking)


def _create_message_raw(user, booking, text):
    from realtime.services import create_chat_message

    return create_chat_message(user, booking, text)


def _list_participant_groups_raw(user):
    groups = [f'user_{user.id}']
    if user.role == 'VENDOR':
        vendor = getattr(user, 'vendor_profile', None)
        if vendor is not None:
            groups.append(f'vendor_{vendor.user_id}')
    elif user.role == 'ADMIN':
        groups.append('admins')
    return groups


def _availability_payload_raw(court_id, date_str):
    from courts.services import resolve_availability_for_date

    return resolve_availability_for_date(court_id, date_str)


class BaseConsumer(AsyncJsonWebsocketConsumer):
    """Handles origin validation, optional JWT auth, ping/pong and room lifecycle."""

    async def connect(self):
        if not is_allowed_origin(self.scope):
            await self.close(code=4403)
            return
        self.user = await database_sync_to_async(get_user_from_scope)(self.scope)
        if not self.require_auth or self.user is None:
            if self.require_auth:
                await self.close(code=4401)
                return
        self.rooms = []
        await self.setup_rooms()
        await self.accept()
        await self.after_accept()

    # Overridable
    require_auth = False

    async def setup_rooms(self):
        pass

    async def after_accept(self):
        pass

    async def teardown_rooms(self):
        for room in self.rooms:
            await self.channel_layer.group_discard(room, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})
            return
        await self.handle_json(content)

    async def handle_json(self, content):
        pass

    async def disconnect(self, code):
        await self.teardown_rooms()


class CourtConsumer(BaseConsumer):
    """Live availability for a single court (public, room ``court_<id>``)."""

    async def setup_rooms(self):
        self.court_id = int(self.scope['url_route']['kwargs']['court_id'])
        self.room = f'court_{self.court_id}'
        await self.channel_layer.group_add(self.room, self.channel_name)
        self.rooms = [self.room]

    async def after_accept(self):
        today = timezone.localdate().isoformat()
        payload = await database_sync_to_async(_availability_payload_raw)(self.court_id, today)
        if payload is not None:
            await self.send_json({'type': 'court.availability', **payload})

    async def court_availability(self, event):
        await self.send_json({'type': 'court.availability', **event['data']})


class NotificationsConsumer(BaseConsumer):
    """Booking events for the authenticated user (rooms ``user_<id>``, ``vendor_<id>``, ``admins``)."""

    require_auth = True

    async def setup_rooms(self):
        self.rooms = await database_sync_to_async(_list_participant_groups_raw)(self.user)
        for room in self.rooms:
            await self.channel_layer.group_add(room, self.channel_name)

    async def booking_event(self, event):
        await self.send_json({'type': 'booking.event', **event['data']})


class ChatConsumer(BaseConsumer):
    """Chat for a booking (room ``booking_<id>``). Only participants can join."""

    require_auth = True

    async def connect(self):
        if not is_allowed_origin(self.scope):
            await self.close(code=4403)
            return
        self.user = await database_sync_to_async(get_user_from_scope)(self.scope)
        if self.user is None:
            await self.close(code=4401)
            return

        self.booking_id = int(self.scope['url_route']['kwargs']['booking_id'])
        self.booking = await database_sync_to_async(_load_booking_raw)(self.booking_id)
        if self.booking is None:
            await self.close(code=4404)
            return
        is_participant = await database_sync_to_async(_is_participant_raw)(self.user, self.booking)
        if not is_participant:
            await self.close(code=4403)
            return

        self.room = f'booking_{self.booking_id}'
        await self.channel_layer.group_add(self.room, self.channel_name)
        self.rooms = [self.room]
        await self.accept()

    async def handle_json(self, content):
        if content.get('type') != 'chat.send':
            return
        text = str(content.get('text', '')).strip()
        if not text:
            return
        message = await database_sync_to_async(_create_message_raw)(self.user, self.booking, text[:4000])
        await self.channel_layer.group_send(
            self.room,
            {'type': 'chat.message', 'data': message},
        )

    async def chat_message(self, event):
        await self.send_json({'type': 'chat.message', **event['data']})