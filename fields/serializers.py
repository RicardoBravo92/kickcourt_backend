from rest_framework import serializers
from .models import Field


class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = '__all__'
        read_only_fields = ('id',)


class FieldListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = ('id', 'name', 'field_type', 'surface', 'price_per_hour', 'is_active')
