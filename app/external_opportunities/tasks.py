from celery import shared_task

from .services import run_all_scrapers


@shared_task
def scrape_external_opportunities():
    return run_all_scrapers()
