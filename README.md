# keel

A minimal Python 3.11, offline personal-finance foundation. Checks this month's
rent and mortgage against local bank fixtures and prints a status table and
console alerts. No bank connections, API keys, database, or web service.

## Setup

From the repository root, with Python 3.11 installed:

```sh
python3.11 -m pip install pipenv
pipenv sync --dev
```

Dependencies are PyYAML and pytest (for tests). `Pipfile.lock` pins the environment;
`requirements.txt` also lists the two direct dependencies.
Installation may download dependencies; running the app and tests needs no network.

## Run

```sh
pipenv run python -m keel check --today 2026-11-03 --fixture all_paid
pipenv run python -m keel check --today 2026-11-03 --fixture rent_missed
pipenv run python -m keel check --today 2026-11-03 --fixture mortgage_returned
pipenv run python -m keel check --today 2026-11-03 --fixture low_balance
```

Inside `pipenv shell`, the command is simply:

```sh
python -m keel check --today 2026-11-03 --fixture all_paid
```

Omit `--today` to use the local date. The sample fixtures are for November 2026.
The low-balance example has 2250 available, below the mortgage's 2200 amount
plus the 100 buffer, two days before its due date.
Successful checks exit with code 0, including checks with alerts; invalid input
exits with code 2.

## Configuration and data

Edit `config.yaml` to set each payment's `name`, `expected_amount`, `due_day`,
`merchant_match`, `tolerance` (an absolute currency amount), and `grace_days`.
`low_balance.warning_days` and `low_balance.buffer` control warnings.
Amounts use `Decimal`; quoted decimal strings are recommended in YAML and JSON.
Use one currency throughout.

Each named scenario is a directory under `fixtures/` containing:

- `transactions.json`: an array of objects with ISO `date`, `description`, and
  signed `amount`. Negative amounts are posted debits; positive amounts are credits.
- `balances.json`: `{"available": "5000.00"}`, the current available balance of
  the single account being checked.

`BankProvider` defines `get_transactions()` and `get_balance()`. `MockProvider`
reads these files; a future real provider can implement the same interface.
`Notifier` defines `notify(message)`; `ConsoleNotifier` prints alerts.

### Checking rules

`check_payments(payments, transactions, today)` is a pure function. It neither
reads files nor changes its inputs.

- A cycle is the calendar month containing `today`. Prior-month and future-dated
  transactions are ignored. Due days beyond the month's end use its final day.
- Matching uses a case-insensitive merchant substring and one debit within the
  inclusive amount tolerance; split payments are not combined. Use distinct
  merchant strings for distinct payments.
- **PAID**: at least one matching debit remains unreversed.
- **RETURNED**: matching debits were offset by later credits from the same
  merchant, each for exactly the actual debit amount. Each credit offsets one
  debit. A successful retry makes the payment PAID again.
- **PENDING**: no matching debit, and today is before or on the due date plus
  grace days. This includes the grace period because no separate grace status
  is modeled.
- **MISSED**: no matching debit, and today is strictly after due date plus grace.

Transactions are processed chronologically; same-day entries keep their JSON
order, which should reflect posting order. RETURNED takes precedence over MISSED.
No inference about credits without the merchant match is attempted.

Low-balance warnings flag payments not already PAID whose due dates fall between
today and `warning_days` ahead, inclusive, **within this month's cycle**, when
available balance is strictly below expected amount plus buffer. Warnings are
per payment, not a combined cash-flow forecast, and do not look into next month.

## Test

```sh
pipenv run pytest
# Or, inside pipenv shell:
pytest
```

Tests cover status boundaries, reversals, tolerance, month ends, low balances,
all four fixtures, and the CLI. In-process tests block socket access.