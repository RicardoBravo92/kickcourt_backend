from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)

    class Meta:
        model = Message
        fields = (
            'id',
            'booking',
            'sender_id',
            'sender_username',
            'sender_role',
            'text',
            'created_at',
            'read_at',
        )
        read_only_fields = fields