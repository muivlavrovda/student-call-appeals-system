import pytest
from django.core.management import call_command
from django.urls import reverse


@pytest.mark.smoke
def test_django_check_passes():
    call_command("check")


@pytest.mark.django_db
@pytest.mark.smoke
def test_admin_login_page_opens(client):
    response = client.get(reverse("admin:login"))
    assert response.status_code == 200
