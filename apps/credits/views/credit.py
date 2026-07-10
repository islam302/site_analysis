"""Credit views: balance, transaction history, and (simulated) purchase."""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import DefaultPagination
from apps.credits.models import CreditTransaction
from apps.credits.selectors import get_balance, get_transactions
from apps.credits.serializers import (
    CreditBalanceSerializer,
    CreditTransactionSerializer,
    PurchaseInputSerializer,
)
from apps.credits.services import add_credits

logger = logging.getLogger("apps.credits")


class CreditBalanceView(APIView):
    """GET /credits/balance/ — the current user's credit balance."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CreditBalanceSerializer}, summary="Get credit balance")
    def get(self, request: Request) -> Response:
        balance = get_balance(user=request.user)
        return Response(CreditBalanceSerializer(balance).data, status=status.HTTP_200_OK)


class CreditPurchaseView(APIView):
    """POST /credits/purchase/ — add credits (simulated payment)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PurchaseInputSerializer,
        responses={201: CreditBalanceSerializer},
        summary="Purchase credits (simulated)",
    )
    def post(self, request: Request) -> Response:
        serializer = PurchaseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        add_credits(
            user=request.user,
            amount=serializer.validated_data["amount"],
            description=serializer.validated_data.get("description", "") or "Credit purchase",
        )
        balance = get_balance(user=request.user)
        return Response(CreditBalanceSerializer(balance).data, status=status.HTTP_201_CREATED)


class CreditTransactionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET /credits/transactions/ — the user's credit ledger."""

    permission_classes = [IsAuthenticated]
    serializer_class = CreditTransactionSerializer
    pagination_class = DefaultPagination
    # Declared for schema generation; real rows come from get_queryset.
    queryset = CreditTransaction.objects.none()

    def get_queryset(self):
        return get_transactions(user=self.request.user)
