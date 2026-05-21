import pytest
from django.urls import reverse


@pytest.fixture
def home_html(client, db):
    response = client.get(reverse("public:home"))
    return response.content.decode()


@pytest.mark.functional
def test_home_shows_service_heading(home_html):
    assert "Учет и анализ телефонных обращений обучающихся" in home_html


@pytest.mark.functional
def test_home_shows_navbar_brand(home_html):
    assert "Журнал обращений" in home_html


@pytest.mark.functional
def test_home_renders_breadcrumbs(home_html):
    assert 'aria-label="Хлебные крошки"' in home_html
    assert 'aria-current="page"' in home_html


@pytest.mark.functional
def test_footer_shows_author(home_html):
    assert "Лавров Дмитрий Андреевич" in home_html


@pytest.mark.functional
def test_home_loads_bootstrap_and_app_styles(home_html):
    assert "vendor/bootstrap/bootstrap.min.css" in home_html
    assert "vendor/bootstrap/bootstrap.bundle.min.js" in home_html
    assert "css/app.css" in home_html
