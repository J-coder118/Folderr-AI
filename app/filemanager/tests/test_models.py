from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.utils.text import slugify

from filemanager.tests.factories import FolderFactory


class FolderTests(TestCase):

    def test_set_email_sets_email(self):
        with patch("filemanager.models.secrets") as mock_secrets:
            mock_secrets.token_urlsafe.side_effect = ['abcd', 'efgh']
            folder = FolderFactory()
            folder.set_email()
            self.assertEqual(folder.email,
                             f"{slugify(folder.title.lower())}-efgh@{settings.FOLDER_EMAIL_DOMAIN}")

    def test_set_email_with_duplicate_email(self):
        with patch("filemanager.models.secrets") as mock_secrets:
            mock_secrets.token_urlsafe.side_effect = ['abcd', 'abcd', 'efgh']
            folder = FolderFactory()
            FolderFactory(title=folder.title)
            self.assertEqual(mock_secrets.token_urlsafe.call_count, 3)
