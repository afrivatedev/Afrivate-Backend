import logging

from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from user_database.models import CustomUser
from user_database.serializers import *

from .utils import sendotp_via_email

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

        # verify user email validity


        user = serializer.save()

        return Response({
            #"id": user.id,
            "message": "User registered successfully",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name
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

        # Generate JWT token
        tokens = user.tokens()  # to create tokens method in model
        logging.info(f"Generating tokens for user {user.id}")
        
        return Response({
            "message": "Login successful",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role,  
                "first_name": user.first_name,
                "last_name": user.last_name
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
                    "message": "Please verify your email first."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            verification, otp = EmailVerification.create_otp_verification(
                email=email,
                verification_type='password_reset',
                user=user,
                expiry_minutes=10
            )
            
            email_sent = sendotp_via_email(user.email) # ........
            
            if email_sent:
                logger.info(f"Password reset OTP sent to {email}")
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
        # Generate JWT token
        user.tokens()  # to create tokens method in model
        
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
    pass  # Implementation goes here       

# otp verify view
class OtpVerifyView(generics.GenericAPIView): 
    serializer_class = VerifyOTPSerializer  
    # permission_classes = [IsAuthenticated]
            
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the verified user from serializer
        verification = serializer.validated_data['verification']
        user = serializer.validated_data['user']

        logging.info(f"OTP verified for user {user.email}")
         
        # Generate tokens
        tokens = user.tokens()
        
        return Response({
            "success": True,
            "message": "OTP verified successfully",
            # "refresh": str(tokens['refresh_token']),
            "access": str(tokens['access_token'])
        }, status=status.HTTP_200_OK)
    
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
