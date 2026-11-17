import argparse
from datetime import date
from decimal import DecimalException
from pathlib import Path

import yaml

from .checks import check_low_balance, check_payments
from .config import load_config
from .models import Status
from .notifiers import ConsoleNotifier, Notifier
from .providers import BankProvider, MockProvider


ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="keel")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Check this month's recurring payments")
    check.add_argument("--today", type=date.fromisoformat, default=date.today())
    check.add_argument("--fixture", required=True)
    args = parser.parse_args(argv)

    try:
        config = load_config(ROOT / "config.yaml")
        provider: BankProvider = MockProvider(args.fixture, ROOT / "fixtures")
        transactions = provider.get_transactions()
        balance = provider.get_balance()
        results = check_payments(config.payments, transactions, args.today)
        warnings = check_low_balance(
            results, balance, args.today, config.warning_days, config.buffer
        )
    except (OSError, ValueError, KeyError, TypeError, DecimalException, yaml.YAMLError) as exc:
        parser.error(str(exc))

    print(f"keel — {args.today:%Y-%m-%d} | Available balance: {balance:.2f}")
    print(f"{'Payment':<20} {'Amount':>10}  {'Due':<10}  Status")
    for result in results:
        print(
            f"{result.payment.name:<20} {result.payment.expected_amount:>10.2f}  "
            f"{result.due_date:%Y-%m-%d}  {result.status}"
        )
    notifier: Notifier = ConsoleNotifier()
    for result in results:
        if result.status in {Status.MISSED, Status.RETURNED}:
            notifier.notify(f"{result.payment.name}: {result.status}")
    for result in warnings:
        notifier.notify(
            f"{result.payment.name}: LOW BALANCE — {balance:.2f} available; "
            f"need {result.payment.expected_amount + config.buffer:.2f} "
            f"by {result.due_date:%Y-%m-%d}"
        )
    return 0
