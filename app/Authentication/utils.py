from datetime import timedelta
from django.utils import timezone
import logging

from user_database.models import CustomUser, OtpToken

from django.core.mail import EmailMessage
from django.conf import settings

from rest_framework.response import Response
from rest_framework import status

import random

def send_otp(email):
    """Generate and send OTP to the user's email"""
    otp = random.randint(100000, 999999)
    try: 
        user = CustomUser.objects.get(email=email)
        user.reset_password_otp = otp
        user.reset_password_otp_expiry = timezone.now() + timedelta(minutes=10)  # OTP valid for 10 minutes
        user.reset_password_otp_used = False
        user.save()
        return otp
    except CustomUser.DoesNotExist:
        logging.error(f"User with email {email} does not exist.")
        return None


def sendotp_via_email(email):
    """Send OTP to the specified email address""" 
    # otp = generateotp(email)  #pyotp based otp
    otp = send_otp(email)
    if otp is None:
        return Response({
            "success": False,
            "message": "User does not exist"
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = CustomUser.objects.get(email=email) # calling this in the send_otp function
    subject = 'Password Reset Request'
    message = f"""
        Dear {user.username},
        You requested a password reset. 

            Your OTP is: {otp}

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
        return Response({
                    "success": True,
                    "message": "Email sent successfully"
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
