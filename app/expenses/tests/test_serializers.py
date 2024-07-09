from django.test import TestCase

from expenses.api.serializers import ExpenseSerializer
from expenses.tests.factories import ExpenseFactory


class ExpenseSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.expense = ExpenseFactory()

    def test_to_representation_includes_line_item_headers(self):
        serializer = ExpenseSerializer(self.expense)
        self.assertIsNotNone(serializer.data.get("line_item_headers"))
        self.assertEqual(serializer.data.get("line_item_headers"),
                         self.expense.line_item_headers)
