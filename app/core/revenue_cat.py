import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class RevenueCat:
    def __init__(self, platform="ios"):
        self.platform = platform
        self.session = self.get_session()

    def get_session(self):
        if self.platform == "ios":
            bearer_token = settings.REVENUE_CAT_PUBLIC_KEY_IOS
        else:
            raise ValueError(f"Platform {self.platform} is unknown.")
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}",
        }
        session = requests.Session()
        session.headers.update(headers)
        return session

    def get_customer(self, app_user_id):
        response = self.session.get(
            f"https://api.revenuecat.com/v1/subscribers/{app_user_id}"
        )

        if response.ok:
            return response.json()["subscriber"]
        else:
            log.info(
                "Failed to fetch RevenueCat customer. Reason: %s",
                response.json(),
            )

    def is_subscribed(self, app_user_id):
        customer = self.get_customer(app_user_id)
        if customer is None:
            return False
        else:
            return len(customer["subscriptions"].keys()) > 0
