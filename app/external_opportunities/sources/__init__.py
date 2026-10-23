from .myjobmag import MyJobMagScraper
from .reliefweb import ReliefWebScraper
from .telegram import TelegramScraper

# Register new scrapers here.
SCRAPERS = [ReliefWebScraper, TelegramScraper, MyJobMagScraper]
