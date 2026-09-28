"""Run pytest without reusing temporary directories or the shared pytest cache."""

from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    root = Path(__file__).resolve().parent
    # Each caller creates its own directory with its current Windows permissions.
    with tempfile.TemporaryDirectory(prefix="monitoreo-vial-tests-") as temporary:
        return subprocess.call(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "--basetemp", str(Path(temporary) / "pytest")],
            cwd=root,
        )


if __name__ == "__main__":
    raise SystemExit(main())
