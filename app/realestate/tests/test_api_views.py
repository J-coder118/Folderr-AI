from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from realestate.tests.factories import HomeFactory


class FindHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.api_client = APIClient()
        cls.api_url = reverse("realestate:find-home-api")

    def setUp(self) -> None:
        self.home = HomeFactory()

    def test_find_home_returns_serialized_data(self):
        self.api_client.force_authenticate(self.home.folder.created_by)
        with patch("realestate.api.views.Home") as mock_home_class:
            mock_home_class.get_or_create_from_address.return_value = (False, self.home)
            response = self.api_client.post(
                self.api_url,
                data={
                    "folder_id": self.home.folder_id,
                    "full_address": self.home.full_address,
                },
            )
            expected_fields = [
                "id",
                "folder",
                "full_address",
                "home_type",
                "price_estimate",
                "last_sold_price",
                "year_built",
                "lot_size",
                "living_area",
                "no_of_bathrooms",
                "no_of_full_bathrooms",
                "no_of_half_bathrooms",
                "no_of_quarter_bathrooms",
                "no_of_bedrooms",
            ]
            for field in response.json().keys():
                self.assertIn(field, expected_fields)


class UpdateHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.api_client = APIClient()

    def setUp(self) -> None:
        self.home = HomeFactory()

    def test_update_is_possible(self):
        self.api_client.force_authenticate(self.home.folder.created_by)
        no_of_bathrooms = self.home.no_of_bathrooms
        if no_of_bathrooms is None:
            no_of_bathrooms = 1
        new_no_of_bathrooms = no_of_bathrooms + 1
        response = self.api_client.patch(
            reverse("realestate:update-home-api", kwargs={"pk": self.home.pk}),
            data={'no_of_bathrooms': new_no_of_bathrooms})
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['no_of_bathrooms'], new_no_of_bathrooms)
