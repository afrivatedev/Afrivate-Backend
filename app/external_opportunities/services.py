import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from opportunities.models import Opportunity

from .sources import SCRAPERS

logger = logging.getLogger(__name__)


def save_listing(listing):
    """Upsert one scraped listing as an Opportunity. Returns True when it was newly created."""
    now = timezone.now()
    defaults = {
        'title': listing.title,
        'opportunity_type': listing.opportunity_type,
        'description': listing.description,
        'link': listing.apply_url,
        'organization_name': listing.organization_name,
        'location': listing.location,
        'is_remote': listing.is_remote,
        'deadline': listing.deadline,
        'field': listing.field,
        'is_open': True,
        'last_seen_at': now,
    }
    # posted_at is only set on creation so a re-scrape never moves a listing's date.
    create_defaults = {**defaults, 'first_scraped_at': now, 'posted_at': listing.posted_at or now}
    try:
        with transaction.atomic():
            _, created = Opportunity.objects.update_or_create(
                source=listing.source,
                external_id=listing.external_id,
                defaults=defaults,
                create_defaults=create_defaults,
            )
    except IntegrityError:
        # Another listing already uses this (title, link); skip it rather than abort the whole run.
        logger.warning('Skipped duplicate scraped listing %s/%s', listing.source, listing.external_id)
        return False
    return created


def run_scraper(scraper):
    """Save everything one scraper returns and close what it no longer lists."""
    started = timezone.now()
    created = seen = 0
    try:
        for listing in scraper.fetch():
            seen += 1
            created += save_listing(listing)
    except Exception:
        # One broken source must not stop the others, and we must not
        # close listings when the fetch was incomplete.
        logger.exception('Scraper %s failed', scraper.name)
        return {'source': scraper.name, 'seen': seen, 'created': created, 'error': True}

    # Only close after a complete run that returned something.
    if seen and scraper.deactivate_missing:
        Opportunity.objects.filter(
            source=scraper.name, is_open=True, last_seen_at__lt=started
        ).update(is_open=False)
    if scraper.max_age_days:
        Opportunity.objects.filter(
            source=scraper.name, is_open=True,
            first_scraped_at__lt=started - timedelta(days=scraper.max_age_days),
        ).update(is_open=False)
    return {'source': scraper.name, 'seen': seen, 'created': created, 'error': False}


def deactivate_expired():
    return Opportunity.objects.exclude(source='').filter(
        is_open=True, deadline__isnull=False, deadline__lt=timezone.now()
    ).update(is_open=False)


def run_all_scrapers():
    results = [run_scraper(cls()) for cls in SCRAPERS]
    expired = deactivate_expired()
    logger.info('External opportunity scrape finished: %s, expired=%s', results, expired)
    return {'results': results, 'expired': expired}
