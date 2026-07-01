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


def test_duplicate_key_selected_items_preserve_original_input_order():
    service = TokenBudgetService(max_tokens=10)
    selected = service.select(
        [
            BudgetItem(key="duplicate", text="first", tokens=1, priority=10),
            BudgetItem(key="middle", text="middle", tokens=1, priority=50),
            BudgetItem(key="duplicate", text="second", tokens=1, priority=90),
        ]
    )

    assert [item.text for item in selected.items] == ["first", "middle", "second"]


def test_same_priority_optional_items_preserve_input_order():
    service = TokenBudgetService(max_tokens=10)
    selected = service.select(
        [
            BudgetItem(key="first", text="one", tokens=1, priority=50),
            BudgetItem(key="second", text="two", tokens=1, priority=50),
            BudgetItem(key="third", text="three", tokens=1, priority=50),
        ]
    )

    assert [item.key for item in selected.items] == ["first", "second", "third"]


def test_exact_budget_fit_includes_fitting_item():
    service = TokenBudgetService(max_tokens=4)
    selected = service.select(
        [
            BudgetItem(key="required", text="one two", tokens=2, priority=100, required=True),
            BudgetItem(key="optional", text="three four", tokens=2, priority=50),
        ]
    )

    assert [item.key for item in selected.items] == ["required", "optional"]
    assert selected.total_tokens == 4
    assert selected.dropped_keys == []


def test_required_item_that_overflows_budget_is_dropped_deterministically():
    service = TokenBudgetService(max_tokens=3)
    selected = service.select(
        [
            BudgetItem(
                key="required-overflow",
                text="one two three four",
                tokens=4,
                priority=100,
                required=True,
            ),
            BudgetItem(key="optional-fit", text="one two", tokens=2, priority=10),
        ]
    )

    assert [item.key for item in selected.items] == ["optional-fit"]
    assert selected.total_tokens == 2
    assert selected.dropped_keys == ["required-overflow"]
