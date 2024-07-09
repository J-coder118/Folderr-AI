import logging
from typing import Any

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class ZillowClient:
    def __init__(self, full_address):
        self.full_address = full_address
        session = requests.Session()
        session.headers = {
            "X-RapidAPI-Key": settings.RAPID_API_KEY,
            "X-RapidAPI-Host": settings.ZILLOW_RAPID_API_HOST,
        }
        self.session = session

    def _get_response(self, url: str, params: dict) -> tuple[bool, Any]:
        success = False
        error_msg = "Unknown error"
        response = self.session.get(url, params=params)
        if response.status_code == requests.codes.ok:
            success = True
            return success, response.json()
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_msg = str(e)
        log.info(
            "Got status code %s while getting url %s with params %s. Message: %s",
            response.status_code,
            url,
            params,
            error_msg,
        )
        return success, error_msg

    def _build_address(self, address: dict) -> str:
        city = address["city"]
        state = address["state"]
        street_address = address["streetAddress"]
        zip_code = address["zipcode"]
        return f"{street_address}, {city}, {state} {zip_code}"

    def _build_model_data(self, data) -> dict:
        return {
            "home_type": data.get("resoFacts", {}).get("homeType", ""),
            "price_estimate": data.get("zestimate", ""),
            "last_sold_price": data.get("lastSoldPrice", ""),
            "year_built": data.get("yearBuild"),
            "lot_size": data.get("lotSize", ""),
            "living_area": data.get("livingArea"),
            "no_of_bathrooms": data.get("bathrooms"),
            "no_of_full_bathrooms": data.get("resoFacts", {}).get(
                "bathroomsFull"
            ),
            "no_of_half_bathrooms": data.get("resoFacts", {}).get(
                "bathroomsHalf"
            ),
            "no_of_quarter_bathrooms": data.get("resoFacts", {}).get(
                "bathroomsOneQuarter"
            ),
            "no_of_bedrooms": data.get("bedrooms"),
            "image_url": data.get("desktopWebHdpImageLink"),
        }

    def get_home_details(self) -> tuple[bool, (str | dict)]:
        success, search_results = self._get_response(
            settings.ZILLOW_SEARCH_API_URL, {"location": self.full_address}
        )
        if success:
            if isinstance(search_results, dict):
                log.debug("Single property found. Data: %s", search_results)
            else:
                log.debug("List of properties found. Data: %s", search_results)
                return False, "Many properties found for this address."

            model_data = self._build_model_data(search_results)
            return success, model_data
        return False, "Unable to fetch properties."
