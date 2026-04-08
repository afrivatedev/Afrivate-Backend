from django.urls import path, include
from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = "accounts"

urlpatterns = [
    path('', index, name='index'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # not used currently
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    # path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    path('logout/', LogoutView.as_view(), name='logout'),
    
    path('verify-otp/', OtpVerifyView.as_view(), name='verify-otp'),  # new path for verifying OTP
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('verify-password-reset-otp/', VerifyPasswordResetOtpView.as_view(), name='verify-password-reset-otp'),

    path('google/pathfinder/', GoogleLoginView.as_view(), {'role': 'pathfinder'}, name='google-pathfinder'),
    path('google/enabler/', GoogleLoginView.as_view(), {'role': 'enabler'}, name="google-enabler"),
    path('set-password/', SetPasswordView.as_view(), name='set-password'),

    path('delete-account/', DeleteUserView.as_view(), name='delete-account'),
]
    