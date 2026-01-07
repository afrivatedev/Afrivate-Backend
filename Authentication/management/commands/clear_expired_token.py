from django.core.management.base import BaseCommand
from django.utils import timezone
from user_database.models import EmailVerification

class Command(BaseCommand):
    help = 'Deletes expired email verification tokens from the database'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        # Find tokens that are expired AND haven't been verified
        expired_tokens = EmailVerification.objects.filter(
            expires_at__lt=now, 
            is_verified=False
        )
        
        count = expired_tokens.count()
        expired_tokens.delete()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {count} expired verification tokens')
        )