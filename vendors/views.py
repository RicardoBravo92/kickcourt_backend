from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .models import Vendor
from .serializers import VendorSerializer, VendorListSerializer
from accounts.permissions import IsAdmin

User = get_user_model()


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['business_name', 'user__username']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'dashboard'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Roles.VENDOR:
            return Vendor.objects.filter(user=user)
        if user.role == User.Roles.ADMIN:
            return Vendor.objects.all()
        return Vendor.objects.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return VendorListSerializer
        return VendorSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def approve(self, request, pk=None):
        vendor = self.get_object()
        vendor.is_approved = True
        vendor.save(update_fields=['is_approved'])
        user = vendor.user
        user.role = User.Roles.VENDOR
        user.save(update_fields=['role'])
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def reject(self, request, pk=None):
        vendor = self.get_object()
        vendor.is_approved = False
        vendor.save(update_fields=['is_approved'])
        return Response({'status': 'rejected'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def dashboard(self, request):
        user = request.user
        vendor = Vendor.objects.filter(user=user).first()
        if not vendor:
            return Response({'error': 'No vendor profile found'}, status=404)
        from bookings.models import Booking
        from django.db.models import Sum, Count
        from django.utils import timezone
        thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)
        bookings = Booking.objects.filter(court__vendor=vendor)
        month_bookings = bookings.filter(date__gte=thirty_days_ago).count()
        total_revenue = bookings.exclude(status=Booking.Status.CANCELLED).aggregate(
            total=Sum('total_price')
        )['total'] or 0
        month_commission = bookings.filter(
            date__gte=thirty_days_ago
        ).exclude(status=Booking.Status.CANCELLED).aggregate(
            total=Sum('commission')
        )['total'] or 0
        return Response({
            'total_courts': vendor.courts.active().count(),
            'total_bookings': bookings.count(),
            'month_bookings': month_bookings,
            'total_revenue': float(total_revenue),
            'month_commission': float(month_commission),
            'pending_approvals': bookings.filter(status=Booking.Status.PENDING).count(),
        })
