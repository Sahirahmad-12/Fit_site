import secrets


class SecurityHeadersMiddleware:
    """
    Adds security headers to every HTTP response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Generate CSP nonce
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce

        response = self.get_response(request)

        # Security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"

        response["Permissions-Policy"] = (
            "geolocation=(self), "
            "camera=(), "
            "microphone=(), "
            "payment=()"
        )

        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        response["Cross-Origin-Opener-Policy"] = "same-origin"

        # CSP
        response["Content-Security-Policy"] = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
            f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            f"img-src 'self' data: blob: https://res.cloudinary.com https://*.cloudinary.com https://images.unsplash.com; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"connect-src 'self'; "
            f"worker-src 'self'; "
            f"frame-src https://www.google.com; "
            f"object-src 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"frame-ancestors 'none';"
        )

        return response