from django import forms

INVALID_CLASS = "is-invalid"


def _control_class_for(widget: forms.Widget) -> str:
    """Подбирает класс Bootstrap под тип виджета."""
    if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
        return "form-check-input"
    if isinstance(widget, forms.Select):
        return "form-select"
    return "form-control"


def _add_class(widget: forms.Widget, css_class: str) -> None:
    classes = widget.attrs.get("class", "").split()
    if css_class not in classes:
        classes.append(css_class)
        widget.attrs["class"] = " ".join(classes)


class BootstrapFormMixin:
    """Оформляет поля формы под Bootstrap.

    Базовый класс оформления добавляется к каждому виджету при создании формы,
    а класс ошибки — после валидации, чтобы поле подсвечивалось красной рамкой.
    Сообщения об ошибках выводит шаблон поля.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _add_class(field.widget, _control_class_for(field.widget))

    def is_valid(self) -> bool:
        valid = super().is_valid()
        for field_name in self.errors:
            if field_name in self.fields:
                _add_class(self.fields[field_name].widget, INVALID_CLASS)
        return valid
