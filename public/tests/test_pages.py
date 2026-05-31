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
        ("public:how_to", "Как подать обращение"),
        ("public:process", "Порядок обработки"),
        ("public:categories", "Категории обращений"),
        ("public:analytics", "Аналитика и отчеты"),
        ("public:faq", "Вопросы и ответы"),
        ("public:contacts", "Контакты"),
        ("public:documents", "Нормативные документы"),
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
@pytest.mark.parametrize(
    "view_name, status, heading",
    [
        ("public:how_to", 200, "Как подать обращение"),
        ("public:process", 200, "Состояния заявки"),
        ("public:analytics", 200, "Выгрузка отчетов"),
        ("public:faq", 200, "Вопросы и ответы"),
        ("public:contacts", 200, "Контакты"),
        ("public:documents", 200, "Нормативные документы"),
    ],
)
def test_new_public_pages_render(client, view_name, status, heading):
    response = client.get(reverse(view_name))
    assert response.status_code == status
    assert heading in response.content.decode()


@pytest.mark.django_db
@pytest.mark.functional
def test_navbar_groups_info_sections_in_dropdown(client):
    html = _get(client, "public:home")
    # Верхний уровень меню: главная, выпадающее меню «Информация», контакты,
    # обратная связь.
    for label in ("Главная", "Информация", "Контакты", "Обратная связь"):
        assert label in html
    # Информационные разделы доступны как пункты выпадающего меню.
    for label in (
        "О сервисе",
        "Как подать обращение",
        "Порядок обработки",
        "Категории обращений",
        "Аналитика и отчеты",
        "Вопросы и ответы",
        "Нормативные документы",
    ):
        assert label in html
