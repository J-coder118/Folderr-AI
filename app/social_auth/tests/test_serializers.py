import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase
from faker import Faker
from social_auth.serializer import SIWAResponseSerializer


class SIWAResponseSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fake = Faker()
        cls.fake = fake
        cls.apple_response = {
            "code": fake.pystr(),
            "id_token": fake.pystr(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
        }
        _, key_file = tempfile.mkstemp()
        with open(key_file, "w", encoding="utf-8") as fp:
            fp.write(fake.pystr())
        cls.key_path = Path(key_file)

    def test_generate_client_secret(self):
        with self.settings(SIWA_PKEY_PATH=self.key_path):
            with patch("social_auth.serializer.jwt") as mock_jwt:
                client_secret = self.fake.pystr()
                mock_jwt.encode.return_value = client_secret
                self.assertEqual(
                    SIWAResponseSerializer._generate_client_secret(), client_secret
                )

    def test_validate(self):
        with self.settings(SIWA_PKEY_PATH=self.key_path):
            with patch("social_auth.serializer.jwt") as mock_jwt, patch(
                "social_auth.serializer.requests"
            ) as mock_requests:
                client_secret = self.fake.pystr()
                mock_jwt.encode.return_value = client_secret

                mock_apple_token_response = MagicMock()
                mock_apple_token_response.status_code = 200

                mock_requests.request.return_value = mock_apple_token_response

                kid = self.fake.pystr()
                mock_jwt.get_unverified_header.return_value = {"kid": kid}

                mock_pubkey_response = MagicMock()
                mock_pubkey_response.status_code = 200
                mock_pubkey_response.json.return_value = {"keys": [{"kid": kid}]}
                mock_requests.get.return_value = mock_pubkey_response

                identity_data = {
                    "email": self.apple_response["email"],
                    "sub": self.fake.pystr(),
                }
                mock_jwt.decode.return_value = identity_data

                serializer = SIWAResponseSerializer(data=self.apple_response)
                self.assertTrue(serializer.is_valid())
