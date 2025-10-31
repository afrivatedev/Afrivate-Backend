from rest_framework import serializers, status
# from Authentication.backends import User
from .models import CustomUser, OtpToken
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
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
        try: 
           validate_password(value)
        except DjangoValidationError as e:
            logging.error(f"Password validation error: {e.messages}")
            raise serializers.ValidationError(e.messages)
        return value

class CustomUserLoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(
        style ={'input_type': 'password'}, write_only=True)
    
    def validate(self, data):
        username_or_email = data.get('username_or_email')
        password = data.get('password')
        
        # try with email first
        user = authenticate(email=username_or_email, password=password) # can use both username/email to login
        if not user:
            # try with username
            user = authenticate(username=username_or_email, password=password)
            
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

class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField() # what is uid here?
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
                logging.error(f"Password change failed for user {self.context['request'].user.id}: New passwords do not match.")
                raise serializers.ValidationError(
                    {"confirm_password": "Passwords do not match"}, code=status.HTTP_400_BAD_REQUEST)
            return data
    
class ProfileSerializer(serializers.ModelSerializer):
    pass

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
    otp = serializers.CharField(max_length=6)

    class Meta:
        fields = ['otp']    

    def validate(self, attrs): 
        otp_code = attrs.get('otp')
        
        # Get the OTP instance
        try:
            otp_instance = OtpToken.objects.get(otp=otp_code, is_used=False, expired=False)
        except OtpToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP")
        
        user = otp_instance.user
        
        # Check if user exists
        if not user:
            raise serializers.ValidationError("No user associated with this OTP")
        
        # Check if OTP is expired
        if otp_instance.is_expired():
            otp_instance.mark_as_expired()
            raise serializers.ValidationError("OTP has expired")
        
        # Mark OTP as used and expired
        otp_instance.mark_as_used()
        otp_instance.mark_as_expired()
        
        # Add user to validated data so the view can access it
        attrs['user'] = user
        
        return attrs  