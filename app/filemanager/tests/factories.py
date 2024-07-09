from datetime import datetime, timedelta

import factory
from django.conf import settings
from django.core.files import File as DjangoFile
from faker import Faker

from core.tests.factories import CreatedByModelFactory
from filemanager.models import (
    AssetType,
    File,
    Folder,
    FolderType,
    IgnoredSuggestedFolder, Share, SuggestedField,
    SuggestedFolder, Task,
)

fake = Faker()


class AssetTypeFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("word")

    class Meta:
        model = AssetType


class SuggestedFieldFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("word")
    placeholder = factory.LazyAttribute(lambda obj: obj.title)
    asset_type = factory.SubFactory(AssetTypeFactory)

    class Meta:
        model = SuggestedField


class SuggestedFolderFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("word")
    asset_type = factory.SubFactory(AssetTypeFactory)

    class Meta:
        model = SuggestedFolder


class FolderTypeFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("word")

    class Meta:
        model = FolderType


class FolderFactory(CreatedByModelFactory):
    title = factory.Faker("word")
    asset_type = factory.SubFactory(AssetTypeFactory)
    folder_type = factory.SubFactory(FolderTypeFactory)

    class Meta:
        model = Folder


class FileFactory(CreatedByModelFactory):
    file_name = factory.Faker("file_name")
    folder = factory.SubFactory(FolderFactory)
    file = factory.django.FileField()

    class Meta:
        model = File


def get_file() -> File:
    file_name = "hd1.png"
    folder = FolderFactory.create()
    sample_receipt_path = settings.BASE_DIR / "fixtures" / "sample_receipts" / file_name
    with sample_receipt_path.open("rb") as receipt_file:
        django_file = DjangoFile(file=receipt_file, name=file_name)
        file = File(
            created_by=folder.created_by,
            file_name=file_name,
            file=django_file,
            folder=folder,
        )
        file.full_clean()
        file.save(make_thumbnail=False)
    return file


ocr_data = {
    "line_item_fields": [
        {
            "ITEM": "ELMET GIRO VERCE",
            "PRICE": "70.00",
            "QUANTITY": "1",
            "UNIT_PRICE": "70.00",
        },
        {
            "ITEM": "DERAILLEUR CABLE 1",
            "UNIT_PRICE": "6.00",
            "QUANTITY": "1",
            "PRICE": "6.00",
        },
        {
            "ITEM": "LABOR INSTALL/AL\n-",
            "UNIT_PRICE": "60.00",
            "QUANTITY": "1",
            "PRICE": "60.00",
        },
        {
            "ITEM": "DER SRAM RR GX 1X",
            "UNIT_PRICE": "139.99",
            "QUANTITY": "1",
            "PRICE": "139.99",
        },
        {
            "ITEM": "CHAIN SRAM 1/2X3/3",
            "UNIT_PRICE": "40,00",
            "QUANTITY": "1",
            "PRICE": "40.00",
        },
        {
            "ITEM": "SHIMANO BRAKE ROTO",
            "UNIT_PRICE": "39.99",
            "QUANTITY": "1",
            "PRICE": "39.99",
        },
        {
            "ITEM": "LABOR ADJUST BRA\n-",
            "UNIT_PRICE": "20.00",
            "QUANTITY": "1",
            "PRICE": "20.00",
        },
    ],
    "summary_fields": {
        "ADDRESS": "Bicycle Outfitters\nWay Unit 101C\nCO 80439\nEvergreen,",
        "STREET": "Way Unit 101C",
        "CITY": "Evergreen,",
        "STATE": "CO",
        "ZIP_CODE": "80439",
        "NAME": "Bicycle Outfitters",
        "ADDRESS_BLOCK": "Way Unit 101C\nCO 80439\nEvergreen,",
        "AMOUNT_PAID": "389.30",
        "DUE_DATE": "08/09/2022",
        "RECEIVER_PHONE": "970-333-0072",
        "SUBTOTAL": "375.98",
        "TAX": "13.32",
        "TOTAL": "0.00",
        "AMOUNT_DUE": "0.00",
        "VENDOR_ADDRESS": "Bicycle Outfitters\nWay Unit 101C\nCO 80439\nEvergreen,",
        "VENDOR_NAME": "Bicycle Outfitters",
        "VENDOR_PHONE": "303-674-6737",
        "VENDOR_URL": "www.velocoloradu.com",
        "OTHER": "23417D",
    },
}


class TaskFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('word')
    description = factory.Faker('sentence')
    task_date = factory.LazyFunction(lambda: datetime.now() + timedelta(days=1))
    folder = factory.SubFactory(FolderFactory)
    created_by = factory.LazyAttribute(lambda o: o.folder.created_by)

    class Meta:
        model = Task


class IgnoredSuggestedFolderFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory('core.tests.factories.UserFactory')
    suggested_folder = factory.SubFactory(SuggestedFolderFactory)
    folder = factory.SubFactory(FolderFactory)

    class Meta:
        model = IgnoredSuggestedFolder


class ShareFactory(factory.django.DjangoModelFactory):
    folder = factory.SubFactory(FolderFactory)
    permission = 1
    sender = factory.SubFactory('core.tests.factories.UserFactory')
    receiver = factory.SubFactory('core.tests.factories.UserFactory')
    receiver_email = factory.LazyAttribute(lambda o: o.receiver.email)

    class Meta:
        model = Share
