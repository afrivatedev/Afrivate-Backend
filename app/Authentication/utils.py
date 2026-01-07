from datetime import timedelta
from django.utils import timezone
import logging

from user_database.models import CustomUser

from django.core.mail import send_mail # , EmailMessage
from django.conf import settings

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

    otp = send_otp(email)

    if otp is None:
        return False
    
    try:
        user = CustomUser.objects.get(email=email) # calling this in the send_otp function
        subject = 'Password Reset Request'
        message = f"""
            Dear {user.username},
            You requested a password reset. 

                Your OTP is: {otp}

            If you didn't request this, please ignore this email.
            This otp will expire in 10 minutes. 
            """
    
        send_mail(
                subject=subject,
                message=message,
                from_email= settings.DEFAULT_FROM_EMAIL, 
                recipient_list=[email],
                fail_silently=False
            )
        return True
    
    except CustomUser.DoesNotExist:
        logging.error(f"User with email {email} does not exist.")
        return False
    
    except Exception as e:
        logging.error(f"Error sending email to {email}: {e}")
        return False


