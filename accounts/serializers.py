from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username = serializers.CharField(required=True)

    def validate(self, attrs):
        username_or_email = attrs.get('username', '')
        if '@' in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
                attrs['username'] = user.username
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    {'detail': 'No account found with this email.'}
                )
            except MultipleObjectsReturned:
                raise serializers.ValidationError(
                    {'detail': 'No account found with this email.'}
                )
        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        return token


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'phone_number')
        read_only_fields = ('id',)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password_confirm', 'phone_number')
        read_only_fields = ('id',)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "Password fields didn't match."
            })
        return data

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return email

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        validated_data['role'] = User.Roles.CLIENT
        if validated_data.get('email'):
            validated_data['email'] = validated_data['email'].lower()
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'role')
        read_only_fields = ('id', 'username', 'role')


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Passwords didn't match."})
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField(help_text='Base64-encoded user id from the reset link.')
    token = serializers.CharField(help_text='Password reset token from the reset link.')
    new_password = serializers.CharField(write_only=True, min_length=8)


class CheckAvailabilitySerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class CheckAvailabilityResponseSerializer(serializers.Serializer):
    username_available = serializers.BooleanField(required=False, allow_null=True)
    email_available = serializers.BooleanField(required=False, allow_null=True)
