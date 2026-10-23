import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from user_database.models import CustomUser

from .classifier import classify_field, is_remote, is_volunteer
from .models import ExternalOpportunity
from .services import run_all_scrapers
from .sources.myjobmag import MyJobMagScraper
from .sources.reliefweb import ReliefWebScraper
from .sources.telegram import TelegramScraper

TEST_CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


def rw_item(id=1, title='Remote Volunteer Web Developer', body='Volunteer online, build our website.',
            city=None, **extra):
    fields = {
        'title': title,
        'body': body,
        'how_to_apply': 'Apply at https://ngo.example.org/apply now',
        'url': f'https://reliefweb.int/job/{id}',
        'date': {'created': '2026-10-01T00:00:00+00:00', 'closing': '2099-01-01T00:00:00+00:00'},
        'source': [{'name': 'Example NGO'}],
        'career_categories': [{'name': 'Information and Communications Technology'}],
        'type': [{'name': 'Volunteer'}],
        'country': [{'name': 'Nigeria'}],
        'city': city or [],
    }
    fields.update(extra)
    return {'id': str(id), 'fields': fields}


class ClassifierTests(SimpleTestCase):
    def test_classifies_fields(self):
        self.assertEqual(classify_field('Python Developer'), 'tech')
        self.assertEqual(classify_field('Social Media Volunteer'), 'marketing')
        self.assertEqual(classify_field('Fundraising Strategy Advisor'), 'business')

    def test_unrelated_returns_none(self):
        self.assertIsNone(classify_field('Hospital Cleaner', 'Health', 'Mop floors'))

    def test_volunteer_and_remote_detection(self):
        self.assertTrue(is_volunteer('Online Volunteer'))
        self.assertTrue(is_volunteer('', 'Pro bono designer'))
        self.assertFalse(is_volunteer('Paid Developer'))
        self.assertTrue(is_remote('Home-based role'))
        self.assertFalse(is_remote('Kabul office role'))


class ReliefWebScraperTests(SimpleTestCase):
    def _fetch(self, items):
        scraper = ReliefWebScraper(appname='test-app')
        with patch.object(ReliefWebScraper, '_request', side_effect=[items, []]):
            return list(scraper.fetch())

    def test_keeps_remote_volunteer_listing(self):
        listings = self._fetch([rw_item()])
        self.assertEqual(len(listings), 1)
        listing = listings[0]
        self.assertEqual(listing.field, 'tech')
        self.assertEqual(listing.apply_url, 'https://ngo.example.org/apply')
        self.assertEqual(listing.source_url, 'https://reliefweb.int/job/1')
        self.assertEqual(listing.organization_name, 'Example NGO')

    def test_skips_onsite_non_volunteer_and_off_topic(self):
        items = [
            rw_item(2, title='Volunteer Web Developer', body='Volunteer at our Kabul office.'),  # on-site
            rw_item(3, title='Remote Paid Developer', body='Online salaried job.', type=[{'name': 'Job'}]),
            rw_item(4, title='Remote Volunteer Cook', body='Cook online meals.',
                    career_categories=[{'name': 'Health'}]),  # no matching field
        ]
        self.assertEqual(self._fetch(items), [])

    def test_missing_appname_skips(self):
        self.assertEqual(list(ReliefWebScraper(appname='').fetch()), [])


def tg_message(post='ngjobs/10', text='Volunteer Python Developer needed<br/>Apply: https://forms.example.org/apply',
               when='2026-10-20T10:00:00+00:00'):
    return (
        f'<div class="tgme_widget_message_wrap js-widget_message_wrap">'
        f'<div class="tgme_widget_message" data-post="{post}">'
        f'<div class="tgme_widget_message_text js-message_text" dir="auto">{text}</div>'
        f'<a class="tgme_widget_message_date"><time datetime="{when}">10:00</time></a>'
        f'</div></div>'
    )


class TelegramScraperTests(SimpleTestCase):
    def _fetch(self, *messages, channels=('ngjobs',)):
        response = type('R', (), {'text': ''.join(messages), 'raise_for_status': lambda self: None})()
        with patch('external_opportunities.sources.telegram.requests.get', return_value=response):
            return list(TelegramScraper(channels=list(channels)).fetch())

    def test_keeps_volunteer_listing(self):
        (listing,) = self._fetch(tg_message())
        self.assertEqual(listing.external_id, 'ngjobs/10')
        self.assertEqual(listing.title, 'Volunteer Python Developer needed')
        self.assertEqual(listing.field, 'tech')
        self.assertEqual(listing.apply_url, 'https://forms.example.org/apply')
        self.assertEqual(listing.source_url, 'https://t.me/ngjobs/10')
        self.assertEqual(listing.location, 'Nigeria')

    def test_falls_back_to_message_link(self):
        (listing,) = self._fetch(tg_message(text='Volunteer web developer wanted, DM us'))
        self.assertEqual(listing.apply_url, 'https://t.me/ngjobs/10')

    def test_skips_non_volunteer_and_off_topic(self):
        self.assertEqual(self._fetch(
            tg_message('ngjobs/11', 'Paid software engineer role in Lagos'),
            tg_message('ngjobs/12', 'Volunteer cook needed for the shelter'),
        ), [])

    def test_no_channels_skips(self):
        self.assertEqual(list(TelegramScraper(channels=[]).fetch()), [])


def mjm_page(*paths):
    return ''.join(
        f'<li class="job-list-li"><ul><li class="job-info"><ul><li class="mag-b">'
        f'<h2><a href="{p}">Job</a></h2></li></ul></li></ul></li>' for p in paths
    )


def mjm_job(title='Data Analyst Intern', country='NG', locality='Lagos',
            description='<p>Analyse data with Python.</p>', valid='2099-11-04T00:00:00+0000'):
    posting = {
        '@type': 'JobPosting', 'title': title,
        'datePosted': '2026-10-23T12:57:55+01:00', 'validThrough': valid,
        'hiringOrganization': {'name': 'Example Ltd'},
        'occupationalCategory': 'Internships , IT',
        'jobLocation': {'address': {'addressLocality': locality, 'addressCountry': country}},
        'description': description,
    }
    return f'<script type="application/ld+json">{json.dumps(posting)}</script>'


class MyJobMagScraperTests(SimpleTestCase):
    def _fetch(self, pages, jobs):
        """pages: list-page HTML per request; jobs: {path: detail HTML}."""
        def get(self_, url):
            if '/job/' in url:
                return jobs[url.replace('https://www.myjobmag.com', '')]
            return pages.pop(0) if pages else ''
        with patch.object(MyJobMagScraper, '_get', get), \
                patch('external_opportunities.sources.myjobmag.time.sleep'):
            return list(MyJobMagScraper(max_pages=3).fetch())

    def test_parses_internship_listing(self):
        (listing,) = self._fetch([mjm_page('/job/data-intern-1')], {'/job/data-intern-1': mjm_job()})
        self.assertEqual(listing.source, 'myjobmag')
        self.assertEqual(listing.external_id, 'data-intern-1')
        self.assertEqual(listing.opportunity_type, 'internship')
        self.assertEqual(listing.field, 'tech')
        self.assertEqual(listing.organization_name, 'Example Ltd')
        self.assertEqual(listing.location, 'Lagos, Nigeria')
        self.assertEqual(listing.apply_url, 'https://www.myjobmag.com/job/data-intern-1')
        self.assertEqual(listing.description, 'Analyse data with Python.')
        self.assertEqual(listing.deadline.year, 2099)
        self.assertFalse(listing.is_remote)

    def test_follows_pagination_and_stops_on_empty_page(self):
        pages = [mjm_page('/job/a-1'), mjm_page('/job/b-2'), '']
        jobs = {'/job/a-1': mjm_job(), '/job/b-2': mjm_job()}
        self.assertEqual(len(self._fetch(pages, jobs)), 2)

    def test_skips_off_topic_and_foreign_onsite(self):
        pages = [mjm_page('/job/cook-1', '/job/ghana-2', '/job/ghana-remote-3')]
        jobs = {
            '/job/cook-1': mjm_job(title='Kitchen Assistant', description='<p>Wash dishes.</p>'),
            '/job/ghana-2': mjm_job(country='GH', locality='Accra'),
            '/job/ghana-remote-3': mjm_job(country='GH', locality='Accra', description='<p>Remote Python work.</p>'),
        }
        listings = self._fetch(pages, jobs)
        self.assertEqual([l.external_id for l in listings], ['ghana-remote-3'])
        self.assertTrue(listings[0].is_remote)

    def test_skips_page_without_job_posting(self):
        self.assertEqual(self._fetch([mjm_page('/job/x-1')], {'/job/x-1': '<html></html>'}), [])

    @override_settings(MYJOBMAG_ENABLED=False)
    def test_disabled_skips(self):
        self.assertEqual(list(MyJobMagScraper().fetch()), [])


@override_settings(CACHES=TEST_CACHES, MYJOBMAG_ENABLED=False)
class ServiceTests(TestCase):
    def _run(self, items):
        with patch.object(ReliefWebScraper, '_request', side_effect=[items, []]), \
                override_settings(RELIEFWEB_APPNAME='test-app'):
            return run_all_scrapers()

    def test_dedupes_on_rerun(self):
        self._run([rw_item()])
        self._run([rw_item(title='Remote Volunteer Web Developer (updated)')])
        self.assertEqual(ExternalOpportunity.objects.count(), 1)
        self.assertIn('updated', ExternalOpportunity.objects.get().title)

    def test_deactivates_listings_no_longer_returned(self):
        self._run([rw_item(1), rw_item(2)])
        self._run([rw_item(1)])
        self.assertTrue(ExternalOpportunity.objects.get(external_id='1').is_active)
        self.assertFalse(ExternalOpportunity.objects.get(external_id='2').is_active)

    def test_failed_fetch_does_not_deactivate(self):
        self._run([rw_item(1)])
        with patch.object(ReliefWebScraper, 'fetch', side_effect=RuntimeError('boom')):
            run_all_scrapers()
        self.assertTrue(ExternalOpportunity.objects.get().is_active)

    def test_telegram_listings_survive_leaving_the_preview_window(self):
        with override_settings(TELEGRAM_CHANNELS=['ngjobs']):
            response = type('R', (), {'text': tg_message(), 'raise_for_status': lambda self: None})()
            empty = type('R', (), {'text': '', 'raise_for_status': lambda self: None})()
            with patch('external_opportunities.sources.telegram.requests.get', side_effect=[response, empty]):
                run_all_scrapers()
                run_all_scrapers()
        self.assertTrue(ExternalOpportunity.objects.get(source='telegram').is_active)

    def test_old_telegram_listings_expire(self):
        ExternalOpportunity.objects.create(
            source='telegram', external_id='ngjobs/1', title='Old', apply_url='https://x.org', field='tech',
        )
        ExternalOpportunity.objects.update(first_scraped_at=timezone.now() - timedelta(days=31))
        with override_settings(TELEGRAM_CHANNELS=['ngjobs']):
            empty = type('R', (), {'text': '', 'raise_for_status': lambda self: None})()
            with patch('external_opportunities.sources.telegram.requests.get', return_value=empty):
                run_all_scrapers()
        self.assertFalse(ExternalOpportunity.objects.get().is_active)

    def test_expired_deadline_deactivated(self):
        self._run([rw_item(1, date={'created': '2026-01-01T00:00:00+00:00',
                                    'closing': (timezone.now() - timedelta(days=1)).isoformat()})])
        self.assertFalse(ExternalOpportunity.objects.get().is_active)


@override_settings(CACHES=TEST_CACHES)
class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = CustomUser.objects.create_user(
            username='u', email='u@example.com', password='Pass123!',
            role='pathfinder', is_email_verified=True,
        )
        self.client.force_authenticate(user=user)
        make = lambda i, field, active=True: ExternalOpportunity.objects.create(
            source='reliefweb', external_id=str(i), title=f'Role {i}', apply_url='https://x.org/a',
            field=field, is_active=active,
        )
        make(1, 'tech'); make(2, 'marketing'); make(3, 'tech', active=False)

    def test_lists_only_active(self):
        data = self.client.get(reverse('external-opportunity-list')).json()
        self.assertEqual(data['count'], 2)

    def test_filter_by_opportunity_type(self):
        ExternalOpportunity.objects.filter(external_id='1').update(opportunity_type='internship')
        data = self.client.get(
            reverse('external-opportunity-list'), {'opportunity_type': 'internship'}
        ).json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['opportunity_type'], 'internship')

    def test_filter_by_field(self):
        data = self.client.get(reverse('external-opportunity-list'), {'field': 'tech'}).json()
        self.assertEqual(data['count'], 1)

    def test_requires_auth(self):
        self.assertEqual(APIClient().get(reverse('external-opportunity-list')).status_code, 401)
