import pyotp
from datetime import datetime , timedelta
import logging
from .models import CustomUser, OtpToken
from django.core.mail import EmailMessage
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

def generateotp(email):
    """Generate a 6-digit OTP"""
    user = CustomUser.objects.get(email=email)

    if not user.otp_secret_key:
        # Generate a new secret key for the user if not already present
        secret_key = pyotp.random_base32()
        user.otp_secret_key = secret_key
        user.save()

    totp = pyotp.TOTP(user.otp_secret_key, interval=300) # OTP valid for 5 minutes
    otp = totp.now()

    try:
        existing_otp = OtpToken.objects.get(user=user)
        if existing_otp.is_valid() and not existing_otp.is_used:
            return existing_otp.otp  # Return existing valid OTP
        existing_otp.delete()  # Remove expired or used OTP
        
    except OtpToken.DoesNotExist:
        logging.info("No existing OTP found, generating a new one.")
        pass
    
    # Create a new OTP record
    OtpToken.objects.create(user=user, otp=otp,)
    logging.info(f"Generated new OTP for user {email}")
    return otp

def sendotp_via_email(email):
    """Send OTP to the specified email address""" 
    try:
        otp = generateotp(email)
        user = CustomUser.objects.get(email=email)
    
        subject = 'Password Reset Request'
        message = f"""
            Hi {user.username},
            You requested a password reset. Click the link below to reset your password:
                Your OTP is: {otp}
            If you didn't request this, please ignore this email.
            This link will expire in 5 min. [draft]
            """
    
        payload = EmailMessage(subject=subject, body=message, from_email=settings.DEFAULT_FROM_EMAIL, to=[email])
        # Send the email, silencing any errors that occur
        payload.send(fail_silently=False)
        return Response({
            "data": "Email sent successfully"
                    }, status=status.HTTP_200_OK)
    
    except CustomUser.DoesNotExist:
        logging.error(f"User with email {email} does not exist.")
        return Response({
            "success": False,
            "message": "User does not exist"
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logging.error(f"Error sending email to {email}: {e}")
        return Response({
            "success": False,
            "message": "Failed to send OTP"
        }, status=status.HTTP_400_BAD_REQUEST)

