from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/courts/(?P<court_id>\d+)/$', consumers.CourtConsumer.as_asgi()),
    re_path(r'^ws/notifications/$', consumers.NotificationsConsumer.as_asgi()),
    re_path(r'^ws/bookings/(?P<booking_id>\d+)/chat/$', consumers.ChatConsumer.as_asgi()),
]