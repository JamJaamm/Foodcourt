"""Custom security middleware for Choply.

Adds Content-Security-Policy, Permissions-Policy, and
additional defence-in-depth headers on every response.
"""


class SecurityHeadersMiddleware:
    """Inject security headers into every HTTP response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content-Security-Policy — tighten as the project grows.
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com "
            "https://accounts.google.com https://www.gstatic.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://unpkg.com https://accounts.google.com https://www.gstatic.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://accounts.google.com https://www.gstatic.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://nominatim.openstreetmap.org "
            "https://accounts.google.com https://www.gstatic.com; "
            "frame-src https://accounts.google.com https://www.gstatic.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Permissions-Policy — disable browser features we don't use.
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(self), '
            'gyroscope=(), magnetometer=(), microphone=(), '
            'payment=(self), usb=(), interest-cohort=()'
        )

        # Additional defence-in-depth headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'

        return response
