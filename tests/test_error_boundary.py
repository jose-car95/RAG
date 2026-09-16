"""Tests for the CLI error boundary.

No real command fails yet, so a test double with failing commands is handed
to the boundary instead of ``RagCli``.
"""

import pytest

from src.adapters.cli import run


class FailingCommands:
    """Test double whose commands end in the ways the boundary must handle."""

    def bad_input(self) -> None:
        """Fail with a message."""
        raise ValueError("bad input")

    def silent_failure(self) -> None:
        """Fail without a message."""
        raise RuntimeError()

    def interrupted(self) -> None:
        """Behave as if the user pressed Ctrl+C."""
        raise KeyboardInterrupt

    def succeed(self) -> None:
        """Finish without errors."""
        print("done")


def test_error_becomes_one_line_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An exception is reported as ``ERROR: <message>`` with exit code 1."""
    exit_code = run(FailingCommands(), ["bad_input"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == "ERROR: bad input\n"


def test_error_without_message_shows_its_type(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An exception without message is reported by its type name."""
    exit_code = run(FailingCommands(), ["silent_failure"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == "ERROR: RuntimeError\n"


def test_ctrl_c_is_reported_as_interrupted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ctrl+C ends with ``Interrupted`` and the conventional exit code 130."""
    exit_code = run(FailingCommands(), ["interrupted"])

    captured = capsys.readouterr()
    assert exit_code == 130
    assert captured.err == "Interrupted\n"


def test_success_returns_zero_and_keeps_stderr_empty(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A command that works exits with 0 and writes nothing to stderr."""
    exit_code = run(FailingCommands(), ["succeed"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "done\n"
    assert captured.err == ""


def test_fire_usage_errors_are_not_swallowed() -> None:
    """Fire's own usage errors still exit with code 2 instead of 1."""
    with pytest.raises(SystemExit) as exit_info:
        run(FailingCommands(), ["nonexistent_command"])

    assert exit_info.value.code == 2
