"""API v1 URL aggregator.

Mounts each app's routes under a stable, versioned prefix:
- /api/v1/auth/          -> users
- /api/v1/google_speed/  -> analysis (Google PageSpeed only)
- /api/v1/gtmetrix/      -> gtmetrix (GTmetrix only)
- /api/v1/speed_test/    -> speed_test (Google PageSpeed + GTmetrix combined)
"""
from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.users.urls")),
    path("google_speed/", include("apps.analysis.urls")),
    path("gtmetrix/", include("apps.gtmetrix.urls")),
    path("speed_test/", include("apps.speed_test.urls")),
    path("audits/", include("apps.audits.urls")),
    path("credits/", include("apps.credits.urls")),
    path("ssl/", include("apps.ssl_check.urls")),
    path("crawl/", include("apps.linkchecker.urls")),
    path("full_report/", include("apps.full_report.urls")),
    # Validator mounts two sibling prefixes: validate/ and validations/.
    path("", include("apps.validator.urls")),
]
