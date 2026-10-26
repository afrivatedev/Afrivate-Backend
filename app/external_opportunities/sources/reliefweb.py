import logging
import re

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from ..classifier import classify_field, is_remote, is_volunteer
from .base import BaseScraper, ScrapedListing

logger = logging.getLogger(__name__)

API_URL = 'https://api.reliefweb.int/v2/jobs'
PAGE_SIZE = 100
MAX_PAGES = 5  # 500 listings per run; the API quota is 1000 calls/day
REQUEST_TIMEOUT = 20
URL_PATTERN = re.compile(r'https?://[^\s)\]>"]+')

FIELDS = [
    'title', 'body', 'how_to_apply', 'url', 'date.created', 'date.closing',
    'source.name', 'career_categories.name', 'type.name', 'country.name', 'city.name',
]


class ReliefWebScraper(BaseScraper):
    """
    Uses the official ReliefWeb API (https://apidoc.reliefweb.int/).
    Requires a pre-approved appname in settings.RELIEFWEB_APPNAME.
    Content belongs to the original organizations, so we always keep the
    link back to the listing (`source_url`) and the organization name.
    """
    name = 'reliefweb'

    def __init__(self, appname=None):
        self.appname = appname or settings.RELIEFWEB_APPNAME

    def _request(self, offset):
        payload = {
            'query': {'value': 'volunteer OR "pro bono" OR unpaid', 'operator': 'OR'},
            'filter': {'field': 'status', 'value': 'published'},
            'fields': {'include': FIELDS},
            'sort': ['date.created:desc'],
            'limit': PAGE_SIZE,
            'offset': offset,
        }
        response = requests.post(
            API_URL,
            params={'appname': self.appname},
            json=payload,
            headers={'User-Agent': 'Afrivate/1.0 (+https://afrivate.com)'},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get('data', [])

    def fetch(self):
        if not self.appname:
            logger.warning('RELIEFWEB_APPNAME is not set; skipping ReliefWeb.')
            return

        for page in range(MAX_PAGES):
            try:
                items = self._request(page * PAGE_SIZE)
            except requests.RequestException:
                logger.exception('ReliefWeb request failed (page %s)', page)
                return
            if not items:
                return

            for item in items:
                try:
                    listing = self._to_listing(item)
                except Exception:
                    logger.exception('Could not parse ReliefWeb item %s', item.get('id'))
                    continue
                if listing:
                    yield listing

            if len(items) < PAGE_SIZE:
                return

    def _to_listing(self, item):
        f = item.get('fields', {})
        title = f.get('title', '')
        body = f.get('body', '')
        how_to_apply = f.get('how_to_apply', '')
        type_name = ', '.join(t.get('name', '') for t in f.get('type', []))
        city = ', '.join(c.get('name', '') for c in f.get('city', []) if c.get('name'))
        country = ', '.join(c.get('name', '') for c in f.get('country', []) if c.get('name'))
        categories = ', '.join(c.get('name', '') for c in f.get('career_categories', []))

        # Keep only remote volunteer roles inside our three fields.
        if not is_volunteer(type_name, title, body):
            return None
        if not is_remote(title, city, body):
            return None
        field = classify_field(title, categories, body)
        if not field:
            return None

        source = f.get('source') or [{}]
        source_url = f.get('url', '')
        apply_match = URL_PATTERN.search(how_to_apply)

        return ScrapedListing(
            source=self.name,
            external_id=str(item['id']),
            title=title[:255],
            organization_name=(source[0].get('name') or '')[:255],
            description=body,
            apply_url=apply_match.group(0) if apply_match else source_url,
            source_url=source_url,
            field=field,
            location=', '.join(p for p in (city, country) if p)[:255],
            is_remote=True,
            deadline=parse_datetime((f.get('date') or {}).get('closing', '') or '') or None,
            posted_at=parse_datetime((f.get('date') or {}).get('created', '') or '') or None,
        )
