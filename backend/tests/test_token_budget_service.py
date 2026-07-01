from app.services.token_budget_service import BudgetItem, TokenBudgetService


def test_budget_keeps_required_items_and_drops_low_priority_overflow():
    service = TokenBudgetService(max_tokens=10)
    selected = service.select(
        [
            BudgetItem(key="system", text="one two", tokens=2, priority=100, required=True),
            BudgetItem(key="current", text="three four", tokens=2, priority=90, required=True),
            BudgetItem(key="retrieval-low", text="a b c d e f g", tokens=7, priority=10),
            BudgetItem(key="summary", text="five six", tokens=2, priority=50),
        ]
    )

    assert [item.key for item in selected.items] == ["system", "current", "summary"]
    assert selected.total_tokens == 6
    assert selected.dropped_keys == ["retrieval-low"]
