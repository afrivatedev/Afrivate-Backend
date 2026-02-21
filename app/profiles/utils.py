from rest_framework.views import exception_handler
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    # If a 400 error occurs, log the specific details
    if response is not None and response.status_code == 400:
        logger.warning(f"❌ SERIALIZER ERROR at {context['view'].__class__.__name__}: {response.data}")

    if response is not None and response.status_code >= 500:
        logger.error(f"🔥 SERVER ERROR at {context['view'].__class__.__name__}: {response.data}"
                     , exc_info=exc)
        
    if response is not None and response.status_code == 404:
        logger.info(f"🔍 NOT FOUND at {context['view'].__class__.__name__}: {response.data}")

    return response