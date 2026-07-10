"""Link checker routes, mounted under /api/v1/crawl/.

Registered at the empty prefix with ``SimpleRouter`` so the viewset lives at
``/crawl/`` (list/create), ``/crawl/{id}/`` (detail), and the extra actions at
``/crawl/{id}/links|broken|progress/``.
"""
from rest_framework.routers import SimpleRouter

from apps.linkchecker.views import CrawlViewSet

app_name = "linkchecker"

router = SimpleRouter(trailing_slash=True)
router.register("", CrawlViewSet, basename="crawl")

urlpatterns = router.urls
