"""
Private Cloudinary storage for organization verification documents.

django-cloudinary-storage's RawMediaCloudinaryStorage always uploads under
Cloudinary's public 'upload' delivery type (see its _upload()) — there is no
built-in private option in the installed version, despite a commented-out
`tag_options={'type': 'private'}` in profiles/models.py suggesting otherwise
(that kwarg doesn't exist on the storage class and was never actually
exercised). This subclass instead uploads as Cloudinary's 'authenticated'
delivery type, which is not reachable by a guessed/public URL — only via a
signed URL requested with the same type (see serializers.SignedPrivateFileField).
"""

import os

import cloudinary
import cloudinary.uploader
from cloudinary_storage.storage import RawMediaCloudinaryStorage

PRIVATE_DELIVERY_TYPE = 'authenticated'


class PrivateRawMediaCloudinaryStorage(RawMediaCloudinaryStorage):
    def _upload(self, name, content):
        options = {
            'use_filename': True,
            'resource_type': self._get_resource_type(name),
            'tags': self.TAG,
            'type': PRIVATE_DELIVERY_TYPE,
        }
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        return cloudinary.uploader.upload(content, **options)

    def delete(self, name):
        response = cloudinary.uploader.destroy(
            name, invalidate=True, resource_type=self._get_resource_type(name), type=PRIVATE_DELIVERY_TYPE
        )
        return response['result'] == 'ok'

    def _get_url(self, name):
        name = self._prepend_prefix(name)
        cloudinary_resource = cloudinary.CloudinaryResource(
            name, default_resource_type=self._get_resource_type(name), type=PRIVATE_DELIVERY_TYPE
        )
        return cloudinary_resource.url
