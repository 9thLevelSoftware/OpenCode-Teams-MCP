"""Cross-platform file locking using the filelock library."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock


@contextmanager
def file_lock(lock_path: Path) -> Iterator[None]:
    """Acquire an exclusive file lock, released on context exit.

    Uses the filelock library for cross-platform compatibility
    (Windows, macOS, Linux) without platform-specific code.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path))
    with lock:
        yield
