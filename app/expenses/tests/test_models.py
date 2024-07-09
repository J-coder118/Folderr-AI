from django.test import TestCase

from expenses.tests.factories import ExpenseFactory


class ExpenseTests(TestCase):

    def setUp(self):
        self.expense = ExpenseFactory()

    def test_line_item_headers_returns_all_headers(self):
        expected_headers = []
        for line_item in self.expense.line_items:
            expected_headers += line_item.keys()
        expected_headers = set(expected_headers)
        self.assertEqual(expected_headers, self.expense.line_item_headers)
