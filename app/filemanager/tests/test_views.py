from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.tests.factories import UserFactory
from filemanager.models import IgnoredSuggestedFolder
from filemanager.tests.factories import FolderFactory, IgnoredSuggestedFolderFactory, \
    ShareFactory, SuggestedFolderFactory, TaskFactory


class TaskViewSetTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.api_client = APIClient()

    def setUp(self):
        task = TaskFactory()
        another_task = TaskFactory(created_by=task.created_by)
        self.task = task
        self.another_task = another_task
        self.api_client.force_authenticate(self.task.created_by)

    def test_list_without_folder_returns_all_tasks(self):
        response = self.api_client.get(reverse("tasks-list"))
        self.assertEqual(response.status_code, 200)
        all_ids = []
        for data in response.json():
            all_ids += [data['id']]
        self.assertIn(self.task.pk, all_ids)
        self.assertIn(self.another_task.pk, all_ids)

    def test_list_with_folder_returns_only_folder_tasks(self):
        response = self.api_client.get(
            reverse("tasks-list") + f"?folder={self.task.folder.pk}")
        self.assertEqual(response.status_code, 200)
        all_ids = []
        for data in response.json():
            all_ids += [data['id']]
        self.assertIn(self.task.pk, all_ids)
        self.assertNotIn(self.another_task.pk, all_ids)

    def test_list_is_paginated(self):
        TaskFactory.create_batch(30, created_by=self.task.created_by,
                                 folder=self.task.folder)

        response = self.api_client.get(
            reverse("tasks-list") + f"?folder={self.task.folder.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()['count'], 20)
        self.assertEqual(len(response.json()['results']), 20)


class IgnoredSuggestedFolderListTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        api_client = APIClient()
        user = UserFactory()
        api_client.force_authenticate(user)
        cls.api_client = api_client
        cls.user = user
        cls.folder = FolderFactory(created_by=user)

    def test_list_of_ignored_folders_returned(self):
        ignored = IgnoredSuggestedFolderFactory(user=self.user, folder=self.folder)
        response = self.api_client.get(
            reverse('ignored-suggested-folders-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ignored.pk, response.json()[0]['id'])

    def test_create_ignored_folder(self):
        suggested_folder = SuggestedFolderFactory(asset_type=self.folder.asset_type)
        self.assertEqual(IgnoredSuggestedFolder.objects.count(), 0)
        response = self.api_client.post(
            reverse('ignored-suggested-folders-list'),
            data={'folder': self.folder.pk, 'suggested_folder': suggested_folder.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IgnoredSuggestedFolder.objects.count(), 1)


class ShareViewSetTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.api_client = APIClient()

    def test_received_returns_receiver_shared_folder(self):
        self.api_client.force_authenticate(self.user)
        share = ShareFactory(receiver=self.user)

        response = self.api_client.get(
            reverse('shares-received', kwargs={'pk': share.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], share.pk)
