from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from .models import Payment, money


@dataclass(frozen=True)
class Config:
    payments: list[Payment]
    warning_days: int
    buffer: Decimal


def load_config(path: Path) -> Config:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    payments = [
        Payment(
            name=item["name"],
            expected_amount=money(item["expected_amount"]),
            due_day=item["due_day"],
            merchant_match=item["merchant_match"],
            tolerance=money(item["tolerance"]),
            grace_days=item["grace_days"],
        )
        for item in data["payments"]
    ]
    warning = data["low_balance"]
    days = warning["warning_days"]
    buffer = money(warning["buffer"])
    if not isinstance(days, int) or days < 0 or buffer < 0:
        raise ValueError("warning_days and buffer must be nonnegative")
    return Config(payments, days, buffer)
