"""Credit routes, mounted under /api/v1/credits/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.credits.views import (
    CreditBalanceView,
    CreditPurchaseView,
    CreditTransactionViewSet,
)

app_name = "credits"

router = DefaultRouter()
router.register("transactions", CreditTransactionViewSet, basename="transaction")

urlpatterns = [
    path("balance/", CreditBalanceView.as_view(), name="balance"),
    path("purchase/", CreditPurchaseView.as_view(), name="purchase"),
    path("", include(router.urls)),
]
