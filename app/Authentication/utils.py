import logging
from django.core.mail import send_mail # , EmailMessage
from django.conf import settings

import resend

resend.api_key = settings.RESEND_API_KEY

def send_signup_otp_email(email, otp, username="User"):
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
        return False
    
# hey let's use RESEND for all our email sending needs

# send email then receive otp input and verify 
def sendotp_via_email(email, otp, username="User"):
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
        email = resend.Emails.send(params)
        logging.info(f"Password reset OTP sent to {email}")  
        return True
    
    except Exception as e:
        logging.error(f"Failed to send password reset OTP to {email}: {e}")
        return False
    

# Send a confirmation email once verification is there


def send_welcome_email(email, name="User"):
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

        email = resend.Emails.send(params)
        logging.info(f"Welcome email sent to {email}")
        return True
    
    except Exception as e:
        logging.error(f"Failed to send welcome email to {email}: {e}")
        return False