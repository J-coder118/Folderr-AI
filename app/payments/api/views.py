from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from payments.api.serializers import StripePaymentLinkSerializer
from payments.models import StripePaymentLink


class RetrieveStripePaymentLink(RetrieveAPIView):
    queryset = StripePaymentLink.objects.all()
    serializer_class = StripePaymentLinkSerializer


@api_view()
@permission_classes([IsAuthenticated])
def get_plus_status(request):
    request.user.sync_membership()
    request.user.refresh_from_db()
    return Response({'isPlus': request.user.is_plus})
