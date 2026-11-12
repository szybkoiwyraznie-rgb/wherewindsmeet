#!/usr/bin/env python3
"""Mapy tekstów gry jako `id -> tekst`, razem z warstwami `_diff`.

Klient trzyma teksty jednego języka w kilku plikach i czyta je po kolei —
późniejszy plik przykrywa wcześniejszy:

    Package/HD/oversea/locale/translate_words_map_<język>          baza
    Package/HD/oversea/locale/translate_words_map_<język>_diff     poprawki z paczki
    LocalData/Patch/HD/oversea/locale/translate_words_map_<język>_diff   poprawki pobrane

Plik `_diff` ma ten sam kontener co baza (docs/LOCALE_CONTAINER.md). Jego
pierwszy chunk to `u64 liczba wpisów po zmianie, u64 liczba kubełków bazy,
u32[kubełki]`: dla każdego kubełka bazy numer chunku z jego zmianami albo
`0xFFFFFFFF`. Chunk zmian jest zwykłą tabelą tekstów z wpisami nowymi,
podmienionymi i skasowanymi (wartość `0xFF`). Warstwa z `LocalData/Patch`
istnieje tylko dla języka wybranego w grze, więc najnowsze teksty mogą mieć
wersję angielską bez chińskiej.

Klucz tekstu (`klucz`) to 16 znaków szesnastkowych SHA-256 z tekstu źródłowego.
Łączy wszystkie identyfikatory o tej samej treści źródłowej: tłumaczenie
przypisane do klucza trafia do każdego z nich, także do identyfikatorów, które
gra doda w przyszłych aktualizacjach.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

try:
    from tools import apply_translation as patcher
    from tools import locale_records as records
except ImportError:  # uruchomienie jako skrypt
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import apply_translation as patcher
    from tools import locale_records as records

DLUGOSC_KLUCZA = 16
_SLOWO_EN = re.compile(r"[a-z0-9']+")
_STOP_EN = frozenset({"a", "an", "the", "to", "of", "in", "on", "at", "for", "and", "or", "is", "are", "be", "with", "by", "from", "as", "that", "this", "it"})


class MapaError(Exception):
    """Plik mapy tekstów nie daje się odczytać w całości."""


def klucz(tekst: str) -> str:
    """Stały klucz tekstu źródłowego."""
    return hashlib.sha256(tekst.encode("utf-8")).hexdigest()[:DLUGOSC_KLUCZA]


def klucz_wariantu(tekst: str, angielski: str) -> str:
    """Klucz rozróżniający kontekstowe warianty tego samego tekstu źródłowego."""
    return hashlib.sha256(f"{tekst}\0{angielski}".encode("utf-8")).hexdigest()[:DLUGOSC_KLUCZA]


def podobienstwo_en(a: str, b: str) -> float:
    """Podobieństwo dwóch wersji angielskich tego samego napisu (0.0..1.0)."""
    def sygnatura(text: str) -> frozenset[str]:
        norm = text.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"').casefold()
        words = _SLOWO_EN.findall(norm)
        core = frozenset(w for w in words if w not in _STOP_EN)
        return core if core else frozenset(words)

    sa, sb = sygnatura(a), sygnatura(b)
    if sa == sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def wczytaj_warstwe(path) -> tuple[dict[int, str], set[int]]:
    """Jedna mapa albo warstwa `_diff`: (`id -> tekst`, identyfikatory skasowane).

    Wpis, którego wartością jest pojedynczy bajt `0xFF`, w warstwie `_diff`
    oznacza skasowanie identyfikatora. Każdy chunk musi się odczytać.
    """
    try:
        data = Path(path).read_bytes()
        chunks = patcher.read_container(data)
        texts: dict[int, str] = {}
        removed: set[int] = set()
        for chunk in chunks:
            if patcher.is_metadata_chunk(chunk, len(chunks)):
                continue
            kind, payload = patcher.split_chunk(chunk)
            table = records.parse_table(patcher.decompress(kind, payload))
            for entry in table["entries"]:
                if not entry["id"] or not entry["length"]:
                    continue
                if entry["placeholder"]:
                    removed.add(entry["id"])
                else:
                    texts[entry["id"]] = entry["text"].decode("utf-8", "replace")
    except (OSError, patcher.PatchError, records.LayoutError) as error:
        raise MapaError(f"{path}: {error}") from error
    return texts, removed


def wczytaj(path) -> dict[int, str]:
    """Sama treść jednej mapy: `id -> tekst` (bez wpisów skasowanych)."""
    return wczytaj_warstwe(path)[0]


def zloz(paths: Iterable) -> dict[int, str]:
    """Złóż warstwy w podanej kolejności: baza, potem kolejne `_diff`.

    Warstwa dopisuje i podmienia teksty oraz kasuje identyfikatory. Każda
    warstwa `_diff` jest liczona względem bazy (jej nagłówek podaje liczbę
    wpisów równą `baza + nowe - skasowane`), a nowsza zawiera zmiany starszej,
    więc złożenie „baza, diff z paczki, diff pobrany” daje stan widziany w grze.
    """
    texts: dict[int, str] = {}
    for path in paths:
        layer, removed = wczytaj_warstwe(path)
        for ident in removed:
            texts.pop(ident, None)
        texts.update(layer)
    return texts


def sha256_pliku(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
