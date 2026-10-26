import html
import json
import logging
import re
import time

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from ..classifier import classify_field, is_remote
from opportunities.models import Opportunity
from .base import BaseScraper, ScrapedListing

logger = logging.getLogger(__name__)

CATEGORY_URL = 'https://www.myjobmag.com/jobs-by-field/internships-volunteering'
BASE_URL = 'https://www.myjobmag.com'
MAX_PAGES = 5  # ~18 listings per page
REQUEST_TIMEOUT = 20
REQUEST_DELAY = 2  # seconds between requests
USER_AGENT = 'Afrivate/1.0 (+https://afrivate.com)'

LIST_LINK = re.compile(r'<li class="job-list-li">.*?<h2>\s*<a\s+href="(/job/[^"]+)"', re.S)
JSON_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
LIST_ITEM_START = re.compile(r'<li[^>]*>', re.I)
BLOCK_END = re.compile(r'</(?:p|li|div|h\d|ul|ol)>|<br\s*/?>', re.I)
TAG = re.compile(r'<[^>]+>')
SPACES = re.compile(r'\s+')


def _plain_text(fragment):
    """HTML (entity-escaped in the JSON-LD) -> plain text, keeping paragraph and bullet breaks."""
    text = html.unescape(fragment or '')
    text = BLOCK_END.sub('\n', LIST_ITEM_START.sub('\n• ', text))
    text = html.unescape(TAG.sub(' ', text))
    lines = (SPACES.sub(' ', line).strip() for line in text.split('\n'))
    return '\n'.join(line for line in lines if line and line != '•')


class MyJobMagScraper(BaseScraper):
    """
    Scrapes MyJobMag's internship category (https://www.myjobmag.com).

    robots.txt blocks query-string searches, so only the clean category URL,
    its /2, /3 ... pagination and the /job/ detail pages are requested. Each
    detail page carries schema.org JobPosting JSON-LD, which we parse instead of
    relying on CSS selectors. Content belongs to the hiring organizations, so we
    keep the link back to the listing.
    """
    name = 'myjobmag'

    def __init__(self, max_pages=MAX_PAGES):
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT

    def _get(self, url):
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text

    def _job_paths(self):
        seen = set()
        for page in range(1, self.max_pages + 1):
            url = CATEGORY_URL if page == 1 else f'{CATEGORY_URL}/{page}'
            try:
                body = self._get(url)
            except requests.RequestException:
                logger.exception('MyJobMag list request failed (page %s)', page)
                return
            paths = [p for p in LIST_LINK.findall(body) if p not in seen]
            if not paths:
                return
            for path in paths:
                seen.add(path)
                yield path
            time.sleep(REQUEST_DELAY)

    def fetch(self):
        if not settings.MYJOBMAG_ENABLED:
            return

        for path in self._job_paths():
            url = BASE_URL + path
            try:
                listing = self._to_listing(url, path, self._get(url))
            except requests.RequestException:
                logger.exception('MyJobMag request failed for %s', url)
                continue
            except Exception:
                logger.exception('Could not parse MyJobMag listing %s', url)
                continue
            finally:
                time.sleep(REQUEST_DELAY)
            if listing:
                yield listing

    @staticmethod
    def _job_posting(body):
        for raw in JSON_LD.findall(body):
            try:
                data = json.loads(raw, strict=False)  # descriptions contain raw newlines
            except ValueError:
                continue
            if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                return data
        return None

    def _to_listing(self, url, path, body):
        posting = self._job_posting(body)
        if not posting:
            return None

        title = posting.get('title') or ''
        description = _plain_text(posting.get('description'))
        address = (posting.get('jobLocation') or {}).get('address') or {}
        locality = address.get('addressLocality') or ''
        categories = posting.get('occupationalCategory') or ''
        remote = is_remote(title, locality, description)

        # Nigeria, or remote roles that Nigerians can take from anywhere.
        country = address.get('addressCountry') or ''
        if country and country != 'NG' and not remote:
            return None
        field = classify_field(title, categories, description)
        if not field:
            return None

        return ScrapedListing(
            source=self.name,
            external_id=path.rsplit('/', 1)[-1],
            title=title[:255],
            organization_name=((posting.get('hiringOrganization') or {}).get('name') or '')[:255],
            description=description,
            apply_url=url,
            source_url=url,
            field=field,
            opportunity_type=Opportunity.Category.INTERNSHIP,
            location=', '.join(p for p in (locality, 'Nigeria') if p)[:255],
            is_remote=remote,
            deadline=parse_datetime(self._iso(posting.get('validThrough'))),
            posted_at=parse_datetime(self._iso(posting.get('datePosted'))),
        )

    @staticmethod
    def _iso(value):
        """'2026-11-04T00:00:00+0000' -> '2026-11-04T00:00:00+00:00' for parse_datetime."""
        return re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', value or '')
