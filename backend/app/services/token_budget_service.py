"""Deterministic token budget assembly for chat working memory."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetItem:
    key: str
    text: str
    tokens: int
    priority: int
    required: bool = False


@dataclass(frozen=True)
class BudgetSelection:
    items: list[BudgetItem]
    total_tokens: int
    dropped_keys: list[str]


class SimpleTokenCounter:
    def count(self, text: str) -> int:
        return len([part for part in text.split() if part])


class TokenBudgetService:
    def __init__(self, max_tokens: int = 64000) -> None:
        self.max_tokens = max_tokens

    def select(self, items: list[BudgetItem]) -> BudgetSelection:
        required = [item for item in items if item.required]
        optional = sorted(
            [item for item in items if not item.required],
            key=lambda item: item.priority,
            reverse=True,
        )
        selected: list[BudgetItem] = []
        dropped: list[str] = []
        total = 0

        for item in required + optional:
            if total + item.tokens <= self.max_tokens:
                selected.append(item)
                total += item.tokens
            else:
                dropped.append(item.key)

        original_order = {item.key: index for index, item in enumerate(items)}
        selected.sort(key=lambda item: original_order[item.key])
        return BudgetSelection(items=selected, total_tokens=total, dropped_keys=dropped)
