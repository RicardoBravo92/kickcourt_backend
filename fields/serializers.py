from rest_framework import serializers
from .models import Field, FieldSchedule, FieldBlock


class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = '__all__'
        read_only_fields = ('id',)


class FieldListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = ('id', 'name', 'field_type', 'surface', 'price_per_hour', 'is_active')


class FieldScheduleSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = FieldSchedule
        fields = '__all__'
        read_only_fields = ('id',)


class FieldBlockSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = FieldBlock
        fields = '__all__'
        read_only_fields = ('id', 'created_by', 'created_at')
