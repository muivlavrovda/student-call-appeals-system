import pytest

from public.models import Feedback
from public.tests.factories import FeedbackFactory


@pytest.mark.django_db
@pytest.mark.unit
def test_feedback_save_normalizes_name_and_message():
    feedback = FeedbackFactory(
        name="  Иван    Петров  ",
        message="  Здравствуйте!  ",
    )
    feedback.refresh_from_db()
    assert feedback.name == "Иван Петров"
    assert feedback.message == "Здравствуйте!"


@pytest.mark.django_db
@pytest.mark.unit
def test_feedback_defaults_to_unprocessed():
    feedback = FeedbackFactory()
    assert feedback.is_processed is False


@pytest.mark.django_db
@pytest.mark.unit
def test_feedback_str_includes_name():
    feedback = FeedbackFactory(name="Мария")
    assert "Мария" in str(feedback)


@pytest.mark.django_db
@pytest.mark.unit
def test_feedback_ordering_is_newest_first():
    older = FeedbackFactory()
    newer = FeedbackFactory()
    assert list(Feedback.objects.all()) == [newer, older]
