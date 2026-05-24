from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView

from appeals.access import visible_appeals_for
from appeals.permissions import VIEW_APPEAL_PERMISSION


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
