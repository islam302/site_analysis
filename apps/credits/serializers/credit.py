"""Credit serializers."""
from rest_framework import serializers

from apps.credits.models import CreditBalance, CreditTransaction


class CreditBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditBalance
        fields = ["balance", "total_purchased", "total_used", "updated_at"]
        read_only_fields = fields


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = [
            "id",
            "amount",
            "transaction_type",
            "description",
            "balance_after",
            "created_at",
        ]
        read_only_fields = fields


class PurchaseInputSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1, max_value=1_000_000)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
