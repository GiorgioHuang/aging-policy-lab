"""CLI smoke tests: the module imports (catches syntax errors in rarely-run
paths like `watch probe`) and offline subcommands run."""
from __future__ import annotations

import pytest

from hapi_pipeline import cli


def test_enums_runs(capsys):
    assert cli.main(["enums"]) == 0
    assert "policy_lifecycle" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [
    ["watch", "probe", "--help"],
    ["watch", "fetch", "--help"],
    ["watch", "review", "--help"],
    ["watch", "digest", "--help"],
    ["ingest", "--help"],
])
def test_subcommand_help(argv):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 0


def test_watch_probe_discover_handles_unreachable_page(capsys):
    assert cli.main(["watch", "probe", "--discover", "file:///nonexistent/page.html"]) == 0
    assert "✗" in capsys.readouterr().out
