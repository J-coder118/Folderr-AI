import factory
from faker import Faker

from filemanager.tests.factories import FolderFactory
from realestate.models import Home

fake = Faker()


def _random_price_estimate():
    return str(fake.pyint(min_value=100_000, max_value=10_000_000_000))


def _random_last_sold_price():
    return str(fake.pyint(min_value=100_000, max_value=10_000_000_000))


def _random_lot_size():
    return str(fake.pyint(min_value=1000))


def _random_living_area():
    return str(fake.pyint(min_value=1000))


def property_details_factory() -> dict:
    return {
        "full_address": fake.address(),
        "home_type": "SingleFamily",
        "price_estimate": _random_price_estimate(),
        "last_sold_price": _random_last_sold_price(),
        "year_built": fake.pyint(min_value=1000, max_value=2022),
        "lot_size": _random_lot_size(),
        "living_area": _random_living_area(),
        "no_of_full_bathrooms": fake.pyint(min_value=1, max_value=6),
        "no_of_half_bathrooms": fake.pyint(min_value=1, max_value=6),
        "no_of_quarter_bathrooms": fake.pyint(min_value=1, max_value=6),
        "no_of_bedrooms": fake.pyint(min_value=1, max_value=10),
    }


class HomeFactory(factory.django.DjangoModelFactory):
    folder = factory.SubFactory(FolderFactory)
    full_address = factory.Faker("address")
    home_type = "SingleFamily"
    price_estimate = factory.LazyFunction(_random_price_estimate)
    last_sold_price = factory.LazyFunction(_random_last_sold_price)
    year_built = factory.Faker("pyint", min_value=1000, max_value=2022)
    lot_size = factory.LazyFunction(_random_lot_size)
    living_area = factory.LazyFunction(_random_living_area)
    no_of_full_bathrooms = factory.Faker("pyint", min_value=1, max_value=6)
    no_of_half_bathrooms = factory.Faker("pyint", min_value=1, max_value=6)
    no_of_quarter_bathrooms = factory.Faker("pyint", min_value=1, max_value=6)
    no_of_bedrooms = factory.Faker("pyint", min_value=1, max_value=10)

    class Meta:
        model = Home
