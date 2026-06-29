"""Provider-neutral normalization for extraction usage, cost, and timing."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict


class UsageResult(TypedDict):
    """Normalized observability fields returned by an extraction attempt."""

    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    extraction_time_ms: int | None


@dataclass(frozen=True, slots=True)
class TokenPricing:
    """Explicit per-million-token prices supplied by the provider integration."""

    input_cost_per_million_tokens: Decimal
    output_cost_per_million_tokens: Decimal


@dataclass(slots=True)
class ExtractionTiming:
    """Timing result populated when an extraction timing context exits."""

    extraction_time_ms: int | None = None


def _normalize_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _supported_rate(value: object) -> Decimal | None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        return None
    return value


def calculate_estimated_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    pricing: TokenPricing | None,
) -> float | None:
    """Calculate total cost only when both counts and explicit prices are valid."""

    normalized_input = _normalize_count(input_tokens)
    normalized_output = _normalize_count(output_tokens)
    if normalized_input is None or normalized_output is None or pricing is None:
        return None

    input_rate = _supported_rate(pricing.input_cost_per_million_tokens)
    output_rate = _supported_rate(pricing.output_cost_per_million_tokens)
    if input_rate is None or output_rate is None:
        return None

    estimated_cost = (
        Decimal(normalized_input) * input_rate
        + Decimal(normalized_output) * output_rate
    ) / Decimal(1_000_000)
    result = float(estimated_cost)
    return result if math.isfinite(result) else None


def normalize_usage(
    usage_metadata: Mapping[str, object] | None,
    *,
    pricing: TokenPricing | None = None,
    extraction_time_ms: int | None = None,
) -> UsageResult:
    """Normalize optional provider usage without assuming a response-object type."""

    metadata = usage_metadata or {}
    input_tokens = _normalize_count(metadata.get("input_tokens"))
    output_tokens = _normalize_count(metadata.get("output_tokens"))
    normalized_time = _normalize_count(extraction_time_ms)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": calculate_estimated_cost_usd(
            input_tokens,
            output_tokens,
            pricing,
        ),
        "extraction_time_ms": normalized_time,
    }


@contextmanager
def track_extraction_time(
    *,
    clock: Callable[[], float] = time.monotonic,
) -> Iterator[ExtractionTiming]:
    """Measure an attempted extraction, including attempts that raise."""

    timing = ExtractionTiming()
    started_at = clock()
    try:
        yield timing
    finally:
        elapsed_seconds = clock() - started_at
        if math.isfinite(elapsed_seconds) and elapsed_seconds >= 0:
            timing.extraction_time_ms = int(elapsed_seconds * 1_000)
