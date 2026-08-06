from django.urls import path
from .views.auth import RegisterView, ProfileView, ChangePasswordView
from .views.password_reset import ForgotPasswordView, ResetPasswordView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('profile/', ProfileView.as_view(), name='user_profile'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('password/forgot/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset_password'),
]
