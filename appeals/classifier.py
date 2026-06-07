"""Классификация телефонного обращения с помощью ИИ-модели.

По краткому описанию звонка модель подбирает категорию обращения из числа уже
заведённых в системе, а отдел определяется выбранной категорией. Все категории и
их описания передаются в запрос, поэтому подбор опирается на реальные данные.

Сервис устойчив к сбоям: если ИИ не настроен или недоступен (нет ключа, модель
не отвечает, закончились средства), он не поднимает исключение в представление, а
возвращает результат со статусом, по которому интерфейс показывает обычную форму
с ручным выбором. Каждый вызов модели — удачный или нет — фиксируется в журнале
``AILog`` для контроля расхода и отладки.
"""

import json
import time
from dataclasses import dataclass
from enum import Enum

import instructor
import structlog
from django.conf import settings
from django.utils import timezone
from django.utils.translation import get_language
from openai import OpenAI
from pydantic import BaseModel, Field

from appeals.models import AILog, AppealCategory
from core.ai import compute_cost

logger = structlog.get_logger(__name__)

# Отключаем «размышления» модели: для классификации они не нужны и только
# увеличивают задержку и расход токенов (см. подбор модели в обсуждении).
_THINKING_DISABLED = {"thinking": {"type": "disabled"}}
_MAX_TOKENS = 400


class Suggestion(BaseModel):
    """Структурированный ответ модели по одному обращению."""

    category_id: int | None = Field(
        default=None,
        description="ID выбранной категории из списка или null, если определить не удалось",
    )
    summary: str = Field(
        default="",
        description="Краткая тема обращения, 3-5 слов",
    )
    confident: bool = Field(
        description="true, если категория определена уверенно",
    )
    reason: str = Field(
        description="Краткое обоснование выбора на языке интерфейса",
    )


class ClassifyStatus(str, Enum):
    """Итог классификации с точки зрения интерфейса."""

    DISABLED = "disabled"  # ИИ не настроен — функции нет
    OK = "ok"  # категория подобрана
    UNDECIDED = "undecided"  # модель не смогла определить категорию
    UNAVAILABLE = "unavailable"  # ИИ настроен, но недоступен или дал сбой


@dataclass(frozen=True)
class ClassifyResult:
    """Результат классификации для представления."""

    status: ClassifyStatus
    category: AppealCategory | None = None
    summary: str = ""
    reason: str = ""


def ai_enabled() -> bool:
    """ИИ-классификация включена, если задана конфигурация подключения."""
    return settings.AI_CONFIG is not None


def classify_appeal(description: str) -> ClassifyResult:
    """Подбирает категорию обращения по описанию звонка.

    Никогда не поднимает исключение наружу: при любой проблеме с ИИ возвращает
    статус ``UNAVAILABLE`` (или ``DISABLED``), а ошибку пишет в журнал и в лог.
    """
    config = settings.AI_CONFIG
    if config is None:
        return ClassifyResult(status=ClassifyStatus.DISABLED)

    categories = list(AppealCategory.objects.filter(is_active=True).select_related("department"))
    language = get_language() or settings.LANGUAGE_CODE
    system_prompt = _build_system_prompt(categories, language=language)
    user_prompt = _build_user_prompt(description)

    started = time.monotonic()
    try:
        suggestion, completion = _call_model(config, system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001 — любой сбой ИИ не должен ронять форму
        logger.warning("ai_classify_failed", error=str(exc))
        _log_call(
            config=config,
            description=description,
            status=AILog.Status.ERROR,
            latency_ms=_elapsed_ms(started),
            error=str(exc),
        )
        return ClassifyResult(status=ClassifyStatus.UNAVAILABLE)

    latency_ms = _elapsed_ms(started)
    category = _resolve_category(suggestion, categories)

    if category is None or not suggestion.confident:
        _log_call(
            config=config,
            description=description,
            status=AILog.Status.UNDECIDED,
            suggestion=suggestion,
            completion=completion,
            latency_ms=latency_ms,
        )
        return ClassifyResult(status=ClassifyStatus.UNDECIDED, reason=suggestion.reason)

    _log_call(
        config=config,
        description=description,
        status=AILog.Status.OK,
        suggestion=suggestion,
        category=category,
        completion=completion,
        latency_ms=latency_ms,
    )
    return ClassifyResult(
        status=ClassifyStatus.OK,
        category=category,
        summary=suggestion.summary,
        reason=suggestion.reason,
    )


def _call_model(config, system_prompt: str, user_prompt: str):
    """Делает запрос к модели и возвращает (Suggestion, сырой ответ completion)."""
    raw_client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
    suggestion, completion = client.chat.completions.create_with_completion(
        model=config.model,
        response_model=Suggestion,
        max_tokens=_MAX_TOKENS,
        extra_body=_THINKING_DISABLED,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return suggestion, completion


def _build_system_prompt(categories: list[AppealCategory], *, language: str) -> str:
    """Статичная часть запроса: инструкция и список категорий с описаниями.

    Постоянная часть идёт в системное сообщение первой — так провайдер кэширует
    префикс между запросами, и оплачивается фактически только описание звонка.
    """
    catalogue = [
        {
            "id": category.pk,
            "category": category.name,
            "department": category.department.name,
            "description": category.description,
        }
        for category in categories
    ]
    return (
        "Ты помощник оператора в журнале телефонных обращений обучающихся. "
        "По описанию звонка выбери ОДНУ наиболее подходящую категорию из списка. "
        "Отдел определяется выбранной категорией, отдельно его выбирать не нужно. "
        "Если ни одна категория явно не подходит или описание непонятно — верни "
        "category_id = null и confident = false, не угадывай. "
        f"Обоснование (reason) и тему (summary) пиши на языке с кодом '{language}'.\n\n"
        "Категории (JSON):\n"
        f"{json.dumps(catalogue, ensure_ascii=False)}\n\n"
        "Ответ верни строго в JSON по заданной схеме."
    )


def _build_user_prompt(description: str) -> str:
    """Изменяемая часть запроса — только описание конкретного звонка."""
    return f'Описание звонка: "{description.strip()}"'


def _resolve_category(
    suggestion: Suggestion,
    categories: list[AppealCategory],
) -> AppealCategory | None:
    """Сопоставляет выбранный моделью id с реальной категорией из списка."""
    if suggestion.category_id is None:
        return None
    by_id = {category.pk: category for category in categories}
    return by_id.get(suggestion.category_id)


def _log_call(
    *,
    config,
    description: str,
    status: str,
    suggestion: Suggestion | None = None,
    category: AppealCategory | None = None,
    completion=None,
    latency_ms: int,
    error: str = "",
) -> None:
    """Сохраняет запись о вызове модели в журнал ``AILog``."""
    usage = getattr(completion, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    cache_hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
    cache_miss = getattr(usage, "prompt_cache_miss_tokens", 0) or 0

    AILog.objects.create(
        created_at=timezone.now(),
        model=config.model,
        status=status,
        description_in=description,
        chosen_category=category,
        summary_out=suggestion.summary if suggestion else "",
        reason=suggestion.reason if suggestion else "",
        prompt_tokens=prompt_tokens,
        cache_hit_tokens=cache_hit,
        cache_miss_tokens=cache_miss,
        completion_tokens=completion_tokens,
        cost_usd=compute_cost(
            config.model,
            cache_hit_tokens=cache_hit,
            cache_miss_tokens=cache_miss,
            completion_tokens=completion_tokens,
        ),
        latency_ms=latency_ms,
        raw_request=_raw_request(config, description),
        raw_response=_raw_response(completion),
        error=error,
    )


def _raw_request(config, description: str) -> dict:
    return {"model": config.model, "description": description}


def _raw_response(completion) -> dict | None:
    if completion is None:
        return None
    try:
        return completion.model_dump(mode="json")
    except Exception:  # noqa: BLE001 — сырой ответ для отладки не критичен
        return {"repr": repr(completion)}


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
