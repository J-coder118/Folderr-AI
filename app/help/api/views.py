from rest_framework.generics import ListAPIView

from help.api.serializers import HelpTopicSerializer
from help.models import HelpTopic


class GetHelpTopics(ListAPIView):
    model = HelpTopic
    serializer_class = HelpTopicSerializer
    queryset = HelpTopic.objects.all()
