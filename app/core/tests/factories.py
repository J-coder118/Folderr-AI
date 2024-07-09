import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    terms_agreed = True
    is_verified = True

    class Meta:
        model = User


class CreatedByModelFactory(factory.django.DjangoModelFactory):
    created_by = factory.SubFactory(UserFactory)
