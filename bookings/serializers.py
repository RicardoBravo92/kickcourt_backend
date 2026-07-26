from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    field_name = serializers.CharField(source='field.name', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('id', 'user', 'total_price', 'created_at')

    def validate(self, attrs):
        from .services import validate_booking_slots
        field = attrs.get('field')
        date = attrs.get('date')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if field and date and start_time and end_time:
            exclude_pk = self.instance.pk if self.instance else None
            validate_booking_slots(field, date, start_time, end_time, exclude_pk)
        return attrs


class BookingListSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source='field.name', read_only=True)

    class Meta:
        model = Booking
        fields = ('id', 'field_name', 'date', 'start_time', 'end_time', 'status', 'total_price')
