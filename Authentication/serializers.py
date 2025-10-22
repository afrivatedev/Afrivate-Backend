from rest_framework import serializers, status
from .models import CustomUser

class CustomUserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'role', 'password2']

        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(**validated_data)
        return user
    
    # Update serializers can be added here for profile updates, password changes, etc.

class CustomUserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        style ={'input_type': 'password'}, write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            raise serializers.ValidationError(
                {"message": "Email and password are required"}
            )
        
        user = CustomUser.objects.filter(email=email).first()
        
        if not user:
            raise serializers.ValidationError(
                {"message": "Invalid email or password"}
            )
        
        if not user.check_password(password):
            raise serializers.ValidationError(
                {"message": "Invalid email or password"}
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                {"message": "User account is disabled"}
            )
        
        # Store user in context for use in the view
        data['user'] = user
        return data
    
class LogoutSerializer(serializers.Serializer):
    pass  # No fields needed for logout

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
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