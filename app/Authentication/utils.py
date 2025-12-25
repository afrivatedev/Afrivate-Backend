from datetime import timedelta
from django.utils import timezone
import logging

from user_database.models import CustomUser

from django.core.mail import send_mail # , EmailMessage
from django.conf import settings

import random

from django.conf import settings
from django.urls import reverse
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To # , Content


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

def send_waitlist_verification_email(request, token, email):
    """Send verification email using SendGrid"""
 
    # Build VERIFICATION URL
    verification_url = request.build_absolute_uri(
            reverse('accounts:verify-email') + f'?token={token}'
        )
    logging.info(f"Verification URL for {email}: {verification_url}")

    html_content=f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Welcome to Afrivate!</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Verify Your Email Address</h2>
                
                <p>Thank you for joining the Afrivate waitlist! We're excited to have you on board.</p>
                
                <p>Please click the button below to verify your email address and secure your spot:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 40px; 
                              text-decoration: none; 
                              border-radius: 5px; 
                              font-weight: bold;
                              display: inline-block;">
                        Verify Email
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    Or copy and paste this link into your browser:<br>
                    <a href="{verification_url}" style="color: #667eea; word-break: break-all;">{verification_url}</a>
                </p>
                
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    This link will expire in 30 minutes. If you didn't request this, please ignore this email.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>&copy; 2024 Afrivate Tech. All rights reserved.</p>
            </div>
        </body>
        </html>
        '''
    
    subject='Verify Your Email - Afrivate Waitlist'
    try:
        message = Mail(
        from_email=Email(settings.DEFAULT_FROM_EMAIL, 'Afrivate Tech'),
        to_emails=To(email),
        subject=subject,
        html_content=html_content)

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
