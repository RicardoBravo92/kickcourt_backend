from django.urls import path
from .views.auth import RegisterView, ProfileView, ChangePasswordView, CheckAvailabilityView
from .views.password_reset import ForgotPasswordView, ResetPasswordView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('check-availability/', CheckAvailabilityView.as_view(), name='check_availability'),
    path('profile/', ProfileView.as_view(), name='user_profile'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('password/forgot/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset_password'),
]
