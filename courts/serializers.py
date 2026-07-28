from rest_framework import serializers
from .models import Court, CourtSchedule, CourtBlock


class CourtSerializer(serializers.ModelSerializer):
    sport_type_display = serializers.CharField(source='get_sport_type_display', read_only=True)
    surface_display = serializers.CharField(source='get_surface_display', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True, default=None)

    class Meta:
        model = Court
        fields = '__all__'
        read_only_fields = ('id', 'deleted_at')


class CourtListSerializer(serializers.ModelSerializer):
    sport_type_display = serializers.CharField(source='get_sport_type_display', read_only=True)
    surface_display = serializers.CharField(source='get_surface_display', read_only=True)

    class Meta:
        model = Court
        fields = ('id', 'name', 'sport_type', 'sport_type_display', 'surface', 'surface_display',
                  'players_per_side', 'price_per_hour', 'is_active')


class CourtScheduleSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)

    class Meta:
        model = CourtSchedule
        fields = '__all__'


class CourtBlockSerializer(serializers.ModelSerializer):
    court_name = serializers.CharField(source='court.name', read_only=True)

    class Meta:
        model = CourtBlock
        fields = '__all__'
        read_only_fields = ('id', 'created_by', 'created_at')
