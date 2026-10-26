import html
import logging
import re

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from ..classifier import classify_field, is_remote, is_volunteer
from .base import BaseScraper, ScrapedListing

logger = logging.getLogger(__name__)

PREVIEW_URL = 'https://t.me/s/{channel}'
REQUEST_TIMEOUT = 20
URL_PATTERN = re.compile(r'https?://[^\s)\]>"<]+')
MESSAGE_SPLIT = re.compile(r'(?=<div class="tgme_widget_message_wrap)')
POST_ID = re.compile(r'data-post="([^"]+)"')
TEXT_BLOCK = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S
)
DATETIME = re.compile(r'<time[^>]*datetime="([^"]+)"')
TAG = re.compile(r'<[^>]+>')
BREAK = re.compile(r'<br\s*/?>', re.I)


def _plain_text(fragment):
    return html.unescape(TAG.sub('', BREAK.sub('\n', fragment))).strip()


class TelegramScraper(BaseScraper):
    """
    Reads the public web preview (t.me/s/<channel>) of the channels listed in
    settings.TELEGRAM_CHANNELS. Only public channels have a preview. Content
    belongs to the channel owners, so we keep the link back to the message.

    The preview shows only the latest ~20 messages, so older listings must not
    be deactivated just because they dropped out of it (see max_age_days).
    """
    name = 'telegram'
    deactivate_missing = False
    max_age_days = 30

    def __init__(self, channels=None):
        self.channels = settings.TELEGRAM_CHANNELS if channels is None else channels

    def fetch(self):
        if not self.channels:
            logger.warning('TELEGRAM_CHANNELS is not set; skipping Telegram.')
            return

        for channel in self.channels:
            try:
                response = requests.get(
                    PREVIEW_URL.format(channel=channel),
                    headers={'User-Agent': 'Afrivate/1.0 (+https://afrivate.com)'},
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
            except requests.RequestException:
                logger.exception('Telegram request failed for %s', channel)
                continue

            for block in MESSAGE_SPLIT.split(response.text):
                try:
                    listing = self._to_listing(channel, block)
                except Exception:
                    logger.exception('Could not parse a Telegram message from %s', channel)
                    continue
                if listing:
                    yield listing

    def _to_listing(self, channel, block):
        post = POST_ID.search(block)
        text_match = TEXT_BLOCK.search(block)
        if not post or not text_match:
            return None

        text = _plain_text(text_match.group(1))
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None
        title = lines[0]

        if not is_volunteer(text):
            return None
        field = classify_field(title, '', text)
        if not field:
            return None

        message_url = f'https://t.me/{post.group(1)}'
        links = [u for u in URL_PATTERN.findall(text) if 't.me/' not in u]
        posted = DATETIME.search(block)

        return ScrapedListing(
            source=self.name,
            external_id=post.group(1),
            title=title[:255],
            organization_name=channel,
            description=text,
            apply_url=links[0] if links else message_url,
            source_url=message_url,
            field=field,
            location='Nigeria',
            is_remote=is_remote(text),
            posted_at=parse_datetime(posted.group(1)) if posted else None,
        )
