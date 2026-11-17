import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from .models import Transaction, money


class BankProvider(Protocol):
    def get_transactions(self) -> list[Transaction]: ...

    def get_balance(self) -> Decimal: ...


class MockProvider:
    def __init__(self, fixture: str, fixtures_dir: Path) -> None:
        if not fixture or Path(fixture).name != fixture or fixture in {".", ".."}:
            raise ValueError("fixture must be a scenario name, not a path")
        self.directory = fixtures_dir / fixture

    def get_transactions(self) -> list[Transaction]:
        with (self.directory / "transactions.json").open(encoding="utf-8") as file:
            data = json.load(file, parse_float=Decimal)
        return [
            Transaction(
                date=date.fromisoformat(item["date"]),
                description=item["description"],
                amount=money(item["amount"]),
            )
            for item in data
        ]

    def get_balance(self) -> Decimal:
        with (self.directory / "balances.json").open(encoding="utf-8") as file:
            return money(json.load(file, parse_float=Decimal)["available"])
