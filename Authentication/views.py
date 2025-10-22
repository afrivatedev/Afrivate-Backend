# from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.views import APIView
from .serializers import CustomUserRegistrationSerializer, CustomUserLoginSerializer
from .models import CustomUser
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .serializers import ForgotPasswordSerializer, ResetPasswordSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
# Create your views here.

# user registration view
class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            #"id": user.id,
            "message": "User registered successfully",
            "user": {
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }, status=status.HTTP_201_CREATED)

# user login view
class LoginView(generics.GenericAPIView):
    serializer_class = CustomUserLoginSerializer
    queryset = CustomUser.objects.all()
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        if user:
            return Response({
                "message": "Login successful",
                "user": {
                    "username": user.username,
                    "email": user.email,
                    # "role": user.role
                }
            }, status=status.HTTP_200_OK)
        return Response({"message": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
    
# password forgot view
class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = CustomUser.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # build reset link
            reset_link = f"http://127.0.0.1:8000/api/auth/reset-password/{uid}/{token}/"

            # send email
            subject = 'Password Reset Request'
            message = f"""
            Hi {user.username},
            You requested a password reset. Click the link below to reset your password:
             {reset_link}
            
            If you didn't request this, please ignore this email.
            
            This link will expire in 24 hours.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            print(f"Email sent successfully to {email}")  # For debugging

            return Response({"message": f"Password reset link sent with token {token}"})
        except CustomUser.DoesNotExist:
            pass
        return Response({"message": "Password reset link sent"}, status=status.HTTP_200_OK)

# password reset view
class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    
    def post(self, request, *args, **kwargs):
        print(request.data)
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
    
# user profile view
class ProfileView(generics.RetrieveAPIView):
    pass  # Implementation goes here

# user logout view
class LogoutView(APIView):
    pass # Implementation goes here



# user deletion view
class DeleteUserView(generics.DestroyAPIView):  
    pass  # Implementation goes here

