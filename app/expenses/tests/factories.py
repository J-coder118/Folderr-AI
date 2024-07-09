from decimal import Decimal

import factory.django
from faker import Faker

from expenses.models import Expense
from filemanager.tests.factories import FileFactory

fake = Faker()


def ocr_data_factory():
    line_items = []
    subtotal = Decimal("0")

    for i in range(5):
        unit_price: Decimal = fake.pydecimal(
            left_digits=2, right_digits=2, positive=True, min_value=1
        )
        quantity = fake.pyint(min_value=1, max_value=9)
        price = unit_price * quantity
        subtotal += price
        line_items += [
            {
                "ITEM": fake.sentence(),
                "PRICE": str(price),
                "QUANTITY": quantity,
                "UNIT_PRICE": str(unit_price),
            }
        ]
    tax = subtotal * Decimal("0.15")
    total = subtotal + tax
    address = fake.address()
    company_name = fake.company()
    phone_number = fake.phone_number()
    return {
        "line_item_fields": line_items,
        "summary_fields": {
            "ADDRESS": address,
            "STREET": fake.street_address(),
            "CITY": fake.city(),
            "STATE": fake.pystr(min_chars=2, max_chars=2).upper(),
            "ZIP_CODE": fake.postcode(),
            "NAME": company_name,
            "ADDRESS_BLOCK": address,
            "AMOUNT_PAID": str(total),
            "DUE_DATE": str(fake.date()),
            "RECEIVER_PHONE": fake.phone_number(),
            "SUBTOTAL": str(subtotal),
            "TAX": str(tax),
            "TOTAL": str(total),
            "AMOUNT_DUE": "0.00",
            "VENDOR_ADDRESS": address,
            "VENDOR_NAME": company_name,
            "VENDOR_PHONE": phone_number,
            "VENDOR_URL": fake.url(),
        },
    }


class ExpenseFactory(factory.django.DjangoModelFactory):
    file = factory.SubFactory(FileFactory)

    @factory.post_generation
    def populate_json_fields(obj: Expense, create, extracted, **kwargs):
        ocr_data = ocr_data_factory()
        obj.summary = ocr_data['summary_fields']
        obj.line_items = ocr_data['line_item_fields']
        obj.save()

    class Meta:
        model = Expense
