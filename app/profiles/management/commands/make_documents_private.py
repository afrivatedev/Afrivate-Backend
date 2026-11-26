"""
Move documents uploaded before the privacy fix from public to private storage.

Affected files: credentials (ID documents, certificates) and application
resumes (CVs). They were uploaded as public Cloudinary assets, so anyone with
the address can open them.

For each file, in order:
  1. Confirm the public copy exists (if it does not, the file is already
     private or missing, so skip it).
  2. Upload the same bytes as a private ('authenticated') asset under the same name.
  3. Confirm the private copy can be fetched with a signed link.
  4. Only then delete the public copy.

Dry run by default. Nothing changes unless --apply is given.
Run it once after the deploy, and keep the output.
"""
import logging

import cloudinary.uploader
import cloudinary.utils
import requests
from django.core.management.base import BaseCommand

from Afrivate.private_files import PRIVATE_ASSET_TYPE, signed_private_url
from applications.models import Application
from profiles.models import Credential

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30


def public_url_for(name):
    url, _ = cloudinary.utils.cloudinary_url(
        name, resource_type='raw', type='upload', secure=True)
    return url


def _exists_at(url):
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        logger.warning("Could not reach %s: %s", url, exc)
        return None
    return response


def move_one(name, apply_changes):
    """Return one of: 'moved', 'would-move', 'not-public', 'kept-public', 'error'."""
    public = _exists_at(public_url_for(name))
    if public is None:
        return 'error'
    if public.status_code != 200:
        # Not reachable at the public address: already private, or the file is missing.
        return 'not-public'
    if not apply_changes:
        return 'would-move'

    try:
        cloudinary.uploader.upload(
            public.content,
            public_id=name,
            resource_type='raw',
            type=PRIVATE_ASSET_TYPE,
            overwrite=True,
            invalidate=True,
        )
    except Exception as exc:
        logger.error("Upload of private copy of %s failed: %s", name, exc)
        return 'error'

    private = _exists_at(signed_private_url(name))
    if private is None or private.status_code != 200:
        # Do not delete the public copy unless the private one is verified.
        logger.error("Private copy of %s could not be verified; public copy kept.", name)
        return 'kept-public'

    try:
        cloudinary.uploader.destroy(name, resource_type='raw', type='upload', invalidate=True)
    except Exception as exc:
        logger.error("Delete of public copy of %s failed: %s", name, exc)
        return 'error'
    return 'moved'


class Command(BaseCommand):
    help = "Move legacy public documents (credentials and resumes) to private storage. Dry run unless --apply."

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help="Actually move the files. Without this flag, nothing is changed.")

    def handle(self, *args, **options):
        apply_changes = options['apply']
        mode = 'APPLY' if apply_changes else 'DRY RUN'
        self.stdout.write(f"[{mode}] Checking legacy documents...")

        targets = [
            ('credential', Credential.objects.exclude(document=''), 'document'),
            ('resume', Application.objects.exclude(resume__isnull=True).exclude(resume=''), 'resume'),
        ]

        counts = {}
        for label, queryset, field in targets:
            for obj in queryset.iterator():
                name = getattr(obj, field).name
                outcome = move_one(name, apply_changes)
                counts[outcome] = counts.get(outcome, 0) + 1
                self.stdout.write(f"  {label} #{obj.pk}: {outcome} ({name})")

        self.stdout.write(self.style.SUCCESS(f"[{mode}] Done. Summary: {counts}"))
