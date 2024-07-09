from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.tests.factories import UserFactory
from expenses.api.views import CREATED_AT_OLDEST_PARAM
from expenses.tests.factories import ocr_data_factory
from filemanager.models import File, Folder
from filemanager.tests.factories import FileFactory, FolderFactory


class ScannedDataViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.api_client = APIClient()
        cls.expense_list_url = reverse("expenses:expenses-list")
        cls.user = UserFactory()

    def test_queryset_includes_only_owners_objects(self):
        a_file: File = FileFactory()
        another_file: File = FileFactory()

        a_file.save_ocr_data(ocr_data_factory())
        another_file.save_ocr_data(ocr_data_factory())

        tokens: dict = a_file.created_by.get_auth_tokens()

        self.api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.api_client.get(self.expense_list_url)

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(a_file.expense.pk, response.data["results"][0]["id"])

    def test_query_order_by_latest_created_by_default(self):
        a_file: File = FileFactory(created_by=self.user)
        another_file: File = FileFactory(created_by=self.user)

        a_file.save_ocr_data(ocr_data_factory())
        another_file.save_ocr_data(ocr_data_factory())

        tokens: dict = self.user.get_auth_tokens()

        self.api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.api_client.get(self.expense_list_url)

        self.assertEqual(response.data["results"][0]["id"], another_file.expense.pk)

    def test_query_order_by_search_params(self):
        a_file: File = FileFactory(created_by=self.user)
        another_file: File = FileFactory(created_by=self.user)

        a_file.save_ocr_data(ocr_data_factory())
        another_file.save_ocr_data(ocr_data_factory())

        tokens: dict = self.user.get_auth_tokens()

        self.api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.api_client.get(
            self.expense_list_url + f"?order_by={CREATED_AT_OLDEST_PARAM}"
        )

        self.assertEqual(response.data["results"][0]["id"], a_file.expense.pk)

    def test_can_list_expenses_for_each_folder_separately(self):
        a_folder: Folder = FolderFactory(created_by=self.user)
        another_folder: Folder = FolderFactory(created_by=self.user)
        a_file: File = FileFactory(created_by=self.user, folder=a_folder)
        another_file: File = FileFactory(created_by=self.user, folder=another_folder)

        a_file.save_ocr_data(ocr_data_factory())
        another_file.save_ocr_data(ocr_data_factory())

        tokens: dict = self.user.get_auth_tokens()

        self.api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.api_client.get(
            self.expense_list_url + f"?folder={a_file.folder_id}"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['count'], 1)
        all_pk = []
        for expense in response_data['results']:
            all_pk += [expense['id']]
        another_file.refresh_from_db()
        self.assertNotIn(another_file.expense.pk, all_pk)

    def test_list_contains_subfolder_expenses_as_well(self):
        a_folder = FolderFactory(created_by=self.user)
        subfolder = FolderFactory(created_by=self.user, parent=a_folder, is_root=False)
        a_file: File = FileFactory(created_by=self.user, folder=a_folder)
        another_file: File = FileFactory(created_by=self.user, folder=subfolder)

        a_file.save_ocr_data(ocr_data_factory())
        another_file.save_ocr_data(ocr_data_factory())

        self.api_client.force_authenticate(self.user)
        response = self.api_client.get(
            self.expense_list_url + f"?folder={a_file.folder_id}"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['count'], 2)
        all_pk = []
        for expense in response_data['results']:
            all_pk += [expense['id']]
        a_file.refresh_from_db()
        another_file.refresh_from_db()
        self.assertIn(a_file.expense.pk, all_pk)
        self.assertIn(another_file.expense.pk, all_pk)
