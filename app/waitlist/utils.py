from django.conf import settings
from django.urls import reverse

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To # , Content

import logging
import re

logger = logging.getLogger(__name__)

from Afrivate.settings import ALLOWED_DOMAINS, BLACKLISTED_DOMAINS, BAD_PATTERNS

def send_waitlist_verification_email(request, token, email):
    """Send verification email using SendGrid"""
 
    # Build VERIFICATION URL
    verification_url = request.build_absolute_uri(
            reverse('accounts:verify-email') + f'?token={token}'
        )
    logging.info(f"Verification URL for {email}: {verification_url}")

    # verification_url = f"{settings.FRONTEND_URL}/verify-email/?token={token}"
    
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
                    This link will expire in 20 minutes. If you didn't request this, please ignore this email.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>&copy; 2026 Afrivate Tech. All rights reserved.</p>
            </div>
        </body>
        </html>
        '''
    
    subject='Welcome  - Afrivate Waitlist'
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
        logger.error(f"SendGrid Error for {email}: {str(e)}")
        return False

def send_welcome_email(email, name):
    """Send welcome email to new waitlist user using SendGrid"""
    subject = 'Welcome to Afrivate!'

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
                <h2 style="color: #333; margin-top: 0;">Welcome to Afrivate!</h2>
                
                <p>Thank you for joining the Afrivate Volunteer Module waitlist. We’re excited to have you with us.</p>
                <p>By joining the waitlist, you’ve taken the first step toward gaining real-world experience, building practical skills, and contributing meaningfully to projects that drive Africa forward.</p>
                <p>Here’s what happens next:</p>
                <ul>
                    <li>You’ll be among the first to get access when the Volunteer Module launches</li>
                    <li>We’ll share important updates, timelines, and next steps directly with you</li>
                    <li>You’ll receive early information on how to get started and what to expect</li>
                </ul>

                <p>Afrivate isn’t just about volunteering, it’s about growth, clarity, and community. We’re intentional about building opportunities that help you learn by doing and stand out professionally.</p>
                <p>We’ll be in touch soon. Welcome to the journey!</p>
                <p>— The Afrivate Team</p>
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>&copy; 2026 Afrivate Tech. All rights reserved.</p>
            </div>
        </body>

        </html>
        '''

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
            logging.info(f"Welcome email sent successfully to {email}")
            return True
        else:
            logging.warning(f"SendGrid returned status {response.status_code} for {email}")
            return False
        
    except Exception as e:
        logger.error(f"SendGrid Error for {email}: {str(e)}")
        return False

def matches_bad_pattern(email: str) -> bool:
    return any(re.search(p, email.lower()) for p in BAD_PATTERNS)

def is_allowed_domain(domain: str) -> bool:
    return domain.lower() in ALLOWED_DOMAINS

def is_blacklisted_domain(domain: str) -> bool:
    return domain.lower() in BLACKLISTED_DOMAINS

