from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    court_name = serializers.CharField(source='court.name', read_only=True)
    vendor_name = serializers.CharField(source='court.vendor.business_name', read_only=True, default=None)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('id', 'user', 'total_price', 'commission', 'created_at')

    def validate(self, attrs):
        from .services import validate_booking_slots
        court = attrs.get('court')
        date = attrs.get('date')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if court and date and start_time and end_time:
            exclude_pk = self.instance.pk if self.instance else None
            validate_booking_slots(court, date, start_time, end_time, exclude_pk)
        return attrs


class BookingListSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    court_name = serializers.CharField(source='court.name', read_only=True)

    class Meta:
        model = Booking
        fields = ('id', 'user', 'court_name', 'date', 'start_time', 'end_time', 'status', 'total_price', 'commission')
