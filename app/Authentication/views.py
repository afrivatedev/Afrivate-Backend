import logging

from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.http import HttpResponse

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from user_database.models import CustomUser
from user_database.serializers import *

from django.contrib.auth.tokens import default_token_generator
# from django.utils.encoding import force_bytes, force_str


from .utils import sendotp_via_email

# Create your views here.
def index(request):
    return HttpResponse("Welcome to Afrivate Authentication Service")

# user registration view
class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = CustomUserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # this would always run all the methods in the serializer
        user = serializer.save()

        return Response({
            #"id": user.id,
            "message": "User registered successfully, Check your mail for email verification link",
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

        # Generate JWT token
        tokens = user.tokens()  # to create tokens method in model
        logging.info(f"Generating tokens for user {user.id}")
        
        return Response({
            "message": "Login successful",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role
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
            sendotp_via_email(user.email)
            logging.info(f"Email sent successfully to {email}")  # For debugging

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

        # Generate JWT token
        user.tokens()  # to create tokens method in model

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

# user profile view
class ProfileView(generics.RetrieveAPIView):
    pass  # Implementation goes here

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
        user = serializer.validated_data['user']
        
        # Generate tokens
        tokens = user.tokens()
        
        return Response({
            "success": True,
            "message": "OTP verified successfully",
            # "refresh": str(tokens['refresh_token']),
            "access": str(tokens['access_token'])
        }, status=status.HTTP_200_OK)
    
# waitlist email view
class WaitlistEmailView(generics.GenericAPIView):
    serializer_class = waitlistEmailSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # SEND CONFIRMATION EMAIL

                return Response({
                    "success": True,
                    'message': "Check your email for confirmation",
                    'email': user.email
                    },
                    status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                   'success': False,
                   'message': ' An error occured. Please try again.' 
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({
            "message": "Email added to waitlist successfully",
            'errors': serializer.errors
            },status=status.HTTP_201_CREATED)
    
'''
class VerifyEmail(generics.GenericAPIView):

    def post(self, request, *args, **kwargs):
        
        # get user email
    
        # create email payload

        # get redirect link

        # create a token generator

        # move this to utils
        user = CustomUser.objects.get(email=email) 
                
        subject = "Verify Email"
        message = f"""
            Dear {user.username},
            Your email has been successfully verified 
                a redirect link to login page. {link}

            If you didn't request this, please ignore this email.
            This otp will expire in 10 minutes. 
            """
        try:
            email_message = EmailMessage(subject=subject,
                                        body=message,
                                            from_email=settings.DEFAULT_FROM_EMAIL, 
                                            to=[email]
                                            )
            # Send the email, silencing any errors that occur
            email_message.send(fail_silently=False)
            
'''

# waitlist stats view
