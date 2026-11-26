"""JSON error pages. They never show stack traces or internal details."""
from django.http import JsonResponse


def not_found(request, exception=None):
    return JsonResponse({"detail": "Not found."}, status=404)


def server_error(request):
    return JsonResponse(
        {"detail": "Something went wrong on our side. Please try again later."},
        status=500,
    )


def forbidden(request, exception=None):
    return JsonResponse({"detail": "You do not have permission to do that."}, status=403)


def bad_request(request, exception=None):
    return JsonResponse({"detail": "Bad request."}, status=400)
