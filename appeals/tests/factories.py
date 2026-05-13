from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from appeals.models import (
    Appeal,
    AppealCategory,
    AppealComment,
    AppealHistoryEvent,
    Department,
)
from users.tests.factories import UserFactory


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department

    name = factory.Sequence(lambda n: f"department {n}")


class AppealCategoryFactory(DjangoModelFactory):
    class Meta:
        model = AppealCategory

    name = factory.Sequence(lambda n: f"category {n}")
    department = factory.SubFactory(DepartmentFactory)


class AppealFactory(DjangoModelFactory):
    class Meta:
        model = Appeal

    student_full_name = "Ivan Ivanov"
    student_phone = "+7 (900) 000-00-00"
    summary = factory.Sequence(lambda n: f"appeal {n}")
    description = "Appeal description"
    category = factory.SubFactory(AppealCategoryFactory)
    department = factory.SelfAttribute("category.department")
    due_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=3))
    created_by = factory.SubFactory(UserFactory)


class AppealCommentFactory(DjangoModelFactory):
    class Meta:
        model = AppealComment

    appeal = factory.SubFactory(AppealFactory)
    author = factory.SelfAttribute("appeal.created_by")
    text = "Comment text"


class AppealHistoryEventFactory(DjangoModelFactory):
    class Meta:
        model = AppealHistoryEvent

    appeal = factory.SubFactory(AppealFactory)
    actor = factory.SelfAttribute("appeal.created_by")
    event_type = AppealHistoryEvent.EventType.CREATED
    message = "Appeal created"
