from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from keel.checks import check_low_balance, check_payments
from keel.models import Payment, Status, Transaction


TODAY = date(2026, 11, 3)
PAYMENT = Payment("Rent", Decimal("1500"), 5, "RENT", Decimal("0.50"), 2)


def transaction(amount="-1500", day=2, description="rent payment"):
    return Transaction(date(2026, 11, day), description, Decimal(amount))


def status(transactions, today=TODAY, payment=PAYMENT):
    return check_payments([payment], transactions, today)[0].status


@pytest.mark.parametrize(
    ("day", "expected"),
    [(3, Status.PENDING), (5, Status.PENDING), (7, Status.PENDING), (8, Status.MISSED)],
)
def test_due_and_grace_boundaries(day, expected):
    assert status([], date(2026, 11, day)) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("-1500", Status.PAID),
        ("-1499.50", Status.PAID),
        ("-1500.50", Status.PAID),
        ("-1499.49", Status.PENDING),
        ("-1500.51", Status.PENDING),
        ("1500", Status.PENDING),
        ("0", Status.PENDING),
    ],
)
def test_debit_amount_and_inclusive_tolerance(amount, expected):
    assert status([transaction(amount)]) == expected


def test_merchant_is_case_insensitive_substring():
    assert status([transaction(description="BANK Rent PAYMENT")]) == Status.PAID
    assert status([transaction(description="GROCERIES")]) == Status.PENDING


def test_only_current_month_through_today_counts():
    transactions = [
        Transaction(date(2026, 10, 31), "RENT", Decimal("-1500")),
        Transaction(date(2025, 11, 2), "RENT", Decimal("-1500")),
        transaction(day=4),
    ]
    assert status(transactions) == Status.PENDING
    assert status([transaction(day=1)]) == Status.PAID


@pytest.mark.parametrize(
    ("transactions", "expected"),
    [
        ([transaction(), transaction("1500", 3)], Status.RETURNED),
        ([transaction("1500", 1), transaction()], Status.PAID),
        ([transaction(), transaction("1500", 2)], Status.RETURNED),
        ([transaction("1500", 2), transaction()], Status.PAID),
        ([transaction(), transaction("1499.99", 3)], Status.PAID),
        ([transaction(), transaction("1500", 3, "OTHER MERCHANT")], Status.PAID),
        ([transaction(), transaction("1500", 4)], Status.PAID),
        ([transaction("-1499.50"), transaction("1499.50", 3)], Status.RETURNED),
        ([transaction(), transaction("1500", 2), transaction(day=3)], Status.PAID),
        ([transaction(), transaction(), transaction("1500", 3)], Status.PAID),
        ([transaction(), transaction("1500", 2), transaction("1500", 3)], Status.RETURNED),
    ],
)
def test_returns_and_successful_retries(transactions, expected):
    assert status(transactions) == expected


def test_transactions_are_sorted_without_mutating_inputs():
    transactions = [transaction("1500", 3), transaction(day=1)]
    original = list(transactions)
    payments = [PAYMENT]
    assert check_payments(payments, transactions, TODAY)[0].status == Status.RETURNED
    assert transactions == original
    assert payments == [PAYMENT]


def test_returned_stays_returned_after_grace():
    assert status([transaction(), transaction("1500", 3)], date(2026, 11, 9)) == Status.RETURNED


@pytest.mark.parametrize(
    ("today", "due"),
    [
        (date(2026, 2, 28), date(2026, 2, 28)),
        (date(2028, 2, 29), date(2028, 2, 29)),
        (date(2026, 4, 30), date(2026, 4, 30)),
        (date(2026, 12, 31), date(2026, 12, 31)),
    ],
)
def test_month_end_due_day_is_clamped(today, due):
    result = check_payments([replace(PAYMENT, due_day=31)], [], today)[0]
    assert result.due_date == due
    assert result.status == Status.PENDING


@pytest.mark.parametrize(
    ("day", "balance", "expected"),
    [
        (1, "0", False),
        (2, "1599.99", True),
        (3, "1500", True),
        (5, "1599.99", True),
        (5, "1600", False),
        (5, "1600.01", False),
        (6, "0", False),
    ],
)
def test_low_balance_window_and_buffer(day, balance, expected):
    today = date(2026, 11, day)
    results = check_payments([PAYMENT], [], today)
    warnings = check_low_balance(results, Decimal(balance), today, 3, Decimal("100"))
    assert bool(warnings) is expected


def test_paid_payment_does_not_warn():
    results = check_payments([PAYMENT], [transaction()], TODAY)
    assert check_low_balance(results, Decimal("0"), TODAY, 3, Decimal("100")) == []


def test_returned_payment_can_warn_before_due_date():
    results = check_payments([PAYMENT], [transaction(), transaction("1500", 3)], TODAY)
    assert check_low_balance(results, Decimal("0"), TODAY, 3, Decimal("100")) == results


@pytest.mark.parametrize(
    "changes",
    [
        {"due_day": 0},
        {"due_day": 32},
        {"expected_amount": Decimal("0")},
        {"expected_amount": Decimal("NaN")},
        {"tolerance": Decimal("-0.01")},
        {"tolerance": Decimal("Infinity")},
        {"grace_days": -1},
        {"merchant_match": " "},
        {"name": ""},
    ],
)
def test_invalid_payment_is_rejected(changes):
    with pytest.raises(ValueError):
        replace(PAYMENT, **changes)


def test_empty_payments():
    assert check_payments([], [], TODAY) == []
