import factory
from factory.django import DjangoModelFactory

from public.models import Feedback


class FeedbackFactory(DjangoModelFactory):
    class Meta:
        model = Feedback

    name = factory.Sequence(lambda n: f"Visitor {n}")
    email = factory.Sequence(lambda n: f"visitor{n}@example.com")
    message = "I have a question about the service."
