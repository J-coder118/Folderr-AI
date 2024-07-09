from unittest.mock import MagicMock

from django.conf import settings
from django.core.files import File
from django.test import TestCase

from core.tests.factories import UserFactory
from filemanager.serializers import VideoFileSerializer
from filemanager.tests.factories import FolderFactory


class VideoFileSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.folder = FolderFactory()

    def test_folder_owner_validation(self):
        with (settings.BASE_DIR / "fixtures" / "folderr-video.webm").open('rb') as fp:
            django_file = File(fp, name="folderr-video.webm")
            data = {
                "folder": self.folder.id,
                "file": django_file,
            }
            request = MagicMock()
            another_user = UserFactory()
            request.user = another_user
            serializer = VideoFileSerializer(data=data, context={'request': request})
            self.assertFalse(serializer.is_valid())
            request.user = self.folder.created_by
            serializer = VideoFileSerializer(data=data, context={'request': request})
            self.assertTrue(serializer.is_valid())
