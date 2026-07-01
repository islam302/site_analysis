"""API v1 URL aggregator.

Mounts each app's routes under a stable, versioned prefix:
- /api/v1/auth/          -> users
- /api/v1/google_speed/  -> analysis (Google PageSpeed)
"""
from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.users.urls")),
    path("google_speed/", include("apps.analysis.urls")),
]
