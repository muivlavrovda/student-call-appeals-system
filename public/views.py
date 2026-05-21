from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Публичная главная страница с кратким описанием сервиса."""

    template_name = "public/home.html"
