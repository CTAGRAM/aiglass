"""Structured logging for the OSINT engine. `import logging as _logging` so this module name doesn't
shadow the stdlib for our own use."""
from __future__ import annotations

import logging as _logging
import sys

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    handler = _logging.StreamHandler(sys.stderr)
    handler.setFormatter(_logging.Formatter("%(asctime)s osint.%(name)s %(levelname)s %(message)s"))
    root = _logging.getLogger("osint")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(_logging.INFO)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> _logging.Logger:
    _configure()
    return _logging.getLogger("osint").getChild(name)
