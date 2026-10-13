from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, extend_schema_view
from ..serializers import UserSerializer, UserCreateSerializer, UserProfileSerializer, ChangePasswordSerializer, CustomTokenObtainPairSerializer, DetailResponseSerializer, CheckAvailabilitySerializer, CheckAvailabilityResponseSerializer

User = get_user_model()


class AuthAnonThrottle(AnonRateThrottle):
    scope = 'auth'


class CheckAvailabilityThrottle(AnonRateThrottle):
    scope = 'check_availability'


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AuthAnonThrottle]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserCreateSerializer
    throttle_classes = [AuthAnonThrottle]


@extend_schema(
    request=CheckAvailabilitySerializer,
    responses={200: CheckAvailabilityResponseSerializer},
)
class CheckAvailabilityView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [CheckAvailabilityThrottle]

    def post(self, request):
        serializer = CheckAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = {}
        username = data.get('username', '').strip()
        if username:
            result['username_available'] = not User.objects.filter(
                username__iexact=username
            ).exists()
        email = data.get('email', '').strip()
        if email:
            result['email_available'] = not User.objects.filter(
                email__iexact=email
            ).exists()
        return Response(result, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        description='Retrieve the authenticated user profile.',
        responses={200: UserProfileSerializer},
    ),
    patch=extend_schema(
        description='Partially update the authenticated user profile.',
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    ),
)
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(
    description='Change the authenticated user password.',
    request=ChangePasswordSerializer,
    responses={200: DetailResponseSerializer},
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'status': 'password changed'}, status=status.HTTP_200_OK)
