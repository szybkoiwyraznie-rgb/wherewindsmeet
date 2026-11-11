#!/usr/bin/env python3
"""Które pliki danych zawierają sceny (`TimelinePObject`) i ile dokładnie.

Rejestr `MANIFEST` podaje pełną liczbę dialogów w grze, więc w każdej dostawie
warte jest sprawdzenie, **które** pliki w ogóle niosą struktury scen. Pliki
`data*` są kontenerami z chunkami w zstd, więc samego `grep` po bajtach nie
wystarczy — najpierw trzeba rozpakować chunki. Znak sceny to serializowany
obiekt `\\x08\\x0f\\x00TimelinePObject` (pole `Type` o wartości
`TimelinePObject`), a nie goły literał, który mógłby wystąpić w tekście.

Narzędzie tylko czyta; nic nie zapisuje. W wyniku podaje nazwy **względem
podanego katalogu**, bez ścieżek systemowych — katalog gry jest prywatny.

Użycie:
    python3 tools/skan_timeline.py local/oversea
    python3 tools/skan_timeline.py local/oversea/data201 local/patch
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from tools import apply_translation as patcher  # noqa: PLC0415 - import pakietu
except ImportError:  # pragma: no cover - uruchomienie jako skrypt
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import apply_translation as patcher


# Serializowane pole `Type` = "TimelinePObject": tag 0x08, u16 długość 15, tekst.
SERIALIZED_TYPE = b"\x08\x0f\x00TimelinePObject"
MEGABYTE = 1000000


def count_objects(path: Path) -> int | None:
    """Liczba obiektów `TimelinePObject` w pliku; `None` jeśli to nie kontener."""
    chunks = patcher.read_container(path.read_bytes())
    total = 0
    for chunk in chunks:
        kind, payload = patcher.split_chunk(chunk)
        try:
            blob = patcher.decompress(kind, payload)
        except Exception:  # noqa: BLE001 - uszkodzony chunk nie zatrzymuje skanu
            continue
        total += blob.count(SERIALIZED_TYPE)
    return total


def display_name(path: Path, root: Path) -> str:
    """Nazwa do raportu: względem katalogu nadrzędnego, bez ścieżki systemowej.

    Dzięki temu skan `local/oversea` i `local/patch` rozróżnia `oversea/data1200`
    od `patch/oversea/data1200`, a prywatna ścieżka do katalogu gry nie trafia
    do wyniku.
    """
    base = root.parent if root.is_dir() else path.parent
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.name


def scan(roots: list[Path]) -> dict[str, object]:
    with_timeline: list[dict[str, object]] = []
    without: list[str] = []
    not_container: list[str] = []
    unreadable = 0
    seen: set[Path] = set()
    for root in roots:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in files:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            name = display_name(path, root)
            try:
                count = count_objects(path)
            except Exception:  # noqa: BLE001 - brak kontenera to też wynik
                not_container.append(name)
                continue
            except OSError:
                unreadable += 1
                continue
            if count:
                with_timeline.append(
                    {
                        "plik": name,
                        "obiekty": count,
                        "megabajty": round(path.stat().st_size / MEGABYTE, 1),
                    }
                )
            else:
                without.append(name)
    with_timeline.sort(key=lambda row: (-int(row["obiekty"]), str(row["plik"])))
    return {
        "plikow": len(seen),
        "kontenerow": len(with_timeline) + len(without),
        "z_timeline": with_timeline,
        "obiekty_razem": sum(int(row["obiekty"]) for row in with_timeline),
        "bez_timeline": sorted(without),
        "poza_kontenerem": sorted(not_container),
        "nieczytelnych": unreadable,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Skan plików danych pod kątem scen (TimelinePObject).",
    )
    parser.add_argument("sciezki", nargs="+", help="katalogi lub pliki do skanu")
    arguments = parser.parse_args(argv)
    roots = [Path(value) for value in arguments.sciezki]
    print(json.dumps(scan(roots), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
