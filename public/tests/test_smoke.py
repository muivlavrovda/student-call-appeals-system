import pytest
from django.urls import reverse


@pytest.mark.smoke
def test_home_url_reverses():
    assert reverse("public:home") == "/"


@pytest.mark.django_db
@pytest.mark.smoke
def test_home_page_opens(client):
    response = client.get(reverse("public:home"))
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.smoke
def test_home_page_uses_expected_templates(client):
    response = client.get(reverse("public:home"))
    template_names = {template.name for template in response.templates}
    assert "public/home.html" in template_names
    assert "base.html" in template_names
