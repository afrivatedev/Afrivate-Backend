from rest_framework.views import exception_handler
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        view_name = context['view'].__class__.__name__

        if response.status_code == 400:
            logger.warning(f"❌ SERIALIZER ERROR at {view_name}: {response.data}")

        elif response.status_code == 401:
            logger.warning(f"🔒 UNAUTHORIZED at {view_name}: {response.data}")

        elif response.status_code == 403:
            logger.warning(f"⛔ FORBIDDEN at {view_name}: {response.data}")

        elif response.status_code == 404:
            logger.info(f"🔍 NOT FOUND at {view_name}: {response.data}")

        elif response.status_code >= 500:
            logger.error(f"🔥 SERVER ERROR at {view_name}: {response.data}", exc_info=exc)

    return response