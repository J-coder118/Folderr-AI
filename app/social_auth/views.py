from core.utils import set_refresh_token_cookie
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .serializer import (
    FacebookSocialAuthSerializer,
    GoogleSocialAuthSerializer,
    SIWAResponseSerializer,
)


class GoogleSocialAuthView(GenericAPIView):
    serializer_class = GoogleSocialAuthSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = {"access": serializer.validated_data["access"]}
        bypass_token = request.data.get("bypass_token")
        if bypass_token:
            if bypass_token == settings.COOKIE_BYPASS_TOKEN:
                data["refresh"] = serializer.validated_data["refresh"]
        response = Response(data=data)
        response = set_refresh_token_cookie(
            response, serializer.validated_data["refresh"]
        )
        return response


class FacebookSocialAuthView(GenericAPIView):
    serializer_class = FacebookSocialAuthSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = {"access": serializer.validated_data["access"]}
        bypass_token = request.data.get("bypass_token")
        if bypass_token:
            if bypass_token == settings.COOKIE_BYPASS_TOKEN:
                data["refresh"] = serializer.validated_data["refresh"]
        response = Response(data=data)
        response = set_refresh_token_cookie(
            response, serializer.validated_data["refresh"]
        )
        return response


@api_view(http_method_names=("POST",))
def siwa(request):
    """
    Expects `code` and `id_token` as found in the
    `authorization` object.

    Can also receive `first_name` and `last_name` as
    found in the `user` object.

    Return user data in a dict
    if the information provided is correct.
    """
    serializer = SIWAResponseSerializer(data=request.data)
    result = {}
    response = Response(status=status.HTTP_400_BAD_REQUEST)
    if serializer.is_valid():
        user_data = serializer.create(serializer.validated_data)
        response.status_code = status.HTTP_200_OK
        response = set_refresh_token_cookie(response, user_data["refresh"])
        bypass_token = request.data.get("bypass_token")
        if bypass_token:
            if bypass_token != settings.COOKIE_BYPASS_TOKEN:
                del user_data["refresh"]
        else:
            del user_data["refresh"]
        result.update(user_data)
    else:
        result.update({"errors": serializer.errors})
    response.data = result
    return response
