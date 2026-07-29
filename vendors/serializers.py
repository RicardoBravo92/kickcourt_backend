from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Vendor

User = get_user_model()


class VendorSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    court_count = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at')

    def get_court_count(self, obj):
        return obj.courts.active().count()


class VendorListSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Vendor
        fields = ('id', 'user', 'business_name', 'description', 'phone', 'address', 'institution_number', 'is_approved', 'commission_rate', 'created_at')
