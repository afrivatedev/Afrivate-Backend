from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ScrapedListing:
    """Source-agnostic shape every scraper returns."""
    source: str
    external_id: str
    title: str
    apply_url: str
    field: str
    opportunity_type: str = 'volunteering'  # an opportunities.Opportunity.Category value
    organization_name: str = ''
    description: str = ''
    source_url: str = ''
    location: str = ''
    is_remote: bool = True
    deadline: Optional[datetime] = None
    posted_at: Optional[datetime] = None


class BaseScraper:
    name = ''
    # Sources that only expose a recent window (e.g. a chat preview) set this to
    # False so listings that scrolled out of the window stay active...
    deactivate_missing = True
    # ...and instead expire this many days after they were first scraped.
    max_age_days = None

    def fetch(self):
        """Return an iterable of ScrapedListing. Must not raise for a single bad item."""
        raise NotImplementedError
