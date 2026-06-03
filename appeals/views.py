from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from appeals.access import (
    can_close_appeal,
    can_comment_appeal,
    can_start_appeal_processing,
    can_transfer_appeal,
    can_view_appeal,
    visible_appeals_for,
)
from appeals.exports import report_to_docx, report_to_xlsx
from appeals.forms import (
    AppealCloseForm,
    AppealCommentForm,
    AppealCreateForm,
    AppealFilterForm,
    AppealTransferForm,
)
from appeals.models import Appeal, normalize_phone
from appeals.permissions import (
    ADD_APPEAL_PERMISSION,
    CLOSE_APPEAL_PERMISSION,
    COMMENT_APPEAL_PERMISSION,
    START_APPEAL_PROCESSING_PERMISSION,
    TRANSFER_APPEAL_PERMISSION,
    VIEW_APPEAL_PERMISSION,
)
from appeals.report_storage import list_reports, open_report, save_report
from appeals.reports import build_appeal_report
from appeals.services import (
    add_appeal_comment,
    close_appeal,
    create_appeal,
    start_appeal_processing,
    transfer_appeal,
)


class AppealListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список обращений, доступных текущему пользователю.

    Состав списка определяется слоем доступа: оператор видит свои заявки,
    ответственный сотрудник — заявки своих отделов, администратор — все.
    """

    permission_required = VIEW_APPEAL_PERMISSION
    template_name = "appeals/appeal_list.html"
    context_object_name = "appeals"
    paginate_by = 20

    def get_filter_form(self):
        # Форму создаём один раз за запрос: ей пользуются и отбор заявок,
        # и отрисовка панели фильтров в контексте.
        if not hasattr(self, "_filter_form"):
            self._filter_form = AppealFilterForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        # Фильтры применяются поверх доступных пользователю заявок, поэтому
        # отбор не может расширить видимость за пределы прав доступа.
        queryset = visible_appeals_for(self.request.user).select_related(
            "category",
            "department",
        )

        form = self.get_filter_form()
        if not form.is_valid():
            return queryset.order_by(AppealFilterForm.DEFAULT_SORT)

        data = form.cleaned_data
        if data.get("q"):
            queryset = self._apply_search(queryset, data["q"])
        if data.get("status"):
            queryset = queryset.filter(status=data["status"])
        if data.get("category"):
            queryset = queryset.filter(category=data["category"])
        if data.get("department"):
            queryset = queryset.filter(department=data["department"])

        return queryset.order_by(data["sort"])

    def _apply_search(self, queryset, query):
        # Телефон в базе хранится в нормализованном виде, поэтому поисковый
        # запрос нормализуем так же — иначе "+7 900…" не найдёт "7900…".
        phone_query = normalize_phone(query)
        filters = Q(student_full_name__icontains=query) | Q(summary__icontains=query)
        if phone_query:
            filters |= Q(student_phone__icontains=phone_query)
        return queryset.filter(filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"label": "Мои обращения"}]
        context["filter_form"] = self.get_filter_form()
        # Признак активного фильтра — чтобы отличить пустую выдачу от
        # «ничего не найдено» и показать кнопку сброса.
        context["filters_active"] = bool(self.request.GET)
        context["querystring"] = self._querystring_without_page()
        return context

    def _querystring_without_page(self):
        # Прочие параметры запроса без page — чтобы ссылки пагинации сохраняли
        # фильтры и сортировку, а не сбрасывали их при переходе на страницу.
        params = self.request.GET.copy()
        params.pop("page", None)
        return params.urlencode()


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
        appeal = self.object
        context["breadcrumbs"] = [
            {"label": "Мои обращения", "url": reverse("appeals:appeal_list")},
            {"label": f"Обращение №{appeal.pk}"},
        ]
        context["history_events"] = appeal.history_events.select_related("actor")
        context["comments"] = appeal.comments.select_related("author")
        context["can_comment"] = can_comment_appeal(self.request.user, appeal)
        context["comment_form"] = AppealCommentForm()
        context["can_start_processing"] = (
            appeal.status == Appeal.Status.NEW
            and can_start_appeal_processing(self.request.user, appeal)
        )
        context["can_close"] = appeal.status != Appeal.Status.CLOSED and can_close_appeal(
            self.request.user, appeal
        )
        context["can_transfer"] = appeal.status != Appeal.Status.CLOSED and can_transfer_appeal(
            self.request.user, appeal
        )
        return context


class AppealCommentCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Добавление комментария к обращению из его карточки.

    Сохранение делегируется сервису ``add_appeal_comment``; результат
    показывается сообщением, после чего пользователь возвращается в карточку.
    """

    permission_required = COMMENT_APPEAL_PERMISSION

    def post(self, request, pk):
        # Ищем только среди доступных заявок: недоступная заявка даёт 404 и не
        # раскрывает своё существование, как и в карточке. Право комментировать
        # в принципе уже проверено миксином доступа.
        appeal = get_object_or_404(visible_appeals_for(request.user), pk=pk)

        form = AppealCommentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Введите текст комментария.")
            return self._redirect_to_appeal(appeal)

        try:
            add_appeal_comment(
                appeal=appeal,
                author=request.user,
                text=form.cleaned_data["text"],
            )
        except ValidationError:
            messages.error(request, "Нельзя комментировать закрытое обращение.")
            return self._redirect_to_appeal(appeal)

        messages.success(request, "Комментарий добавлен.")
        return self._redirect_to_appeal(appeal)

    def _redirect_to_appeal(self, appeal):
        url = reverse("appeals:appeal_detail", kwargs={"pk": appeal.pk})
        return redirect(f"{url}#comments")


class AppealStartProcessingView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Перевод нового обращения в работу ответственным сотрудником.

    Состояние меняет сервис ``start_appeal_processing``; результат показывается
    сообщением, после чего пользователь возвращается в карточку обращения.
    """

    permission_required = START_APPEAL_PROCESSING_PERMISSION

    def post(self, request, pk):
        appeal = get_object_or_404(visible_appeals_for(request.user), pk=pk)
        if not can_start_appeal_processing(request.user, appeal):
            raise PermissionDenied

        try:
            start_appeal_processing(appeal=appeal, started_by=request.user)
        except ValidationError:
            messages.error(request, "Обращение уже взято в работу.")
        else:
            messages.success(request, "Обращение взято в работу.")

        return redirect("appeals:appeal_detail", pk=appeal.pk)


class AppealCloseView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Закрытие обращения с указанием результата обработки.

    Сохранение делегируется сервису ``close_appeal``; при гонке состояний
    ошибка сервиса показывается на форме, а не приводит к сбою.
    """

    permission_required = CLOSE_APPEAL_PERMISSION
    template_name = "appeals/appeal_close.html"
    form_class = AppealCloseForm

    def get(self, request, *args, **kwargs):
        self._load_appeal()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._load_appeal()
        return super().post(request, *args, **kwargs)

    def _load_appeal(self):
        # Закрывать можно любую доступную заявку, поэтому ограничение выборки
        # доступными заявками (404 при отсутствии, без раскрытия существования)
        # вместе с миксином прав полностью закрывают доступ — отдельная
        # проверка по объекту не нужна.
        self.appeal = get_object_or_404(
            visible_appeals_for(self.request.user),
            pk=self.kwargs["pk"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["appeal"] = self.appeal
        context["breadcrumbs"] = [
            {"label": "Мои обращения", "url": reverse("appeals:appeal_list")},
            {
                "label": f"Обращение №{self.appeal.pk}",
                "url": reverse("appeals:appeal_detail", kwargs={"pk": self.appeal.pk}),
            },
            {"label": "Закрытие"},
        ]
        return context

    def form_valid(self, form):
        try:
            close_appeal(
                appeal=self.appeal,
                closed_by=self.request.user,
                result=form.cleaned_data["result"],
            )
        except ValidationError as error:
            for message in error.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "Обращение закрыто.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("appeals:appeal_detail", kwargs={"pk": self.appeal.pk})


class AppealTransferView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Перенос обращения в другую категорию или отдел.

    Поля формы предзаполняются текущим маршрутом; сохранение делегируется
    сервису ``transfer_appeal``, а его ошибки показываются на форме.
    """

    permission_required = TRANSFER_APPEAL_PERMISSION
    template_name = "appeals/appeal_transfer.html"
    form_class = AppealTransferForm

    def get(self, request, *args, **kwargs):
        self._load_appeal()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._load_appeal()
        return super().post(request, *args, **kwargs)

    def _load_appeal(self):
        # Доступные заявки дают 404 для чужого id (без раскрытия), а перенос
        # дополнительно ограничен отделом, поэтому проверяем его по объекту.
        self.appeal = get_object_or_404(
            visible_appeals_for(self.request.user),
            pk=self.kwargs["pk"],
        )
        if not can_transfer_appeal(self.request.user, self.appeal):
            raise PermissionDenied

    def get_initial(self):
        return {
            "category": self.appeal.category_id,
            "department": self.appeal.department_id,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["appeal"] = self.appeal
        context["breadcrumbs"] = [
            {"label": "Мои обращения", "url": reverse("appeals:appeal_list")},
            {
                "label": f"Обращение №{self.appeal.pk}",
                "url": reverse("appeals:appeal_detail", kwargs={"pk": self.appeal.pk}),
            },
            {"label": "Перенаправление"},
        ]
        return context

    def form_valid(self, form):
        try:
            transfer_appeal(
                appeal=self.appeal,
                transferred_by=self.request.user,
                category=form.cleaned_data["category"],
                department=form.cleaned_data["department"],
            )
        except ValidationError as error:
            for message in error.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, "Обращение перенаправлено.")
        return super().form_valid(form)

    def get_success_url(self):
        # Перенос в чужой отдел выводит заявку из зоны видимости сотрудника,
        # поэтому возвращаем в карточку только если она ещё доступна, иначе —
        # к списку обращений, чтобы не упереться в 404.
        self.appeal.refresh_from_db()
        if can_view_appeal(self.request.user, self.appeal):
            return reverse("appeals:appeal_detail", kwargs={"pk": self.appeal.pk})
        return reverse("appeals:appeal_list")


class AppealReportMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Общий доступ и сбор сводки для страницы отчёта и его выгрузок.

    Отчёт строится по тем же доступным пользователю заявкам, что и список,
    поэтому оператор видит сводку по своим обращениям, ответственный — по
    обращениям своих отделов, администратор — по всем. Отдельного права не
    требуется: достаточно права на просмотр.
    """

    permission_required = VIEW_APPEAL_PERMISSION

    def get_report(self):
        return build_appeal_report(visible_appeals_for(self.request.user))


# Типы содержимого офисных форматов — общие для выгрузки и для скачивания
# сохранённых на диск файлов.
REPORT_CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class AppealReportView(AppealReportMixin, TemplateView):
    """Страница сводного отчёта по обращениям с кнопками выгрузки.

    Помимо текущей сводки, страница показывает список ранее сформированных
    файлов отчётов, сохранённых в файловой системе.
    """

    template_name = "appeals/appeal_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.get_report()
        context["stored_reports"] = list_reports()
        context["breadcrumbs"] = [
            {"label": "Мои обращения", "url": reverse("appeals:appeal_list")},
            {"label": "Отчёты"},
        ]
        return context


class AppealReportXlsxView(AppealReportMixin, View):
    """Выгрузка сводного отчёта в файл .xlsx с сохранением копии на диск."""

    def get(self, request):
        generated_at = timezone.now()
        content = report_to_xlsx(self.get_report(), generated_at=generated_at)
        save_report(content, fmt="xlsx", generated_at=generated_at)
        return _file_response(
            content,
            filename="appeal-report.xlsx",
            content_type=REPORT_CONTENT_TYPES["xlsx"],
        )


class AppealReportDocxView(AppealReportMixin, View):
    """Выгрузка сводного отчёта в файл .docx с сохранением копии на диск."""

    def get(self, request):
        generated_at = timezone.now()
        content = report_to_docx(self.get_report(), generated_at=generated_at)
        save_report(content, fmt="docx", generated_at=generated_at)
        return _file_response(
            content,
            filename="appeal-report.docx",
            content_type=REPORT_CONTENT_TYPES["docx"],
        )


class AppealReportFileView(AppealReportMixin, View):
    """Скачивание ранее сохранённого на диск файла отчёта.

    Доступ закрыт тем же правом, что и сами отчёты: сохранённые файлы содержат
    сводку по обращениям и не должны быть доступны без авторизации.
    """

    def get(self, request, name):
        stored_file = open_report(name)
        if stored_file is None:
            raise Http404("Файл отчёта не найден.")

        fmt = name.rsplit(".", 1)[-1].lower()
        content_type = REPORT_CONTENT_TYPES.get(fmt, "application/octet-stream")
        with stored_file:
            content = stored_file.read()
        return _file_response(content, filename=name, content_type=content_type)


def _file_response(content: bytes, *, filename: str, content_type: str) -> HttpResponse:
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
