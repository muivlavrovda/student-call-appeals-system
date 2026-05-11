import factory
from factory.django import DjangoModelFactory

from users.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "pw-default")
        return model_class.objects.create_user(*args, password=password, **kwargs)


class StaffUserFactory(UserFactory):
    is_staff = True


class SuperUserFactory(UserFactory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "pw-default")
        return model_class.objects.create_superuser(*args, password=password, **kwargs)
