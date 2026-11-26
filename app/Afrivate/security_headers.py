"""Security headers for API responses.

The backend serves JSON, so browsers have no reason to run scripts, load frames or
submit forms from its responses. A strict Content Security Policy makes that explicit.
Pages that do need scripts (Django admin, API docs, static files) are left alone.
"""

# Paths that render HTML with scripts or styles and must keep a looser policy.
CSP_EXEMPT_PREFIXES = ("/admin/", "/api/v1/docs/", "/docs/", "/api-auth/", "/static/")

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class ApiSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path

        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)

        if not path.startswith(CSP_EXEMPT_PREFIXES):
            response.headers.setdefault("Content-Security-Policy", API_CSP)

        # API responses can hold private data, so shared caches and the browser
        # back/forward cache must not keep them.
        if path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")

        return response
