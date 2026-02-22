from rest_framework import serializers, status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CustomUser, EmailVerification

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

import logging

# Create your serializers here.
class CustomUserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'role', 'password2']

        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):  # double password validation, determine to keep or not
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(**validated_data)
        return user

    # Update serializers can be added here for profile updates, password changes, etc.
    def validate_password(self, value):
        """This would validate the password like checking its strength and length.
        DRF takes the password field automatically and runs this method on it."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            logging.error(f"Password validation error: {e.messages}")
            raise serializers.ValidationError(e.messages)
        return value


class CustomUserLoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)

    def validate(self, data):
        username_or_email = data.get('username_or_email')
        password = data.get('password')

        # try with email first
        user = authenticate(email_or_username=username_or_email, password=password)  # can use both username/email to login
        if not user:
            # try with username
            user = authenticate(email_or_username=username_or_email, password=password)


        if not user:
            raise serializers.ValidationError(
                {"error": "Invalid email or password"}, code=status.HTTP_401_UNAUTHORIZED)

        # Store user in context for use in the view
        data['user'] = user
        return data


class LogoutSerializer(serializers.Serializer):
    pass  # No fields needed for logout


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower().strip()
        
        try:
            user = CustomUser.objects.get(email=email)
            if not user.is_email_verified:
                raise serializers.ValidationError(
                    "Please verify your email before resetting password."
                )
            return email
            
        except CustomUser.DoesNotExist:
            return email

class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()  # what is uid here?
    token = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)
    confirm_password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)

    def validate(self, data):
        password = data.get('password')
        confirm_password = data.get('confirm_password')

        if password != confirm_password:
            raise serializers.ValidationError(
                {"password": "Passwords do not match"}, code=status.HTTP_400_BAD_REQUEST)
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)
    new_password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)
    confirm_password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            logging.error(f"Password change failed for user {user.id}: Old password is incorrect.")
            raise serializers.ValidationError(
                {"old_password": "Old password is not correct"}, code=status.HTTP_400_BAD_REQUEST)
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            logging.error(
                f"Password change failed for user {self.context['request'].user.id}: New passwords do not match.")
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}, code=status.HTTP_400_BAD_REQUEST)
        return data


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, email):
        try:
            # Check if any user has already been registered with this email
            if CustomUser.objects.filter(email=email).exists():
                return email
                # user = CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError(
                {"error": "No user is associated with this email"}, code=status.HTTP_400_BAD_REQUEST)
        return email


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    class Meta:
        fields = ['otp']

    def validate(self, attrs):
        email = attrs.get('email').lower().strip()
        otp = attrs.get('otp')

        # Get the OTP instance
        try:
            verification = EmailVerification.objects.filter(
                email=email,
                token=otp,
                verification_type='password_reset',
                is_verified=False
            ).order_by('-created_at').first()

            if not verification:
                raise serializers.ValidationError({
                    'otp': 'Invalid OTP code'
                })

            if verification.is_expired():
                raise serializers.ValidationError({
                    'otp': 'OTP has expired. Please request a new one.'
                })

            user = CustomUser.objects.get(email=email)

            attrs['verification'] = verification
            attrs['user'] = user

        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                'email': 'User not found'
            })

class VerifyEmailSerializer(serializers.Serializer):

    class Meta:
        ref_name = "CustomVerifyEmailSerializer"
        
    # email = serializers.EmailField()    
    token = serializers.CharField(max_length=64)

    def validate_token(self, value):
        try:
            self.verification_obj = EmailVerification.objects.get(token=value)
            
            if self.verification_obj.is_verified:
                raise serializers.ValidationError("This verification link has already been used.")
            
            if self.verification_obj.is_expired():
                raise serializers.ValidationError("This verification link has expired.")
            
            return value
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("Invalid verification token.")

    def verify(self):
        """Process the verification"""
       
        verification = self.verification_obj  

        try:
            with transaction.atomic():  
                # Mark verification as complete
                verification.mark_verified()
                
                # Update model based on verification type
                if verification.verification_type == 'waitlist':
                    if hasattr(verification, 'waitlist_email'):
                        verification.waitlist_email.is_verified = True
                        verification.waitlist_email.save()
                
                elif verification.verification_type == 'user_signup':
                    if verification.user:
                        verification.user.is_email_verified = True
                        verification.user.save()
                
                return verification
        except Exception as e:
            logging.error(f"Error during verification process: {str(e)}")
            raise e


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
    
        token["role"] = user.role
        token["email"] = user.email

        return token