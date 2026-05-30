from django import forms

from appeals.models import AppealCategory, Department, normalize_phone
from core.forms import BootstrapFormMixin


class AppealCreateForm(BootstrapFormMixin, forms.Form):
    """Форма регистрации телефонного обращения оператором.

    Собирает данные звонка и маршрут заявки; сохранение выполняет сервис
    ``create_appeal``. Отдел необязателен — по умолчанию берется из категории.
    """

    student_full_name = forms.CharField(
        label="ФИО студента",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Иванов Иван Иванович",
                "autocomplete": "name",
                "autofocus": True,
            },
        ),
        error_messages={"required": "Укажите ФИО студента."},
    )

    student_phone = forms.CharField(
        label="Телефон",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "placeholder": "+7 (900) 000-00-00",
                "autocomplete": "tel",
                "inputmode": "tel",
            },
        ),
        error_messages={"required": "Укажите телефон студента."},
    )

    summary = forms.CharField(
        label="Тема",
        max_length=255,
        widget=forms.TextInput(
            attrs={"placeholder": "Коротко о сути обращения"},
        ),
        error_messages={"required": "Укажите тему обращения."},
    )

    category = forms.ModelChoiceField(
        label="Категория",
        queryset=AppealCategory.objects.none(),
        empty_label="Выберите категорию",
        error_messages={
            "required": "Выберите категорию обращения.",
            "invalid_choice": "Выберите категорию из списка.",
        },
    )

    department = forms.ModelChoiceField(
        label="Отдел",
        queryset=Department.objects.none(),
        required=False,
        empty_label="По категории",
        help_text="Оставьте пустым, чтобы определить отдел по категории.",
        error_messages={"invalid_choice": "Выберите отдел из списка."},
    )

    description = forms.CharField(
        label="Описание",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Подробное описание вопроса студента.",
            },
        ),
        error_messages={"required": "Опишите суть обращения."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = AppealCategory.objects.filter(
            is_active=True,
        ).select_related("department")
        self.fields["department"].queryset = Department.objects.filter(is_active=True)

    def clean_student_phone(self) -> str:
        return normalize_phone(self.cleaned_data["student_phone"])


class AppealCommentForm(BootstrapFormMixin, forms.Form):
    """Форма добавления комментария к обращению.

    Сохранение выполняет сервис ``add_appeal_comment``, который пишет
    комментарий и событие в историю и запрещает комментировать закрытые заявки.
    """

    text = forms.CharField(
        label="Комментарий",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Добавьте комментарий по обращению.",
            },
        ),
        error_messages={"required": "Введите текст комментария."},
    )


class AppealCloseForm(BootstrapFormMixin, forms.Form):
    """Форма закрытия обращения с указанием результата обработки.

    Сохранение выполняет сервис ``close_appeal``: он нормализует результат,
    переводит заявку в закрытый статус и пишет событие в историю.
    """

    result = forms.CharField(
        label="Результат обработки",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Опишите, как обращение было обработано.",
            },
        ),
        error_messages={"required": "Опишите результат обработки."},
    )


class AppealTransferForm(BootstrapFormMixin, forms.Form):
    """Форма переноса обращения в другую категорию или отдел.

    Поля предзаполняются текущим маршрутом заявки; сохранение выполняет сервис
    ``transfer_appeal``, который отклоняет неизменённый маршрут и закрытые заявки.
    """

    category = forms.ModelChoiceField(
        label="Категория",
        queryset=AppealCategory.objects.none(),
        error_messages={
            "required": "Выберите категорию обращения.",
            "invalid_choice": "Выберите категорию из списка.",
        },
    )

    department = forms.ModelChoiceField(
        label="Отдел",
        queryset=Department.objects.none(),
        error_messages={
            "required": "Выберите отдел.",
            "invalid_choice": "Выберите отдел из списка.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = AppealCategory.objects.filter(
            is_active=True,
        ).select_related("department")
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
