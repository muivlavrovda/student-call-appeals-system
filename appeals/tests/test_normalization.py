import pytest
from django.core.exceptions import ValidationError

from appeals.models import normalize_name_key, normalize_phone, normalize_spaces, validate_phone


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  учебный   отдел  ", "учебный отдел"),
        ("иванов\tиван\nиванович", "иванов иван иванович"),
        ("one", "one"),
        ("", ""),
    ],
)
def test_normalize_spaces(value, expected):
    assert normalize_spaces(value) == expected


@pytest.mark.unit
def test_normalize_name_key_collapses_spaces_and_casefolds():
    assert normalize_name_key("  Аптечка   Первая  ") == "аптечка первая"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+7 (906) 123-45-67", "79061234567"),
        ("8 906 123 45 67", "79061234567"),
        ("9061234567", "79061234567"),
        ("79061234567", "79061234567"),
        ("123", "123"),
    ],
)
def test_normalize_phone(value, expected):
    assert normalize_phone(value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "+7 (906) 123-45-67",
        "8 906 123 45 67",
        "9061234567",
        "79061234567",
    ],
)
def test_validate_phone_accepts_supported_formats(value):
    validate_phone(value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "123",
        "69061234567",
        "+1 555 123 45 67",
        "not a phone",
    ],
)
def test_validate_phone_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        validate_phone(value)
