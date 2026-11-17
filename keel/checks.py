from calendar import monthrange
from datetime import date
from decimal import Decimal

from .models import Payment, PaymentResult, Status, Transaction


def check_payments(
    payments: list[Payment], transactions: list[Transaction], today: date
) -> list[PaymentResult]:
    """Check the calendar month through today without changing the inputs."""
    cycle_start = today.replace(day=1)
    cycle = sorted(
        (tx for tx in transactions if cycle_start <= tx.date <= today),
        key=lambda tx: tx.date,
    )
    results = []
    for payment in payments:
        due = today.replace(
            day=min(payment.due_day, monthrange(today.year, today.month)[1])
        )
        debits: list[Decimal] = []
        returned = False
        for tx in cycle:
            if payment.merchant_match.strip().casefold() not in tx.description.casefold():
                continue
            if tx.amount < 0 and abs(-tx.amount - payment.expected_amount) <= payment.tolerance:
                debits.append(-tx.amount)
            elif tx.amount > 0 and tx.amount in debits:
                debits.remove(tx.amount)
                returned = True
        if debits:
            status = Status.PAID
        elif returned:
            status = Status.RETURNED
        elif (today - due).days > payment.grace_days:
            status = Status.MISSED
        else:
            status = Status.PENDING
        results.append(PaymentResult(payment, due, status))
    return results


def check_low_balance(
    results: list[PaymentResult],
    balance: Decimal,
    today: date,
    warning_days: int,
    buffer: Decimal,
) -> list[PaymentResult]:
    """Flag unpaid payments due this month within the inclusive warning window."""
    return [
        result
        for result in results
        if result.status != Status.PAID
        and 0 <= (result.due_date - today).days <= warning_days
        and balance < result.payment.expected_amount + buffer
    ]
