from django.urls import path

from .views import BookingMessageListCreateView

urlpatterns = [
    path(
        'bookings/<int:booking_id>/messages/',
        BookingMessageListCreateView.as_view(),
        name='booking-messages',
    ),
]