"""One-line progress messages for the long phases of ``index``."""

import sys

from tqdm import tqdm


def status(message: str) -> None:
    """Tell the user which phase is running, on stderr.

    ``tqdm.write`` is used instead of ``print`` so a message that arrives
    while a progress bar is open does not break the bar. It goes to stderr
    so stdout keeps only the results a script may parse. The phases between
    two bars (writing SQLite, loading the model) have no known total, so a
    message is the only honest feedback there.

    Args:
        message: The text to show.
    """
    tqdm.write(message, file=sys.stderr)
