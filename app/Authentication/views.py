import logging

from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.db import transaction

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from user_database.models import CustomUser, EmailVerification
from user_database.serializers import *
# from user_database.serializers import GoogleAuthSerializer # no need

from .utils import sendotp_via_email, send_signup_otp_email, send_welcome_email

from datetime import timedelta

User = get_user_model()

# Create your views here.
def index(request):
    return HttpResponse("Welcome to Afrivate Technologies Backend Service")

# user registration view
class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = CustomUserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # this would always run all the methods in the serializer

        try:
            with transaction.atomic():   # applying fix
                user = serializer.save()

                # should wrap this up in a transaction, if email sending fails, we should rollback user creation
                verification, otp = EmailVerification.create_otp_verification(
                    email=user.email,
                    verification_type='user_signup',
                    user=user,
                    expiry_minutes=10
                )
                send_signup_otp_email(user.email, otp, user.username)

        except Exception as e:
            logging.error(f"Registration failed: {e}")
            return Response(
                {"error": "Registration failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "User registered successfully. Please check your email for the OTP verification code.",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }, status=status.HTTP_201_CREATED)

# user login view
class LoginView(generics.GenericAPIView):
    serializer_class = CustomUserLoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if not user.is_email_verified:
            return Response({
                "error": "Account not verified. Please verify your email using the OTP sent to you."
            }, status=status.HTTP_403_FORBIDDEN)

        # Generate JWT token
        tokens = user.tokens()  # to create tokens method in model
        logging.info(f"Generating tokens for user {user.id}")
        
        return Response({
            "message": "Login successful",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role,  
            },
            "refresh": tokens['refresh_token'],
            "access": tokens['access_token']
        }, status=status.HTTP_200_OK)
    
# password forgot view
class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # send password reset email
        try:
            user = CustomUser.objects.get(email=email)

            # Check if email is verified
            if not user.is_email_verified:
                return Response({
                    "success": False,
                    "message": "Please verify your email first." # i need an explanation for this, if email is not verified, how will they receive the password reset otp?  
                }, status=status.HTTP_400_BAD_REQUEST)
            
            verification, otp = EmailVerification.create_otp_verification(
                email=email,
                verification_type='password_reset',
                user=user,
                expiry_minutes=10
            )
            
            email_sent = sendotp_via_email(user.email, otp, user.username)
            
            if email_sent:
                return Response({
                    "success": True,
                    "message": "If the email exists, a password reset code has been sent."
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "message": "Failed to send OTP. Please try again."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except CustomUser.DoesNotExist:
            logging.warning(f"Password reset requested for a non existent user with non-existent email-> {email}")

        return Response({"message": "If the email exists, a password reset link has been sent."}, status=status.HTTP_200_OK)
    
class VerifyPasswordResetOtpView(generics.GenericAPIView):
    serializer_class = VerifyPasswordResetOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verification = serializer.validated_data['verification']
        user = serializer.validated_data['user']

        verification.mark_verified()

        logging.info(f"Password reset OTP verified for {user.email}")

        return Response({
            "success": True,
            "message": "OTP verified. You may now reset your password.",
            "uid": user.pk,
        }, status=status.HTTP_200_OK)

# password reset view
class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        
        try:
            # Decode token to get user 
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)

            # For demo, let's assume token belongs to the first user
            if default_token_generator.check_token(user, token):
                user.set_password(password)
                user.save()
                return Response(
                    {"message": "Password reset successful"}, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Invalid or expired token"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {"error": "Invalid reset link"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

# user change password view
class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
    
            user = request.user
            # new_password = serializer.validated_data['new_password']
            user.set_password(serializer.validated_data['new_password'])
            user.save()
    
            logging.info(f"Password changed successfully for user {user.id}")
            return Response(
                {"message": "Password changed successfully"}, 
                status=status.HTTP_200_OK
            )

# user logout view
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logging.info(f"User {request.user.id} is logging out.")
        try:
            refresh_token = request.data["refresh"]
            if not refresh_token:
                logging.error(f"Logout error for user {request.user.id}: No refresh token provided.")
                return Response({"error": "No refresh token provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()

            logging.info(f"User logged out successfully: {request.user.id}")
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        
        except Exception as e:
            logging.error(f"Logout error for user {request.user.id}: {e}")
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

# user deletion view
class DeleteUserView(generics.DestroyAPIView):  
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        logging.info(f"User deletion requested for user {user.id}")
        user.delete()
        logging.info(f"User deleted successfully: {user.id}")
        return Response({"message": "User account deleted successfully"}, status=status.HTTP_200_OK)   

# otp verify view
class OtpVerifyView(generics.GenericAPIView): 
    serializer_class = VerifyRegistrationOTPSerializer 
    permission_classes = [AllowAny]
            
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the verified user from serializer
        verification = serializer.validated_data['verification']
        user = serializer.validated_data['user']

        verification.mark_verified()

        user.is_email_verified = True
        user.save()

        logging.info(f"OTP verified successfully for user {user.email}")
        
        # Generate tokens
        tokens = user.tokens()
        
        return Response({
            "success": True,
            "message": "Email verified successfully.",
            "user": {
                "email": user.email,
                "username": user.username,
                "is_email_verified": user.is_email_verified
            },
            "refresh": str(tokens['refresh_token']),
            "access": str(tokens['access_token'])
        }, status=status.HTTP_200_OK)

# resend otp view
class ResendOtpView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        from django.utils import timezone

        email = request.data.get('email', '').lower().strip()

        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Don't reveal whether email exists
            return Response(
                {"message": "If this email is registered, a new OTP has been sent."}, 
                status=status.HTTP_200_OK
            )

        if user.is_email_verified:
            return Response(
                {"error": "This account is already verified."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        latest = EmailVerification.objects.filter(
            email=email,
            verification_type = 'user_signup',
            is_verified = False
        ).order_by('-created_at').first()

        MAX_RESENDS = 3 # things like this should ideally be in settings incase of changes
        COOLDOWN_MINUTES = 30

        if latest:
            if latest.resend_count >= MAX_RESENDS:
                if latest.last_resend_at:
                    cooldown_end = latest.last_resend_at + timedelta(minutes=COOLDOWN_MINUTES)
                    if timezone.now() < cooldown_end:
                        wait_minutes = int((cooldown_end - timezone.now()).seconds / 60) + 1
                        return Response({
                            "error": f"Too many OTP requests. Please wait {wait_minutes} minutes before trying again."
                        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                    else:
                        latest.resend_count = 0
                        latest.save()

        # Invalidate old OTPs
        EmailVerification.objects.filter(
            email=email,
            verification_type='user_signup',
            is_verified=False
        ).update(expires_at=timezone.now())  # expire them all

        verification, otp = EmailVerification.create_otp_verification(
            email=email,
            verification_type='user_signup',
            user=user,
            expiry_minutes=10
        )

        verification.resend_count = (latest.resend_count + 1) if latest else 1
        verification.last_resend_at = timezone.now()
        verification.save()

        send_signup_otp_email(email, otp, user.username)

        logging.info(f"OTP resent to {email}, resend count: {verification.resend_count}")

        return Response(
            {"message": "If this email is registered, a new OTP has been sent."}, 
            status=status.HTTP_200_OK
        )

# verify email view    
class VerifyEmailView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyEmailSerializer
    
    def get(self, request, *args, **kwargs):
        token = request.query_params.get('token')

        if not token:
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/verify-error?reason=no_token")
        
        serializer = self.get_serializer(data={'token': token})

        if serializer.is_valid():
            try:
                verification = serializer.verify()
                logging.info(f"Email verified successfully for {verification.email}")
                
                send_welcome_email(verification.email, verification.waitlist_email.name if hasattr(verification, 'waitlist_email') else "")
                
                return HttpResponseRedirect(f"{settings.FRONTEND_URL}/verify-success")
                
            except Exception as e:
                logging.error(f"Error verifying email: {str(e)}")
                return HttpResponseRedirect(f"{settings.FRONTEND_URL}/verify-error?reason=server_error")
            
        errors = serializer.errors.get('token', [])
        if any("already been used" in str(e) for e in errors):
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/verify-success?already_done=true")

        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/verify-error?reason=invalid_token")
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                verification = serializer.verify()
                return Response({
                    'success': True,
                    'message': 'Email verified successfully!',
                    'email': verification.email
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logging.error(f"Error verifying email: {str(e)}")
                return Response({
                    'success': False,
                    'message': 'An error occurred during verification'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'message': serializer.errors.get('token', ['Invalid token'])[0]
        }, status=status.HTTP_400_BAD_REQUEST)

# Google Login
class GoogleLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = GoogleAuthSerializer

    def post(self, request, role='pathfinder', *args, **kwargs):
        if role not in ['pathfinder', 'enabler']:
            return Response(
                {"error": "Invalid role. Must be 'pathfinder' or 'enabler'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_data = serializer.get_user_data()
        email = user_data['email']

        try:
            # Existing user — just log them in, don't change their role
            user = User.objects.get(email=email)
            logging.info(f"Existing user logged in via Google: {email}")

        except User.DoesNotExist:
            username = user_data['username']

            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                email=email,
                username=username,
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=role,
                is_email_verified=True,  
                auth_provider='google',
            )
            logging.info(f"New user created via Google: {email} with role {role}")

        tokens = user.tokens()

        return Response({
            "message": "Google login successful.",
            "user": {
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_email_verified": user.is_email_verified,
            },
            "access": tokens['access_token'],
            "refresh": tokens['refresh_token'],
        }, status=status.HTTP_200_OK)

class SetPasswordView(generics.GenericAPIView):
    """Allows Google-authenticated users to set a password 
    so they can also use normal email/password login"""
    permission_classes = [IsAuthenticated]
    serializer_class = SetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not new_password or not confirm_password: # all this logic realy shouldn't be here
            return Response(
                {"error": "new_password and confirm_password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {"error": "Passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response({"error": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.auth_provider = 'email' 
        user.set_password(serializer.validated_data['new_password'])
        user.auth_provider = 'email'
        user.save()

        logging.info(f"Password set for Google user {user.email}")
        return Response(
            {"message": "Password set successfully. You can now login with email and password."},
            status=status.HTTP_200_OK
        )