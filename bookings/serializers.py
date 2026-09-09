from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    court_name = serializers.CharField(source='court.name', read_only=True)
    vendor_name = serializers.CharField(source='court.vendor.business_name', read_only=True, default=None)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('id', 'user', 'status', 'total_price', 'commission', 'created_at')

    def validate(self, attrs):
        from .services import validate_booking_slots
        instance = self.instance
        court = attrs.get('court', instance.court if instance else None)
        date = attrs.get('date', instance.date if instance else None)
        start_time = attrs.get('start_time', instance.start_time if instance else None)
        end_time = attrs.get('end_time', instance.end_time if instance else None)

        if court and date and start_time and end_time:
            exclude_pk = instance.pk if instance else None
            validate_booking_slots(court, date, start_time, end_time, exclude_pk)
        return attrs


class BookingListSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    user_id = serializers.ReadOnlyField(source='user.id')
    user_email = serializers.ReadOnlyField(source='user.email')
    user_phone = serializers.ReadOnlyField(source='user.phone_number')
    user_role = serializers.ReadOnlyField(source='user.role')
    court_name = serializers.CharField(source='court.name', read_only=True)

    class Meta:
        model = Booking
        fields = ('id', 'user', 'user_id', 'user_email', 'user_phone', 'user_role', 'court_name', 'date', 'start_time', 'end_time', 'status', 'total_price', 'commission')
