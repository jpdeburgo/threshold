import subprocess
import sys

import pytest

from keel.cli import main
from conftest import ROOT


@pytest.mark.parametrize(
    ("fixture", "rent", "mortgage", "alert"),
    [
        ("all_paid", "PAID", "PAID", None),
        ("rent_missed", "MISSED", "PAID", "Rent: MISSED"),
        ("mortgage_returned", "PAID", "RETURNED", "Mortgage: RETURNED"),
        ("low_balance", "PAID", "PENDING", "Mortgage: LOW BALANCE"),
    ],
)
def test_cli_scenarios(fixture, rent, mortgage, alert, capsys):
    assert main(["check", "--today", "2026-11-03", "--fixture", fixture]) == 0
    output = capsys.readouterr().out
    rows = output.splitlines()
    assert "2026-11-03" in rows[0]
    assert rows[2].startswith("Rent") and rows[2].endswith(rent)
    assert rows[3].startswith("Mortgage") and rows[3].endswith(mortgage)
    if alert:
        assert f"ALERT: {alert}" in output
    else:
        assert "ALERT:" not in output


def test_module_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "keel", "check", "--today", "2026-11-03",
         "--fixture", "all_paid"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("PAID") == 2
    assert result.stderr == ""


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["check"],
        ["check", "--fixture", "missing"],
        ["check", "--fixture", "../all_paid"],
        ["check", "--fixture", "all_paid", "--today", "not-a-date"],
    ],
)
def test_cli_invalid_input(arguments, capsys):
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err
