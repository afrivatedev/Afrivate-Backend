import logging
from datetime import timedelta

from django.utils import timezone

from .models import ExternalOpportunity
from .sources import SCRAPERS

logger = logging.getLogger(__name__)


def save_listing(listing):
    obj, created = ExternalOpportunity.objects.update_or_create(
        source=listing.source,
        external_id=listing.external_id,
        defaults={
            'title': listing.title,
            'organization_name': listing.organization_name,
            'description': listing.description,
            'apply_url': listing.apply_url,
            'source_url': listing.source_url,
            'field': listing.field,
            'opportunity_type': listing.opportunity_type,
            'location': listing.location,
            'is_remote': listing.is_remote,
            'deadline': listing.deadline,
            'posted_at': listing.posted_at,
            'is_active': True,
        },
    )
    return created


def run_scraper(scraper):
    """Save everything one scraper returns and deactivate what it no longer lists."""
    started = timezone.now()
    created = seen = 0
    try:
        for listing in scraper.fetch():
            seen += 1
            created += save_listing(listing)
    except Exception:
        # One broken source must not stop the others, and we must not
        # deactivate listings when the fetch was incomplete.
        logger.exception('Scraper %s failed', scraper.name)
        return {'source': scraper.name, 'seen': seen, 'created': created, 'error': True}

    # Only deactivate after a complete run that returned something.
    if seen and scraper.deactivate_missing:
        ExternalOpportunity.objects.filter(
            source=scraper.name, is_active=True, last_seen_at__lt=started
        ).update(is_active=False)
    if scraper.max_age_days:
        ExternalOpportunity.objects.filter(
            source=scraper.name, is_active=True,
            first_scraped_at__lt=started - timedelta(days=scraper.max_age_days),
        ).update(is_active=False)
    return {'source': scraper.name, 'seen': seen, 'created': created, 'error': False}


def deactivate_expired():
    return ExternalOpportunity.objects.filter(
        is_active=True, deadline__isnull=False, deadline__lt=timezone.now()
    ).update(is_active=False)


def run_all_scrapers():
    results = [run_scraper(cls()) for cls in SCRAPERS]
    expired = deactivate_expired()
    logger.info('External opportunity scrape finished: %s, expired=%s', results, expired)
    return {'results': results, 'expired': expired}
