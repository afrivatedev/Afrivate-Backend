"""
Upload validation for organization documents.

No existing validator in the codebase handles non-image documents —
profiles.serializers.ProfilePictureSerializer.validate_profile_pic only
covers profile pictures. This follows the same size/format-check shape
but is generalized across image, video, and PDF certificates.
"""

import os

from django.conf import settings
from PIL import Image
from rest_framework import serializers

from .models import OrganizationDocument

IMAGE_ONLY_DOCUMENT_TYPES = {
    OrganizationDocument.DocumentType.PROOF_OF_WORK_PHOTO,
}
VIDEO_DOCUMENT_TYPES = {
    OrganizationDocument.DocumentType.PROOF_OF_WORK_VIDEO,
}
# Letterheads and recognition letters (an LGA/school/community-leader letter,
# per PRD 5.2) are as often issued as scanned PDFs as they are photographed —
# same real-world shape as the CAC/SCUML certificates, so all four accept
# either format rather than forcing an image-only upload.
FLEXIBLE_DOCUMENT_TYPES = {
    OrganizationDocument.DocumentType.CAC_CERTIFICATE,
    OrganizationDocument.DocumentType.SCUML_CERTIFICATE,
    OrganizationDocument.DocumentType.LETTERHEAD,
    OrganizationDocument.DocumentType.RECOGNITION_LETTER,
}

ALLOWED_IMAGE_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4"}
ALLOWED_FLEXIBLE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def validate_org_document(file, document_type):
    """Enforce size and type limits for an OrganizationDocument upload.

    Raises serializers.ValidationError on failure; returns the file unchanged
    on success so callers can use it directly as a serializer field validator.
    """
    max_mb = getattr(settings, "MAX_ORG_DOCUMENT_MB", 10)
    max_bytes = max_mb * 1024 * 1024
    size = getattr(file, "size", None)
    if size is not None and size > max_bytes:
        raise serializers.ValidationError(f"File too large. Max size is {max_mb} MB.")

    ext = os.path.splitext(getattr(file, "name", ""))[1].lower()

    if document_type in IMAGE_ONLY_DOCUMENT_TYPES:
        try:
            img = Image.open(file)
            img.verify()
        except (Image.UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise serializers.ValidationError("Upload a valid image file.")
        finally:
            if hasattr(file, "seek"):
                try:
                    file.seek(0)
                except Exception:
                    pass
        fmt = getattr(img, "format", "").upper()
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError(
                f"Unsupported image format: {fmt}. Allowed: {', '.join(sorted(ALLOWED_IMAGE_FORMATS))}."
            )

    elif document_type in VIDEO_DOCUMENT_TYPES:
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported video format. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}."
            )

    elif document_type in FLEXIBLE_DOCUMENT_TYPES:
        if ext not in ALLOWED_FLEXIBLE_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file format. Allowed: {', '.join(sorted(ALLOWED_FLEXIBLE_EXTENSIONS))}."
            )

    return file


def validate_appointment_letter(file):
    """Enforce the same size/format rules as an org's flexible documents
    (letterhead, recognition letter) on a representative's appointment letter
    — previously this upload had no server-side validation at all.
    """
    max_mb = getattr(settings, "MAX_ORG_DOCUMENT_MB", 10)
    max_bytes = max_mb * 1024 * 1024
    size = getattr(file, "size", None)
    if size is not None and size > max_bytes:
        raise serializers.ValidationError(f"File too large. Max size is {max_mb} MB.")

    ext = os.path.splitext(getattr(file, "name", ""))[1].lower()
    if ext not in ALLOWED_FLEXIBLE_EXTENSIONS:
        raise serializers.ValidationError(
            f"Unsupported file format. Allowed: {', '.join(sorted(ALLOWED_FLEXIBLE_EXTENSIONS))}."
        )
    return file
