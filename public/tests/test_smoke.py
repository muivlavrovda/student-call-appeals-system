import pytest
from django.urls import reverse

PUBLIC_PAGES = [
    ("public:home", "/", "public/home.html"),
    ("public:about", "/about/", "public/about.html"),
    ("public:categories", "/categories/", "public/categories.html"),
    ("public:feedback", "/feedback/", "public/feedback.html"),
]


@pytest.mark.smoke
@pytest.mark.parametrize("view_name, path, _template", PUBLIC_PAGES)
def test_public_url_reverses(view_name, path, _template):
    assert reverse(view_name) == path


@pytest.mark.django_db
@pytest.mark.smoke
@pytest.mark.parametrize("view_name, _path, _template", PUBLIC_PAGES)
def test_public_page_opens(client, view_name, _path, _template):
    response = client.get(reverse(view_name))
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.smoke
@pytest.mark.parametrize("view_name, _path, template", PUBLIC_PAGES)
def test_public_page_uses_expected_templates(client, view_name, _path, template):
    response = client.get(reverse(view_name))
    template_names = {used.name for used in response.templates}
    assert template in template_names
    assert "base.html" in template_names
