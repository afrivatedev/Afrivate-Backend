"""
Private storage for personal documents: ID documents, credentials and CVs/resumes.

Files are uploaded to Cloudinary as 'authenticated' assets. Cloudinary does not
serve those to anyone who has the plain address. Access is only given through a
signed link that expires after a few minutes, and only when an authorised user
asks for the record (see the serializers).
"""
import os
import time

import cloudinary.utils
import cloudinary.uploader
from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.utils.deconstruct import deconstructible

PRIVATE_ASSET_TYPE = 'authenticated'
# How long a document link stays valid. Long enough to open a PDF, short enough
# that a copied link stops working soon after.
PRIVATE_LINK_TTL_SECONDS = 300


def signed_private_url(public_id, ttl_seconds=PRIVATE_LINK_TTL_SECONDS):
    """Return a signed Cloudinary download link for a private raw file.

    The link carries an expiry timestamp and a signature made with the API
    secret. It stops working once the expiry passes.
    """
    if not public_id:
        return None
    expires_at = int(time.time()) + int(ttl_seconds)
    return cloudinary.utils.private_download_url(
        public_id,
        None,
        resource_type='raw',
        type=PRIVATE_ASSET_TYPE,
        expires_at=expires_at,
    )


@deconstructible
class PrivateRawMediaCloudinaryStorage(RawMediaCloudinaryStorage):
    """Raw file storage that keeps uploads private.

    - Uploads are stored as 'authenticated' assets.
    - url() returns a signed link that expires, never the open public address.
    - delete() targets the private asset.
    """

    def _upload(self, name, content):
        options = {
            'use_filename': True,
            'resource_type': self._get_resource_type(name),
            'tags': self.TAG,
            'type': PRIVATE_ASSET_TYPE,
        }
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        return cloudinary.uploader.upload(content, **options)

    def delete(self, name):
        response = cloudinary.uploader.destroy(
            name,
            invalidate=True,
            resource_type=self._get_resource_type(name),
            type=PRIVATE_ASSET_TYPE,
        )
        return response.get('result') == 'ok'

    def url(self, name):
        return signed_private_url(self._prepend_prefix(name))
