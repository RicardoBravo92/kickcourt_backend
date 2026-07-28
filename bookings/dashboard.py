import csv
from datetime import timedelta, date
from django.db.models import Count, Sum, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.permissions import IsAdmin
from .models import Booking
from fields.models import Field


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def dashboard_stats(request):
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)

    total_bookings = Booking.objects.active().count()
    total_revenue = Booking.objects.active().exclude(
        status=Booking.Status.CANCELLED
    ).aggregate(total=Sum('total_price'))['total'] or 0

    bookings_last_30 = Booking.objects.active().filter(
        created_at__date__gte=last_30_days
    ).count()

    bookings_last_7 = Booking.objects.active().filter(
        created_at__date__gte=last_7_days
    ).count()

    bookings_by_status = dict(
        Booking.objects.active().values_list('status').annotate(count=Count('id')).values_list('status', 'count')
    )

    bookings_by_day = {}
    for i in range(30):
        day = today - timedelta(days=i)
        count = Booking.objects.active().filter(date=day).count()
        bookings_by_day[day.isoformat()] = count

    top_fields = list(
        Booking.objects.active()
        .values('field__name')
        .annotate(booking_count=Count('id'), revenue=Sum('total_price'))
        .order_by('-booking_count')[:5]
    )

    top_users = list(
        Booking.objects.active()
        .values('user__username')
        .annotate(booking_count=Count('id'), total_spent=Sum('total_price'))
        .order_by('-booking_count')[:5]
    )

    bookings_by_hour = {}
    for h in range(24):
        count = Booking.objects.active().filter(start_time__hour=h).count()
        bookings_by_hour[f'{h:02d}:00'] = count

    return Response({
        'summary': {
            'total_bookings': total_bookings,
            'total_revenue': float(total_revenue),
            'bookings_last_30_days': bookings_last_30,
            'bookings_last_7_days': bookings_last_7,
            'active_fields': Field.objects.active().count(),
            'total_users': Booking.objects.active().values('user').distinct().count(),
        },
        'bookings_by_status': bookings_by_status,
        'bookings_by_day': bookings_by_day,
        'top_fields': top_fields,
        'top_users': top_users,
        'bookings_by_hour': bookings_by_hour,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def bookings_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookings_export.csv"'

    field_id = request.query_params.get('field_id')
    status_filter = request.query_params.get('status')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    bookings = Booking.objects.active().select_related('field', 'user')

    if field_id:
        bookings = bookings.filter(field_id=field_id)
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if date_from:
        bookings = bookings.filter(date__gte=date_from)
    if date_to:
        bookings = bookings.filter(date__lte=date_to)

    bookings = bookings.order_by('-date', '-start_time')

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'User', 'Field', 'Date', 'Start Time', 'End Time',
        'Status', 'Total Price', 'Created At'
    ])

    def csv_cell(value):
        value = str(value)
        return f"'{value}" if value.startswith(('=', '+', '-', '@')) else value

    for booking in bookings:
        writer.writerow([
            booking.id,
            csv_cell(booking.user.username),
            csv_cell(booking.field.name),
            booking.date,
            booking.start_time,
            booking.end_time,
            booking.status,
            booking.total_price,
            booking.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response
