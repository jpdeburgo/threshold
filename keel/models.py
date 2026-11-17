from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


def money(value: str | int | float | Decimal) -> Decimal:
    amount = Decimal(str(value))
    if not amount.is_finite():
        raise ValueError("Amounts must be finite")
    return amount


@dataclass(frozen=True)
class Payment:
    name: str
    expected_amount: Decimal
    due_day: int
    merchant_match: str
    tolerance: Decimal = Decimal("0.00")
    grace_days: int = 0

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.merchant_match.strip():
            raise ValueError("Payment name and merchant_match must not be empty")
        if not 1 <= self.due_day <= 31:
            raise ValueError("due_day must be between 1 and 31")
        if not self.expected_amount.is_finite() or self.expected_amount <= 0:
            raise ValueError("expected_amount must be positive and finite")
        if not self.tolerance.is_finite() or self.tolerance < 0:
            raise ValueError("tolerance must be nonnegative and finite")
        if self.grace_days < 0:
            raise ValueError("grace_days must be nonnegative")


@dataclass(frozen=True)
class Transaction:
    date: date
    description: str
    amount: Decimal


class Status(StrEnum):
    PAID = "PAID"
    PENDING = "PENDING"
    MISSED = "MISSED"
    RETURNED = "RETURNED"


@dataclass(frozen=True)
class PaymentResult:
    payment: Payment
    due_date: date
    status: Status
