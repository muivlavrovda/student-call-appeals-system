from types import SimpleNamespace
from unittest.mock import patch

import pytest

from appeals import classifier
from appeals.classifier import ClassifyStatus, Suggestion, ai_enabled, classify_appeal
from appeals.models import AILog
from appeals.tests.factories import AppealCategoryFactory
from core.ai import AIConfig


@pytest.fixture
def ai_config(settings):
    # Включаем ИИ для теста, не обращаясь к реальному API (вызов модели мокаем).
    settings.AI_CONFIG = AIConfig(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key="sk-test",
    )
    return settings.AI_CONFIG


def _fake_completion(prompt=590, hit=512, miss=78, out=40):
    usage = SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=out,
        prompt_cache_hit_tokens=hit,
        prompt_cache_miss_tokens=miss,
    )
    return SimpleNamespace(usage=usage, model_dump=lambda mode="json": {"ok": True})


@pytest.mark.django_db
@pytest.mark.unit
def test_classify_returns_disabled_when_no_config(settings):
    settings.AI_CONFIG = None

    result = classify_appeal("нужна справка")

    assert result.status is ClassifyStatus.DISABLED
    assert not ai_enabled()
    assert AILog.objects.count() == 0  # без ИИ ничего не вызываем и не логируем


@pytest.mark.django_db
@pytest.mark.integration
def test_classify_undecided_without_categories_and_skips_api(ai_config):
    # Нет активных категорий — выбирать не из чего, модель не дёргаем.
    with patch.object(classifier, "_call_model") as mocked:
        result = classify_appeal("нужна справка")

    mocked.assert_not_called()
    assert result.status is ClassifyStatus.UNDECIDED
    assert AILog.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
def test_classify_ok_resolves_category_and_logs(ai_config):
    category = AppealCategoryFactory()
    suggestion = Suggestion(
        category_id=category.pk,
        summary="Справка об обучении",
        confident=True,
        reason="Подходит по описанию.",
    )

    with patch.object(classifier, "_call_model", return_value=(suggestion, _fake_completion())):
        result = classify_appeal("нужна справка")

    assert result.status is ClassifyStatus.OK
    assert result.category == category
    assert result.summary == "Справка об обучении"

    log = AILog.objects.get()
    assert log.status == AILog.Status.OK
    assert log.chosen_category == category
    assert log.cache_hit_tokens == 512
    assert log.cost_usd > 0


@pytest.mark.django_db
@pytest.mark.integration
def test_classify_undecided_when_category_is_null(ai_config):
    AppealCategoryFactory()
    suggestion = Suggestion(category_id=None, summary="", confident=False, reason="Непонятно.")

    with patch.object(classifier, "_call_model", return_value=(suggestion, _fake_completion())):
        result = classify_appeal("во сколько обед")

    assert result.status is ClassifyStatus.UNDECIDED
    assert result.category is None
    assert result.reason == "Непонятно."
    assert AILog.objects.get().status == AILog.Status.UNDECIDED


@pytest.mark.django_db
@pytest.mark.integration
def test_classify_undecided_when_not_confident_even_if_id_given(ai_config):
    # Модель указала id, но не уверена — трактуем как «не определено».
    category = AppealCategoryFactory()
    suggestion = Suggestion(
        category_id=category.pk,
        summary="Возможно справка",
        confident=False,
        reason="Сомневаюсь.",
    )

    with patch.object(classifier, "_call_model", return_value=(suggestion, _fake_completion())):
        result = classify_appeal("что-то про учёбу")

    assert result.status is ClassifyStatus.UNDECIDED
    assert AILog.objects.get().status == AILog.Status.UNDECIDED


@pytest.mark.django_db
@pytest.mark.integration
def test_classify_unavailable_on_api_error_and_logs_error(ai_config):
    AppealCategoryFactory()

    with patch.object(classifier, "_call_model", side_effect=RuntimeError("connection refused")):
        result = classify_appeal("нужна справка")

    assert result.status is ClassifyStatus.UNAVAILABLE
    assert result.category is None

    log = AILog.objects.get()
    assert log.status == AILog.Status.ERROR
    assert "connection refused" in log.error


@pytest.mark.django_db
@pytest.mark.integration
def test_classify_ignores_unknown_category_id(ai_config):
    # Если модель вернула несуществующий id — это «не определено», а не падение.
    AppealCategoryFactory()
    suggestion = Suggestion(category_id=999999, summary="x", confident=True, reason="r")

    with patch.object(classifier, "_call_model", return_value=(suggestion, _fake_completion())):
        result = classify_appeal("текст")

    assert result.status is ClassifyStatus.UNDECIDED


@pytest.mark.unit
def test_call_model_passes_expected_parameters(ai_config):
    # Проверяем именно нашу обвязку запроса, не делая сетевого вызова: клиент
    # instructor подменён, важны переданные параметры (модель, отключённое
    # «мышление», роли сообщений).
    suggestion = Suggestion(category_id=1, summary="s", confident=True, reason="r")
    completion = _fake_completion()
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return suggestion, completion

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create_with_completion=fake_create))
    )

    with (
        patch.object(classifier, "OpenAI", return_value=SimpleNamespace()),
        patch.object(classifier.instructor, "from_openai", return_value=fake_client),
    ):
        got_suggestion, got_completion = classifier._call_model(
            ai_config, "system text", "user text"
        )

    assert got_suggestion is suggestion
    assert got_completion is completion
    assert captured["model"] == "deepseek-v4-flash"
    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}
    assert [m["role"] for m in captured["messages"]] == ["system", "user"]


@pytest.mark.unit
def test_raw_response_falls_back_to_repr_on_dump_error():
    class Boom:
        def model_dump(self, mode="json"):
            raise ValueError("cannot dump")

    raw = classifier._raw_response(Boom())

    assert "repr" in raw
