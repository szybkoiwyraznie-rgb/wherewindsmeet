"""Wyjście narzędzi zawsze w UTF-8.

W Windows wyjście przekierowane do pliku albo potoku (`> raport.json`, CI)
dostaje stronę kodową systemu, w której nie ma polskich ani chińskich znaków,
i `print` kończy się wyjątkiem `UnicodeEncodeError`. Okno konsoli tego problemu
nie ma. Każde narzędzie z `main()` woła `utf8()` na samym początku, zanim
`argparse` wypisze cokolwiek.
"""

from __future__ import annotations

import sys


def utf8() -> None:
    """Przestaw `stdout` i `stderr` na UTF-8; znak nie do zapisania zamień na `\\uXXXX`."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # podstawiony bufor (testy, przechwytywanie)
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass
