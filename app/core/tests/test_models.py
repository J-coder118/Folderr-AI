from core.tests.factories import UserFactory
from django.test import TestCase


class UserTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create()

    def test_update_login_timestamp(self):
        self.assertIsNone(self.user.last_login)
        self.user.update_login_timestamp()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_get_auth_tokens(self):
        tokens = self.user.get_auth_tokens()
        self.assertIn("refresh", tokens.keys())
        self.assertIn("access", tokens.keys())
        self.assertIsInstance(tokens["refresh"], str)
        self.assertIsInstance(tokens["access"], str)
