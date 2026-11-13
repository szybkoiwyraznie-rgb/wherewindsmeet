#!/usr/bin/env python3
"""Mapy tekstów gry jako `id -> tekst`, razem z warstwami `_diff`.

Klient trzyma teksty jednego języka w pliku bazowym oraz warstwie `_diff`:

    Package/HD/oversea/locale/translate_words_map_<język>                 baza
    Package/HD/oversea/locale/translate_words_map_<język>_diff            poprawki z paczki
    LocalData/Patch/HD/oversea/locale/translate_words_map_<język>_diff    poprawki pobrane

Uwaga: jak wykazała analiza Patcha 2.4, plik `_diff` z `LocalData/Patch/` jest
liczony od zera względem bazy z `Package/` i **zastępuje** starszy `_diff`
z `Package/` (potrafi m.in. wycofać starsze wpisy z powrotem do wartości bazy
albo je skasować). Dlatego przy odczycie stanu gry warstwa `LocalData/Patch/.../_diff`
zastępuje `Package/.../_diff` tego samego wariantu i języka (`wybierz_warstwy_gry`).

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
from typing import Iterable, TypeVar

try:
    from tools import apply_translation as patcher
    from tools import locale_records as records
except ImportError:  # uruchomienie jako skrypt
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import apply_translation as patcher
    from tools import locale_records as records

DLUGOSC_KLUCZA = 16
_T = TypeVar("_T")
_SLOWO_EN = re.compile(r"[a-z0-9']+")
_STOP_EN = frozenset({"a", "an", "the", "to", "of", "in", "on", "at", "for", "and", "or", "is", "are", "be", "with", "by", "from", "as", "that", "this", "it"})
_DIFF_LAYER_RE = re.compile(
    r"(?:^|/)(package|localdata/patch)/(.+/locale)/((?:\d+_)?translate_words_map_[a-z0-9_]+)_diff$",
    re.IGNORECASE,
)


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
    """Złóż warstwy dokładnie w podanej kolejności: baza, potem kolejne `_diff`.

    Warstwa dopisuje i podmienia teksty oraz kasuje identyfikatory. Uwaga:
    w danych gry warstwa `_diff` z `LocalData/Patch/` jest liczona od zera
    względem bazy i **zastępuje** starsze `_diff` z `Package/` — przed złożeniem
    ścieżek ze źródeł gry użyj `wybierz_warstwy_gry(paths)`.
    """
    texts: dict[int, str] = {}
    for path in paths:
        layer, removed = wczytaj_warstwe(path)
        for ident in removed:
            texts.pop(ident, None)
        texts.update(layer)
    return texts


def filtruj_zastapione_diffy(entries: Iterable[tuple[str, _T]]) -> list[tuple[str, _T]]:
    """Pomiń `Package/.../_diff`, jeśli dla tego samego wariantu i mapy istnieje `LocalData/Patch/.../_diff`."""
    items = list(entries)
    patch_diffs: set[tuple[str, str]] = set()
    for rel, _value in items:
        norm = rel.replace("\\", "/").casefold()
        match = _DIFF_LAYER_RE.search(norm)
        if match and match.group(1) == "localdata/patch":
            base_name = re.sub(r"^\d+_", "", match.group(3))
            patch_diffs.add((match.group(2), base_name))
    if not patch_diffs:
        return items
    filtered: list[tuple[str, _T]] = []
    for rel, value in items:
        norm = rel.replace("\\", "/").casefold()
        match = _DIFF_LAYER_RE.search(norm)
        if match and match.group(1) == "package":
            base_name = re.sub(r"^\d+_", "", match.group(3))
            if (match.group(2), base_name) in patch_diffs:
                continue
        filtered.append((rel, value))
    return filtered


def wybierz_warstwy_gry(paths: Iterable) -> list[Path]:
    """Odfiltruj warstwy `Package/.../_diff` zastąpione przez `LocalData/Patch/.../_diff`."""
    entries = [(str(p), Path(p)) for p in paths]
    return [path for _rel, path in filtruj_zastapione_diffy(entries)]


def sha256_pliku(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
