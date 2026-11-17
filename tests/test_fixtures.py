from datetime import date
from decimal import Decimal

import pytest

from keel.checks import check_low_balance, check_payments
from keel.config import load_config
from keel.models import Status
from keel.providers import MockProvider
from conftest import ROOT


@pytest.mark.parametrize(
    ("fixture", "statuses", "warnings"),
    [
        ("all_paid", [Status.PAID, Status.PAID], []),
        ("rent_missed", [Status.MISSED, Status.PAID], []),
        ("mortgage_returned", [Status.PAID, Status.RETURNED], []),
        ("low_balance", [Status.PAID, Status.PENDING], ["Mortgage"]),
    ],
)
def test_fixture_scenarios(fixture, statuses, warnings):
    config = load_config(ROOT / "config.yaml")
    provider = MockProvider(fixture, ROOT / "fixtures")
    today = date(2026, 11, 3)
    results = check_payments(config.payments, provider.get_transactions(), today)
    assert [result.status for result in results] == statuses
    assert isinstance(provider.get_balance(), Decimal)
    assert [
        result.payment.name
        for result in check_low_balance(
            results, provider.get_balance(), today, config.warning_days, config.buffer
        )
    ] == warnings


@pytest.mark.parametrize("name", ["../all_paid", "/tmp", ".", "..", ""])
def test_fixture_paths_cannot_escape_directory(name):
    with pytest.raises(ValueError):
        MockProvider(name, ROOT / "fixtures")


@pytest.mark.parametrize(
    "replacement",
    [
        'warning_days: -1',
        'warning_days: "3"',
        'buffer: "-1"',
        'buffer: "NaN"',
    ],
)
def test_invalid_warning_configuration(tmp_path, replacement):
    text = (ROOT / "config.yaml").read_text()
    key = replacement.split(":")[0]
    original = "warning_days: 3" if key == "warning_days" else 'buffer: "100.00"'
    path = tmp_path / "config.yaml"
    path.write_text(text.replace(original, replacement))
    with pytest.raises(ValueError):
        load_config(path)
