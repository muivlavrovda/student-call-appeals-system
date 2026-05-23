import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from public.models import Feedback

FEEDBACK_URL_NAME = "public:feedback"


@pytest.mark.django_db
@pytest.mark.functional
def test_feedback_get_renders_empty_form(client):
    response = client.get(reverse(FEEDBACK_URL_NAME))
    assert response.status_code == 200
    assert b'method="post"' in response.content
    assert not Feedback.objects.exists()


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_feedback_valid_post_saves_and_redirects(client):
    response = client.post(
        reverse(FEEDBACK_URL_NAME),
        data={
            "name": "  Анна   Смирнова ",
            "email": "anna@example.com",
            "message": "  Не приходит письмо со справкой.  ",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == reverse(FEEDBACK_URL_NAME)

    feedback = Feedback.objects.get()
    assert feedback.name == "Анна Смирнова"
    assert feedback.email == "anna@example.com"
    assert feedback.message == "Не приходит письмо со справкой."
    assert feedback.is_processed is False


@pytest.mark.django_db
@pytest.mark.functional
def test_feedback_success_message_is_shown(client):
    response = client.post(
        reverse(FEEDBACK_URL_NAME),
        data={
            "name": "Анна",
            "email": "anna@example.com",
            "message": "Спасибо за сервис!",
        },
        follow=True,
    )
    messages = [str(message) for message in get_messages(response.wsgi_request)]
    assert any("отправлено" in message.lower() for message in messages)


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Анна", "email": "anna@example.com", "message": "   "},
        {"name": "Анна", "email": "anna@example.com", "message": ""},
        {"name": "", "email": "anna@example.com", "message": "Текст"},
        {"name": "Анна", "email": "not-an-email", "message": "Текст"},
    ],
)
def test_feedback_invalid_post_shows_errors_and_saves_nothing(client, payload):
    response = client.post(reverse(FEEDBACK_URL_NAME), data=payload)

    assert response.status_code == 200
    assert response.context["form"].errors
    assert not Feedback.objects.exists()


@pytest.mark.django_db
@pytest.mark.functional
def test_feedback_errors_are_shown_in_russian(client):
    response = client.post(
        reverse(FEEDBACK_URL_NAME),
        data={"name": "Анна", "email": "not-an-email", "message": ""},
    )
    html = response.content.decode()
    assert "Введите сообщение." in html
    assert "Введите корректный адрес электронной почты." in html


@pytest.mark.django_db
@pytest.mark.functional
def test_feedback_invalid_field_gets_bootstrap_invalid_class(client):
    response = client.post(
        reverse(FEEDBACK_URL_NAME),
        data={"name": "Анна", "email": "bad", "message": "Текст"},
    )
    assert "is-invalid" in response.content.decode()
