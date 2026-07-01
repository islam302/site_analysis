"""Root URL configuration.

Keeps the project-level routing tiny: admin, the versioned API, and the
OpenAPI schema/docs. All endpoint definitions live inside the apps.
"""
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.clickjacking import xframe_options_exempt
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


@xframe_options_exempt
def api_tester(request) -> HttpResponse:
    """Serve the standalone HTML API tester (DEBUG only).

    Read and returned raw (not rendered through the template engine) so the
    inline JavaScript is never interpreted as Django template syntax.
    """
    html = (settings.BASE_DIR / "templates" / "api_tester.html").read_text(encoding="utf-8")
    return HttpResponse(html)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.api_v1.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    # Same-origin tester console at /tester/ — avoids CORS while developing.
    urlpatterns += [path("tester/", api_tester, name="api-tester")]
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except ImportError:
        pass
