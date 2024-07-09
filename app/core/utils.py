import logging

import requests
from django.conf import settings
from rest_framework.response import Response

log = logging.getLogger(__name__)


def recaptcha_valid(response_token):
    request_body = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "sitekey": settings.RECAPTCHA_SITE_KEY,
        "response": response_token,
    }
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify", data=request_body
    )
    response_data = response.json()
    log.debug("Recaptcha responded with %s", response_data)
    success = response_data.get("success", False)
    score = response_data.get("score", 0)

    if success and score > 0.5:
        return True

    return False


def set_refresh_token_cookie(
    response: Response,
    refresh_token: str,
    expiry: int = settings.SESSION_COOKIE_AGE,
):
    kwargs = {
        "key": settings.REFRESH_TOKEN_COOKIE_NAME,
        "value": refresh_token,
        "samesite": settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        "domain": settings.REFRESH_TOKEN_COOKIE_DOMAIN,
    }

    if expiry > 0:
        kwargs["expires"] = expiry

    response.set_cookie(**kwargs)
    return response
