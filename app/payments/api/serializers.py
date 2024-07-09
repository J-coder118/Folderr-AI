from rest_framework import serializers

from payments.models import StripePaymentLink


class StripePaymentLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = StripePaymentLink
        exclude = ['plan']
