from rest_framework import serializers

from .utils import is_allowed_domain, is_blacklisted_domain, matches_bad_pattern
from .models import WaitlistEmail
from user_database.models import EmailVerification

from email_validator import validate_email as validate_email_lib, EmailNotValidError

from django.db import transaction
    
class WaitlistEmailSerializer(serializers.ModelSerializer):
    
    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email address is required")
        
        email = value.lower().strip()
        try:
            # Validate email format and deliverability
            v = validate_email_lib(email, check_deliverability=True)
            domain = v.domain
            normalized_email = v.normalized

            # Check blacklisted domains
            if is_blacklisted_domain(domain):
                raise serializers.ValidationError("Disposable email domains are not allowed")

            # Check for suspicious patterns
            if matches_bad_pattern(normalized_email):
                raise serializers.ValidationError("Suspicious email pattern detected")
            
            # Check allowed domains
            if not is_allowed_domain(domain):
                raise serializers.ValidationError("This email domain is not allowed")

            # Return the normalized email
            return normalized_email

        except EmailNotValidError as e:
            raise serializers.ValidationError(f"Invalid email: {str(e)}")
        
    class Meta:
        model = WaitlistEmail
        fields = ['email', 'name']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'email': {'required': True}
        }

    def create(self, validated_data):
        email = validated_data['email']
        name = validated_data.get('name') or ''

        # Using atomic to ensure both records are actually created together
        with transaction.atomic():

            # Get or Create the waitlist entry
            waitlist_entry, created = WaitlistEmail.objects.get_or_create(
            email=email,
            defaults={'name': name}
            )

            # # if User is already verified
            # if waitlist_entry.is_verified:
            #     raise serializers.ValidationError({"email": "This email is already on the waitlist!"})
            
            # # if User exists but is NOT verified (or maybe new self)
            # EmailVerification.objects.filter(email=email, is_verified=False).delete()

            # Create the Verification Token 
            verification = EmailVerification.create_verification(
                email=email,
                verification_type='waitlist'
            )

            # now attach verification to the waitlist entry
            waitlist_entry.verification = verification
            waitlist_entry.save()

            return waitlist_entry


# waitlisrt stats serializer
'''
    total_signups
    signups_today 
    signups_this_week 
    signups_this_month
'''

class WaitlistStatsSerializer(serializers.Serializer):
    """Serializer for waitlist statistics"""
    total_signups = serializers.IntegerField()
    verified_signups = serializers.IntegerField()
    signups_today = serializers.IntegerField()
    signups_this_week = serializers.IntegerField()
    signups_this_month = serializers.IntegerField()
    
    def get_stats(self):
        """Calculate waitlist statistics"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        total = WaitlistEmail.objects.count()
        verified = WaitlistEmail.objects.filter(is_verified=True).count()
        today = WaitlistEmail.objects.filter(created_at__gte=today_start).count()
        week = WaitlistEmail.objects.filter(created_at__gte=week_start).count()
        month = WaitlistEmail.objects.filter(created_at__gte=month_start).count()
        
        return {
            'total_signups': total,
            'verified_signups': verified,
            'signups_today': today,
            'signups_this_week': week,
            'signups_this_month': month
        }
    
