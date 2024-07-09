from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase

from filemanager.tests.factories import FolderFactory
from realestate.models import Home
from realestate.tests.factories import HomeFactory, property_details_factory


class HomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.folder = FolderFactory()

    def test_get_or_create_from_address_creates_new_instance(self):
        with patch("realestate.models.ZillowClient") as mock_zillow_client_class:
            zillow_client = MagicMock()
            zillow_client.get_home_details.return_value = (
                True,
                property_details_factory(),
            )
            mock_zillow_client_class.return_value = zillow_client

            _, home = Home.get_or_create_from_address(self.folder.pk, "abcd")
            self.assertFalse(home._state.adding)

    def test_get_or_create_from_address_returns_existing_instance(self):
        home = HomeFactory()
        _, result = Home.get_or_create_from_address(
            folder_id=home.folder.pk, full_address=home.full_address
        )
        self.assertEqual(home.pk, result.pk)

    def test_image_saving(self):
        home = HomeFactory()
        with patch("realestate.models.requests") as mock_requests:
            with (settings.BASE_DIR / "fixtures" / "sample_receipts" / "hd1.png").open(
                    'rb') as fp:
                response_content = fp.read()
            mock_response = MagicMock()
            mock_response.content = response_content
            mock_requests.get.return_value = mock_response
            home.image_url = "https://google.io/foobar.jpg"
            home.save()
        home.refresh_from_db()
        self.assertIsNotNone(home.folder.image.name)
