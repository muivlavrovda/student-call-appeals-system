import pytest
from django import forms

from core.forms import INVALID_CLASS, BootstrapFormMixin


class _SampleForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField()
    agree = forms.BooleanField(required=False)
    choice = forms.ChoiceField(choices=[("a", "A"), ("b", "B")])


@pytest.mark.unit
def test_text_widget_gets_form_control_class():
    form = _SampleForm()
    assert "form-control" in form.fields["name"].widget.attrs["class"]


@pytest.mark.unit
def test_checkbox_widget_gets_form_check_class():
    form = _SampleForm()
    assert form.fields["agree"].widget.attrs["class"] == "form-check-input"


@pytest.mark.unit
def test_select_widget_gets_form_select_class():
    form = _SampleForm()
    assert form.fields["choice"].widget.attrs["class"] == "form-select"


@pytest.mark.unit
def test_invalid_field_gets_invalid_class_after_validation():
    form = _SampleForm(data={"name": "", "choice": "a"})

    assert form.is_valid() is False
    assert INVALID_CLASS in form.fields["name"].widget.attrs["class"]
    # Поле без ошибки остается без класса ошибки.
    assert INVALID_CLASS not in form.fields["choice"].widget.attrs["class"]


@pytest.mark.unit
def test_existing_classes_are_preserved_and_not_duplicated():
    class _Pre(BootstrapFormMixin, forms.Form):
        name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))

    form = _Pre()
    assert form.fields["name"].widget.attrs["class"].split().count("form-control") == 1
