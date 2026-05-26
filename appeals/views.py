from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView

from appeals.access import visible_appeals_for
from appeals.forms import AppealCreateForm
from appeals.permissions import ADD_APPEAL_PERMISSION, VIEW_APPEAL_PERMISSION
from appeals.services import create_appeal


class AppealListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список обращений, доступных текущему пользователю.

    Состав списка определяется слоем доступа: оператор видит свои заявки,
    ответственный сотрудник — заявки своих отделов, администратор — все.
    """

    permission_required = VIEW_APPEAL_PERMISSION
    template_name = "appeals/appeal_list.html"
    context_object_name = "appeals"
    paginate_by = 20

    def get_queryset(self):
        return visible_appeals_for(self.request.user).select_related(
            "category",
            "department",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Мои обращения"}]
        return context


class AppealCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Регистрация нового телефонного обращения оператором.

    Сохранение делегируется сервису ``create_appeal``, который проверяет
    маршрут, считает срок обработки и пишет событие в историю заявки.
    """

    permission_required = ADD_APPEAL_PERMISSION
    template_name = "appeals/appeal_form.html"
    form_class = AppealCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"label": "Мои обращения", "url": reverse("appeals:appeal_list")},
            {"label": "Новое обращение"},
        ]
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            self.appeal = create_appeal(
                student_full_name=data["student_full_name"],
                student_phone=data["student_phone"],
                summary=data["summary"],
                description=data["description"],
                category=data["category"],
                department=data["department"],
                created_by=self.request.user,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)

        messages.success(self.request, "Обращение зарегистрировано.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("appeals:appeal_detail", kwargs={"pk": self.appeal.pk})


class AppealDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Карточка обращения с данными студента и маршрутом заявки.

    Поиск идет только по доступным пользователю заявкам, поэтому чужое или
    несуществующее обращение одинаково возвращает 404 и не раскрывает данные.
    """

    permission_required = VIEW_APPEAL_PERMISSION
    template_name = "appeals/appeal_detail.html"
    context_object_name = "appeal"

    def get_queryset(self):
        return visible_appeals_for(self.request.user).select_related(
            "category",
            "department",
            "created_by",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"label": "Мои обращения", "url": reverse("appeals:appeal_list")},
            {"label": f"Обращение №{self.object.pk}"},
        ]
        return context
