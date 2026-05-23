import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.urls import reverse

from public.admin import FeedbackAdmin
from public.models import Feedback
from public.tests.factories import FeedbackFactory
from users.tests.factories import SuperUserFactory


def _feedback_admin():
    return FeedbackAdmin(Feedback, AdminSite())


@pytest.mark.django_db
@pytest.mark.unit
def test_feedback_admin_disables_adding():
    request = RequestFactory().get("/")
    assert _feedback_admin().has_add_permission(request) is False


@pytest.mark.django_db
@pytest.mark.unit
def test_feedback_admin_content_is_readonly():
    model_admin = _feedback_admin()
    for field in ("name", "email", "message", "created_at"):
        assert field in model_admin.readonly_fields


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.integration
def test_admin_can_open_feedback_changelist(client):
    admin_user = SuperUserFactory(password="secret")
    assert client.login(email=admin_user.email, password="secret")
    FeedbackFactory(name="Тестовое сообщение")

    response = client.get(reverse("admin:public_feedback_changelist"))

    assert response.status_code == 200
    assert "Тестовое сообщение" in response.content.decode()
