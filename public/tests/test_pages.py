import pytest
from django.urls import reverse


def _get(client, view_name):
    return client.get(reverse(view_name)).content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_about_page_shows_roles(client):
    html = _get(client, "public:about")
    assert "О сервисе" in html
    assert "Оператор" in html
    assert "Ответственный сотрудник" in html
    assert "Администратор" in html


@pytest.mark.django_db
@pytest.mark.functional
def test_categories_page_lists_topics(client):
    html = _get(client, "public:categories")
    assert "Категории обращений" in html
    assert "Учебный процесс" in html


@pytest.mark.django_db
@pytest.mark.functional
@pytest.mark.parametrize(
    "view_name, crumb_label",
    [
        ("public:about", "О сервисе"),
        ("public:categories", "Категории обращений"),
        ("public:feedback", "Обратная связь"),
    ],
)
def test_inner_pages_render_breadcrumb_trail(client, view_name, crumb_label):
    html = _get(client, view_name)
    # На внутренних страницах крошки ведут от главной к текущему разделу.
    assert 'aria-label="Хлебные крошки"' in html
    assert ">Главная</a>" in html
    assert crumb_label in html


@pytest.mark.django_db
@pytest.mark.functional
def test_navbar_lists_public_sections(client):
    html = _get(client, "public:home")
    for label in ("Главная", "О сервисе", "Категории обращений", "Обратная связь"):
        assert label in html
