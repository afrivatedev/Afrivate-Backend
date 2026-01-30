from datetime import timedelta
from django.utils import timezone
import logging

from user_database.models import CustomUser

from django.core.mail import send_mail # , EmailMessage
from django.conf import settings

import random

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To # , Content

# Generate OTP 
def send_otp(email):
    """Generate and send OTP to the user's email"""
    otp = random.randint(100000, 999999)
    try: 
        user = CustomUser.objects.get(email=email)
        
        user.save()
        return otp
    except CustomUser.DoesNotExist:
        logging.error(f"User with email {email} does not exist.")
        return None
    
# send email then receive otp input and verify 
def sendotp_via_email(email):
    """Send OTP to the specified email address""" 

    otp = send_otp(email)

    if otp is None:
        return False
    
    try:
        user = CustomUser.objects.get(email=email) # calling this in the send_otp function
        subject = 'OTP for email verification - Afrivate'
        message = f"""
            Dear {user.username},
            You requested a password reset. 

                Your OTP is: {otp}

            If you didn't request this, please ignore this email.
            This otp will expire in 10 minutes. 
            """
    
        message = Mail(
        from_email=Email(settings.DEFAULT_FROM_EMAIL, 'Afrivate Tech'),
        to_emails=To(email),
        subject=subject)

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(f"SendGrid response status for {email}: {response.status_code}")

        if response.status_code == 202:
            logging.info(f"otp email sent successfully to {email}")
            return True
        else:
            logging.warning(f"SendGrid returned status {response.status_code} for {email}")
            return False
    
    except CustomUser.DoesNotExist:
        logging.error(f"User with email {email} does not exist.")
        return False
    
    except Exception as e:
        logging.error(f"Error sending email to {email}: {e}")
        return False

# Send a confirmation email once verification is there
def send_welcome_email(email, name):
    subject = 'Welcome to Afrivate!'
    
    try:
        message = Mail(
        from_email=Email(settings.DEFAULT_FROM_EMAIL, 'Afrivate Tech'),
        to_emails=To(email),
        subject=subject)

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(f"SendGrid response status for {email}: {response.status_code}")

        if response.status_code == 202:
            logging.info(f"Verification email sent successfully to {email}")
            return True
        else:
            logging.warning(f"SendGrid returned status {response.status_code} for {email}")
            return False
    except Exception as e:
        print(f"SendGrid Error for {email}: {str(e)}")
        return False
