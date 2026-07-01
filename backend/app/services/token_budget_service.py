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
        return len(text.split())


class TokenBudgetService:
    def __init__(self, max_tokens: int = 64000) -> None:
        self.max_tokens = max_tokens

    def select(self, items: list[BudgetItem]) -> BudgetSelection:
        indexed_items = list(enumerate(items))
        required = [(index, item) for index, item in indexed_items if item.required]
        optional = sorted(
            [(index, item) for index, item in indexed_items if not item.required],
            key=lambda indexed_item: indexed_item[1].priority,
            reverse=True,
        )
        selected: list[tuple[int, BudgetItem]] = []
        dropped: list[str] = []
        total = 0

        for index, item in required + optional:
            if total + item.tokens <= self.max_tokens:
                selected.append((index, item))
                total += item.tokens
            else:
                dropped.append(item.key)

        selected.sort(key=lambda indexed_item: indexed_item[0])
        return BudgetSelection(
            items=[item for _, item in selected],
            total_tokens=total,
            dropped_keys=dropped,
        )
