import logging
import resend

from django.core.mail import send_mail # , EmailMessage
from django.conf import settings

from celery import shared_task

resend.api_key = settings.RESEND_API_KEY

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_signup_otp_email(self, email, otp, username="User"):
    """Send OTP email for new user registration"""
    message = f"""
    Dear {username},

    Welcome to Afrivate!

    Your OTP for email verification is: {otp}

    This OTP is valid for 10 minutes.
    If you did not create an account, please ignore this email.
        """
    try:
        params: resend.Emails.SendParams = {
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": [email],
        "subject": "Verify your Afrivate Account",
        "html": f"<p>{message}</p>",
        }

        email = resend.Emails.send(params)
        logging.info(f"Signup OTP sent to {email}")
        return True
    
    except Exception as e:
        logging.error(f"Failed to send signup OTP to {email}: {e}")
        raise self.retry(exc=e)  # Celery will retry up to 3 times

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sendotp_via_email(self, email, otp, username="User"):
    """Send OTP to the specified email address""" 

    message = f"""
    Dear {username},

    You requested a password reset. 

    Your OTP is: {otp}

    This otp will expire in 10 minutes.
    If you didn't request this, please ignore this email.
        """
    
    try:
        params: resend.Emails.SendParams = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [email],
            "subject": "Password Reset OTP - Afrivate",
            "html": f"<p>{message}</p>",
        }
        response = resend.Emails.send(params)
        logging.info(f"Password reset OTP sent to {email}")  
        return True
    
    except Exception as e:
        logging.error(f"Failed to send password reset OTP to {email}: {e}")
        raise self.retry(exc=e)  
    
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, email, name="User"):
    """Send welcome email after email is verified"""

    message = f"""
    Dear {name},

    Your email has been verified. Welcome to Afrivate!
        """
    try:
        params: resend.Emails.SendParams = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [email],
            "subject": "Welcome to Afrivate!",
            "html": f"<p>{message}</p>",
        }

        response = resend.Emails.send(params)
        logging.info(f"Welcome email sent to {email}")
        return True
    
    except Exception as e:
        logging.error(f"Failed to send welcome email to {email}: {e}")
        raise self.retry(exc=e)  