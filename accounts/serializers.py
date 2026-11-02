from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer that accepts either email or username for login.
    Since USERNAME_FIELD = 'email', the parent expects 'email' field.
    We make email not required so username can be used instead.
    """
    # Override the username_field to use our custom logic
    username_field = 'email'
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TokenObtainSerializer.__init__ forcibly replaces the username field
        # with a required CharField, ignoring the ``required=False`` above.
        # Relax it so a login payload carrying only ``username`` validates,
        # then let ``validate()`` resolve the real identifier.
        self.fields[self.username_field].required = False
        self.fields[self.username_field].allow_blank = True

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        username = (attrs.get('username') or '').strip()

        # If an explicit email field was sent, use it directly
        # (USERNAME_FIELD = 'email').
        if email:
            attrs['email'] = email.lower()
        elif username:
            # The login form sends a single "username" field that may hold
            # either the username or the email address.
            lookup = (
                {'email__iexact': username}
                if '@' in username
                else {'username__iexact': username}
            )
            user = User.objects.filter(**lookup).first()
            if user is None:
                raise serializers.ValidationError(
                    {'detail': 'No account found with these credentials.'}
                )
            attrs['email'] = user.email.lower()
        else:
            raise serializers.ValidationError(
                {'detail': 'Email or username is required.'}
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
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )


class CheckAvailabilitySerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class CheckAvailabilityResponseSerializer(serializers.Serializer):
    username_available = serializers.BooleanField(required=False, allow_null=True)
    email_available = serializers.BooleanField(required=False, allow_null=True)
