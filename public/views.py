from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from public.forms import FeedbackForm


class HomeView(TemplateView):
    """Публичная главная страница с кратким описанием сервиса."""

    template_name = "public/home.html"


class AboutView(TemplateView):
    """Страница с описанием назначения и рамок сервиса."""

    template_name = "public/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "О сервисе"}]
        return context


class CategoriesView(TemplateView):
    """Страница с описанием основных категорий обращений."""

    template_name = "public/categories.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Категории обращений"}]
        return context


class HowToView(TemplateView):
    """Страница с порядком подачи телефонного обращения."""

    template_name = "public/how_to.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Как подать обращение"}]
        return context


class ProcessView(TemplateView):
    """Страница с описанием жизненного цикла заявки."""

    template_name = "public/process.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Порядок обработки"}]
        return context


class AnalyticsView(TemplateView):
    """Страница с описанием аналитики и отчетов по обращениям."""

    template_name = "public/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Аналитика и отчеты"}]
        return context


class FaqView(TemplateView):
    """Страница с ответами на частые вопросы о сервисе."""

    template_name = "public/faq.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Вопросы и ответы"}]
        return context


class ContactsView(TemplateView):
    """Страница с контактной информацией сервиса."""

    template_name = "public/contacts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Контакты"}]
        return context


class DocumentsView(TemplateView):
    """Страница со списком нормативных документов."""

    template_name = "public/documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Нормативные документы"}]
        return context


class FeedbackView(CreateView):
    """Публичная форма обратной связи.

    Сохраняет сообщение и по схеме PRG перенаправляет обратно на форму,
    чтобы повторная отправка по обновлению страницы не дублировала запись.
    """

    form_class = FeedbackForm
    template_name = "public/feedback.html"
    success_url = reverse_lazy("public:feedback")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Обратная связь"}]
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Спасибо! Ваше сообщение отправлено.",
        )
        return response
