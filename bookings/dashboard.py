from django.utils import timezone
from django.db.models import Count, Sum, Q, F
from datetime import timedelta
from accounts.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def get_dashboard_stats():
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    six_months_ago = today - timedelta(days=180)

    from bookings.models import Booking
    from courts.models import Court

    total_users = User.objects.count()
    active_users = User.objects.filter(
        Q(bookings__date__gte=thirty_days_ago) | Q(date_joined__gte=thirty_days_ago)
    ).distinct().count()

    total_bookings = Booking.objects.active().count()
    month_bookings = Booking.objects.active().filter(date__gte=thirty_days_ago).count()

    confirmed_bookings = Booking.objects.active().filter(status=Booking.Status.CONFIRMED).count()
    pending_bookings = Booking.objects.active().filter(status=Booking.Status.PENDING).count()
    cancelled_bookings = Booking.objects.active().filter(status=Booking.Status.CANCELLED).count()
    completed_bookings = Booking.objects.active().filter(status=Booking.Status.COMPLETED).count()

    total_revenue = Booking.objects.active().exclude(status=Booking.Status.CANCELLED).aggregate(
        total=Sum('total_price')
    )['total'] or 0
    month_revenue = Booking.objects.active().exclude(status=Booking.Status.CANCELLED).filter(
        date__gte=thirty_days_ago
    ).aggregate(total=Sum('total_price'))['total'] or 0

    total_courts = Court.objects.active().count()
    active_courts = Court.objects.active().count()

    bookings_by_month = []
    for i in range(5, -1, -1):
        month_start = today - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)
        count = Booking.objects.active().filter(
            date__gte=month_start, date__lt=month_end
        ).count()
        bookings_by_month.append({
            'month': month_start.strftime('%b %Y'),
            'count': count,
        })

    top_users = User.objects.filter(
        bookings__date__gte=six_months_ago,
        bookings__deleted_at__isnull=True,
    ).annotate(
        booking_count=Count('bookings', filter=Q(bookings__deleted_at__isnull=True))
    ).order_by('-booking_count')[:5]

    booking_stats = {
        'confirmed': confirmed_bookings,
        'pending': pending_bookings,
        'cancelled': cancelled_bookings,
        'completed': completed_bookings,
    }

    court_stats = {
        'total': total_courts,
        'active': active_courts,
    }

    return {
        'total_users': total_users,
        'active_users': active_users,
        'total_bookings': total_bookings,
        'month_bookings': month_bookings,
        'confirmed_bookings': confirmed_bookings,
        'pending_bookings': pending_bookings,
        'cancelled_bookings': cancelled_bookings,
        'completed_bookings': completed_bookings,
        'total_revenue': float(total_revenue),
        'month_revenue': float(month_revenue),
        'total_courts': total_courts,
        'active_courts': active_courts,
        'bookings_by_month': bookings_by_month,
        'top_users': [
            {'id': u.id, 'username': u.username, 'booking_count': u.booking_count}
            for u in top_users
        ],
        'booking_stats': booking_stats,
        'court_stats': court_stats,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    return Response(get_dashboard_stats())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bookings_export_csv_view(request):
    filters = {
        'start_date': request.query_params.get('start_date'),
        'end_date': request.query_params.get('end_date'),
        'status': request.query_params.get('status'),
        'court': request.query_params.get('court'),
        'user': request.query_params.get('user'),
    }
    filters = {k: v for k, v in filters.items() if v}
    return bookings_export_csv(filters)
    import csv
    from django.http import HttpResponse
    from bookings.models import Booking

    bookings = Booking.objects.active().with_court().with_user()

    if filters:
        if filters.get('start_date'):
            bookings = bookings.filter(date__gte=filters['start_date'])
        if filters.get('end_date'):
            bookings = bookings.filter(date__lte=filters['end_date'])
        if filters.get('status'):
            bookings = bookings.filter(status=filters['status'])
        if filters.get('court'):
            bookings = bookings.filter(court_id=filters['court'])
        if filters.get('user'):
            bookings = bookings.filter(user_id=filters['user'])

    bookings = bookings.select_related('user', 'court')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookings_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'User', 'Court', 'Date', 'Start Time', 'End Time',
        'Status', 'Total Price', 'Commission', 'Created At'
    ])

    for booking in bookings:
        writer.writerow([
            booking.id,
            booking.user.username,
            booking.court.name,
            booking.date,
            booking.start_time,
            booking.end_time,
            booking.status,
            booking.total_price,
            booking.commission,
            booking.created_at,
        ])

    return response
