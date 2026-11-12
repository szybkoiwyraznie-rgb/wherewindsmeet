#!/usr/bin/env python3
"""Czytnik bazy danych gry: MANIFEST -> indexN -> dataN (tylko odczyt).

Pliki `MANIFEST`, `indexN` i `dataN` z `Package/HD/oversea` tworzą jedną bazę
klucz -> wartość (opis: docs/BAZA_GRY.md):

    MANIFEST   nazwa tabeli -> liczba wierszy, chunk schematu, chunki wierszy
               (każdy z opcjonalnym chunkiem poprawek z warstwy aktualizacji)
    indexN     chunk schematu (nazwy kolumn) albo tablica haszująca
               klucz wiersza -> (plik danych, chunk, offset, długość)
    dataN      wartości; offset i długość liczone w słowach 8-bajtowych

Wartość tabeli bez schematu to jedna wartość z etykietą typu. Wiersz tabeli ze
schematem to `u16 liczba pól`, a potem pola `u16 (kolumna | typ << 10)` + dane
w tym samym kodowaniu co wartości z etykietą.

Moduł niczego nie zapisuje do plików gry. Każda niezgodność formatu kończy się
wyjątkiem `BazaError` — nie ma cichego pomijania.

Użycie:
    python3 tools/baza_gry.py KATALOG [KATALOG...]              # podsumowanie
    python3 tools/baza_gry.py KATALOG... --tabele [PREFIKS]     # lista tabel (TSV)
    python3 tools/baza_gry.py KATALOG... --tabela NAZWA         # wiersze jako JSONL
    python3 tools/baza_gry.py KATALOG... --sprawdz              # odczyt wszystkiego

Późniejszy katalog przykrywa wcześniejszy (np. `Package/...` potem
`LocalData/Patch/...`), tak jak robi to klient gry.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

try:  # import jako moduł
    from tools import apply_translation as patcher
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import apply_translation as patcher
    from tools import wypisz


class BazaError(Exception):
    """Plik nie pasuje do rozpoznanego układu bazy gry."""


BEZ_SCHEMATU = 0xFFFF
BRAK = 0xFFFF
FLAGA_KLUCZE_LICZBOWE = 0x400
FLAGA_KLUCZE_NAPISOWE = 0x800
SLOWO = 8
NAGLOWEK_MANIFESTU = struct.Struct("<HHIIIII")
REKORD_TABELI = struct.Struct("<IIHHIIIII")
CZESC = struct.Struct("<HHHH")
NAGLOWEK_TABLICY = struct.Struct("<QQQ")
MAKS_GLEBOKOSC = 200

T_U8, T_U16, T_U32, T_U64 = 0x01, 0x02, 0x03, 0x04
T_F64 = 0x06
T_NAPIS = 0x08
T_LISTA = 0x09
T_OBIEKT = 0x0A
T_NONE, T_FALSE, T_TRUE = 0x0B, 0x0C, 0x0D


@dataclass(frozen=True)
class Czesc:
    """Chunk indeksu z wierszami oraz opcjonalny chunk poprawek (warstwa aktualizacji)."""

    plik: int
    chunk: int
    poprawki: tuple[int, int] | None = None


@dataclass(frozen=True)
class Tabela:
    nazwa: str
    wiersze: int
    schemat: tuple[int, int] | None
    czesci: tuple[Czesc, ...]
    flagi: int
    schemat_dopisany: tuple[int, int] | None = None

    @property
    def klucze_liczbowe(self) -> bool:
        return bool(self.flagi & FLAGA_KLUCZE_LICZBOWE)


@dataclass(frozen=True)
class Polozenie:
    """Miejsce wartości: numer pliku danych, chunk, offset i długość w słowach."""

    plik: int
    chunk: int
    offset: int
    dlugosc: int

    @property
    def usuniety(self) -> bool:
        """W chunku poprawek: wiersz skasowany przez warstwę aktualizacji."""
        return self.plik == 0 and self.dlugosc == 0


@dataclass(frozen=True)
class Manifest:
    tabele: dict[str, Tabela]
    bez_rekordu: tuple[str, ...]
    pliki_indeksu: tuple[str, ...]
    pliki_danych: tuple[str, ...]


# ---------------------------------------------------------------- kontener


def rozpakuj_chunki(data: bytes) -> list[bytes]:
    """Surowe chunki kontenera `0xDEADBEEF` (jeszcze skompresowane)."""
    try:
        return patcher.read_container(data)
    except patcher.PatchError as error:
        raise BazaError(str(error)) from error


def rozpakuj_chunk(chunk: bytes) -> bytes:
    try:
        kind, payload = patcher.split_chunk(chunk)
        return patcher.decompress(kind, payload)
    except patcher.PatchError as error:
        raise BazaError(str(error)) from error


# ---------------------------------------------------------------- MANIFEST


def _nazwy_plikow(buf: bytes, pos: int) -> tuple[tuple[str, ...], int]:
    if pos + 4 > len(buf):
        raise BazaError("MANIFEST: ucięta lista plików")
    count = struct.unpack_from("<I", buf, pos)[0]
    pos += 4
    names = []
    for _ in range(count):
        if pos + 2 > len(buf):
            raise BazaError("MANIFEST: ucięta nazwa pliku")
        size = struct.unpack_from("<H", buf, pos)[0]
        names.append(buf[pos + 2 : pos + 2 + size].decode("ascii"))
        pos += 2 + size
    return tuple(names), pos


def parse_manifest(buf: bytes) -> Manifest:
    """Rozłóż zdekompresowany chunk `MANIFEST`."""
    if len(buf) < NAGLOWEK_MANIFESTU.size:
        raise BazaError("MANIFEST: za krótki nagłówek")
    _a, _b, _c, n_tabel, n_czesci, n_c, n_d = NAGLOWEK_MANIFESTU.unpack_from(buf, 0)
    pos = NAGLOWEK_MANIFESTU.size
    names = []
    for _ in range(n_tabel + n_c + n_d):
        if pos + 2 > len(buf):
            raise BazaError("MANIFEST: ucięta lista nazw")
        size = struct.unpack_from("<H", buf, pos)[0]
        raw = buf[pos + 2 : pos + 2 + size]
        if len(raw) != size:
            raise BazaError("MANIFEST: ucięta nazwa tabeli")
        names.append(raw.decode("utf-8"))
        pos = (pos + 2 + size + 7) // 8 * 8
    records_at = pos
    parts_at = records_at + REKORD_TABELI.size * n_tabel
    tail_at = parts_at + CZESC.size * n_czesci
    if tail_at > len(buf):
        raise BazaError("MANIFEST: rekordy wychodzą poza plik")
    parts = []
    for index in range(n_czesci):
        plik, chunk, d_plik, d_chunk = CZESC.unpack_from(buf, parts_at + CZESC.size * index)
        parts.append(Czesc(plik, chunk, None if d_plik == BRAK else (d_plik, d_chunk)))
    tabele: dict[str, Tabela] = {}
    for index in range(n_tabel):
        rows, count, s_file, s_chunk, delta, _hash, _zero, first, flags = REKORD_TABELI.unpack_from(
            buf, records_at + REKORD_TABELI.size * index
        )
        d_file, d_chunk = delta & 0xFFFF, delta >> 16
        if first + count > n_czesci:
            raise BazaError(f"MANIFEST: tabela {names[index]!r} wskazuje części poza listą")
        tabele[names[index]] = Tabela(
            nazwa=names[index],
            wiersze=rows,
            schemat=None if s_file == BEZ_SCHEMATU else (s_file, s_chunk),
            czesci=tuple(parts[first : first + count]),
            flagi=flags,
            schemat_dopisany=None if d_file == BRAK else (d_file, d_chunk),
        )
    pliki_indeksu, pos = _nazwy_plikow(buf, tail_at)
    pliki_danych, pos = _nazwy_plikow(buf, pos)
    return Manifest(
        tabele=tabele,
        bez_rekordu=tuple(names[n_tabel:]),
        pliki_indeksu=pliki_indeksu,
        pliki_danych=pliki_danych,
    )


def read_manifest(path) -> Manifest:
    chunks = rozpakuj_chunki(Path(path).read_bytes())
    if len(chunks) != 1:
        raise BazaError(f"MANIFEST: oczekiwano 1 chunku, jest {len(chunks)}")
    return parse_manifest(rozpakuj_chunk(chunks[0]))


# ---------------------------------------------------------------- indeks


def parse_schema(buf: bytes) -> list[str]:
    """Chunk schematu: `u16 liczba`, potem nazwy kolumn `[u16 długość, UTF-8]`."""
    if len(buf) < 2:
        raise BazaError("schemat: pusty chunk")
    count = struct.unpack_from("<H", buf, 0)[0]
    pos = 2
    columns = []
    for _ in range(count):
        if pos + 2 > len(buf):
            raise BazaError("schemat: ucięta nazwa kolumny")
        size = struct.unpack_from("<H", buf, pos)[0]
        raw = buf[pos + 2 : pos + 2 + size]
        if len(raw) != size:
            raise BazaError("schemat: ucięta nazwa kolumny")
        columns.append(raw.decode("utf-8"))
        pos += 2 + size
    return columns


def iter_index(buf: bytes, klucze_liczbowe: bool) -> Iterator[tuple[object, Polozenie]]:
    """Wiersze tablicy haszującej indeksu: (klucz, położenie wartości)."""
    if len(buf) < NAGLOWEK_TABLICY.size:
        raise BazaError("indeks: za krótki nagłówek tablicy")
    capacity, used, _seed = NAGLOWEK_TABLICY.unpack_from(buf, 0)
    ctrl_at = NAGLOWEK_TABLICY.size
    entries_at = ctrl_at + max(capacity + 17, 24)
    if entries_at + 16 * capacity > len(buf):
        raise BazaError("indeks: sloty wychodzą poza chunk")
    found = 0
    for slot in range(capacity):
        if buf[ctrl_at + slot] >= 0x80:
            continue
        base = entries_at + 16 * slot
        if klucze_liczbowe:
            key: object = struct.unpack_from("<Q", buf, base)[0]
        else:
            offset, size = struct.unpack_from("<II", buf, base)
            raw = buf[base + offset : base + offset + size]
            if len(raw) != size:
                raise BazaError("indeks: klucz wychodzi poza chunk")
            key = raw.decode("utf-8")
        found += 1
        yield key, Polozenie(*struct.unpack_from("<4H", buf, base + 8))
    if found != used:
        raise BazaError(f"indeks: nagłówek podaje {used} wierszy, w slotach jest {found}")


# ---------------------------------------------------------------- wartości


def _klucz(value):
    """Klucz słownika musi być haszowalny; listy i obiekty zamieniamy na JSON."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _dane(tag: int, buf: bytes, pos: int, depth: int):
    """Odczytaj dane wartości o znanym typie (bez bajtu etykiety)."""
    if depth > MAKS_GLEBOKOSC:
        raise BazaError("wartość: zagnieżdżenie głębsze niż dopuszczalne")
    try:
        if tag == T_U8:
            return buf[pos], pos + 1
        if tag == T_U16:
            return struct.unpack_from("<H", buf, pos)[0], pos + 2
        if tag == T_U32:
            return struct.unpack_from("<I", buf, pos)[0], pos + 4
        if tag == T_U64:
            return struct.unpack_from("<Q", buf, pos)[0], pos + 8
        if tag == T_F64:
            return struct.unpack_from("<d", buf, pos)[0], pos + 8
        if tag == T_NAPIS:
            size = struct.unpack_from("<H", buf, pos)[0]
            raw = buf[pos + 2 : pos + 2 + size]
            if len(raw) != size:
                raise BazaError("wartość: napis wychodzi poza chunk")
            return raw.decode("utf-8", "surrogateescape"), pos + 2 + size
        if tag == T_LISTA:
            count = struct.unpack_from("<H", buf, pos)[0]
            pos += 2
            items = []
            for _ in range(count):
                item, pos = read_value(buf, pos, depth + 1)
                items.append(item)
            return items, pos
        if tag == T_OBIEKT:
            count = struct.unpack_from("<H", buf, pos)[0]
            pos += 2
            if count % 2:
                raise BazaError("wartość: obiekt ma nieparzystą liczbę elementów")
            mapping = {}
            for _ in range(count // 2):
                key, pos = read_value(buf, pos, depth + 1)
                value, pos = read_value(buf, pos, depth + 1)
                mapping[_klucz(key)] = value
            return mapping, pos
        if tag == T_NONE:
            return None, pos
        if tag == T_FALSE:
            return False, pos
        if tag == T_TRUE:
            return True, pos
    except (struct.error, IndexError) as error:
        raise BazaError(f"wartość: dane ucięte przy pozycji {pos}") from error
    raise BazaError(f"wartość: nieznany typ {tag:#04x} przy pozycji {pos}")


def read_value(buf: bytes, pos: int, depth: int = 0):
    """Jedna wartość z etykietą typu; zwraca (wartość, pozycja za nią)."""
    if pos >= len(buf):
        raise BazaError(f"wartość: pozycja {pos} poza chunkiem")
    return _dane(buf[pos], buf, pos + 1, depth)


def read_row(buf: bytes, pos: int, kolumny: list[str]):
    """Wiersz tabeli ze schematem: słownik nazwa kolumny -> wartość."""
    if pos + 2 > len(buf):
        raise BazaError("wiersz: ucięty nagłówek")
    count = struct.unpack_from("<H", buf, pos)[0]
    pos += 2
    row = {}
    for _ in range(count):
        if pos + 2 > len(buf):
            raise BazaError("wiersz: ucięte pole")
        head = struct.unpack_from("<H", buf, pos)[0]
        column, tag = head & 0x3FF, head >> 10
        if column >= len(kolumny):
            raise BazaError(f"wiersz: kolumna {column} poza schematem ({len(kolumny)} kolumn)")
        row[kolumny[column]], pos = _dane(tag, buf, pos + 2, 1)
    return row, pos


# ---------------------------------------------------------------- baza


class Baza:
    """Odczyt tabel z katalogów z plikami `MANIFEST`, `indexN`, `dataN`."""

    def __init__(self, katalogi, manifest=None, pamiec_chunkow: int = 512):
        self.pliki: dict[str, Path] = {}
        for katalog in katalogi:
            katalog = Path(katalog)
            if not katalog.is_dir():
                raise BazaError(f"brak katalogu: {katalog}")
            for path in sorted(katalog.iterdir()):
                if path.is_file():
                    self.pliki[path.name] = path  # późniejszy katalog przykrywa
        manifest_path = Path(manifest) if manifest else self.pliki.get("MANIFEST")
        if manifest_path is None:
            raise BazaError("nie znaleziono pliku MANIFEST")
        self.sciezka_manifestu = manifest_path
        self.manifest = read_manifest(manifest_path)
        self.tabele = self.manifest.tabele
        self._kontenery: dict[str, list[bytes]] = {}
        self._chunki: OrderedDict[tuple[str, int], bytes] = OrderedDict()
        self._pamiec = pamiec_chunkow
        self._schematy: dict[tuple, list[str]] = {}

    def _chunk(self, nazwa_pliku: str, index: int) -> bytes:
        key = (nazwa_pliku, index)
        cached = self._chunki.get(key)
        if cached is not None:
            self._chunki.move_to_end(key)
            return cached
        chunks = self._kontenery.get(nazwa_pliku)
        if chunks is None:
            path = self.pliki.get(nazwa_pliku)
            if path is None:
                raise BazaError(f"brak pliku {nazwa_pliku}")
            chunks = rozpakuj_chunki(path.read_bytes())
            self._kontenery[nazwa_pliku] = chunks
        if index >= len(chunks):
            raise BazaError(f"{nazwa_pliku}: brak chunku {index} (jest {len(chunks)})")
        data = rozpakuj_chunk(chunks[index])
        self._chunki[key] = data
        if len(self._chunki) > self._pamiec:
            self._chunki.popitem(last=False)
        return data

    def tabela(self, nazwa: str) -> Tabela:
        try:
            return self.tabele[nazwa]
        except KeyError:
            raise BazaError(f"brak tabeli {nazwa!r}") from None

    def kolumny(self, nazwa: str) -> list[str] | None:
        """Kolumny tabeli: schemat bazowy plus kolumny dopisane przez warstwę aktualizacji."""
        tabela = self.tabela(nazwa)
        if tabela.schemat is None:
            return None
        klucz = (tabela.schemat, tabela.schemat_dopisany)
        if klucz not in self._schematy:
            kolumny = list(parse_schema(self._chunk(f"index{tabela.schemat[0]}", tabela.schemat[1])))
            if tabela.schemat_dopisany is not None:
                plik, chunk = tabela.schemat_dopisany
                kolumny += parse_schema(self._chunk(f"index{plik}", chunk))
            self._schematy[klucz] = kolumny
        return self._schematy[klucz]

    def polozenia(self, nazwa: str) -> Iterator[tuple[object, Polozenie]]:
        """Wiersze tabeli po nałożeniu poprawek: zamiana, dopisanie, skasowanie."""
        tabela = self.tabela(nazwa)
        count = 0
        for czesc in tabela.czesci:
            rows = dict(iter_index(self._chunk(f"index{czesc.plik}", czesc.chunk), tabela.klucze_liczbowe))
            if czesc.poprawki is not None:
                d_plik, d_chunk = czesc.poprawki
                for key, place in iter_index(self._chunk(f"index{d_plik}", d_chunk), tabela.klucze_liczbowe):
                    if place.usuniety:
                        rows.pop(key, None)
                    else:
                        rows[key] = place
            count += len(rows)
            yield from rows.items()
        if count != tabela.wiersze:
            raise BazaError(f"{nazwa}: MANIFEST podaje {tabela.wiersze} wierszy, indeks ma {count}")

    def wartosc(self, nazwa: str, miejsce: Polozenie):
        """Wartość spod położenia; sprawdza, że kończy się w swoim przedziale."""
        buf = self._chunk(f"data{miejsce.plik}", miejsce.chunk)
        start = miejsce.offset * SLOWO
        end = (miejsce.offset + miejsce.dlugosc) * SLOWO
        if end > len(buf):
            raise BazaError(f"{nazwa}: wartość wychodzi poza chunk danych")
        kolumny = self.kolumny(nazwa)
        if kolumny is None:
            value, stop = read_value(buf, start)
        else:
            value, stop = read_row(buf, start, kolumny)
        if stop > end or end - stop >= SLOWO or any(buf[stop:end]):
            raise BazaError(
                f"{nazwa}: wartość kończy się na {stop}, a przedział to {start}..{end}"
            )
        return value

    def wiersze(self, nazwa: str) -> Iterator[tuple[object, object]]:
        for key, place in self.polozenia(nazwa):
            yield key, self.wartosc(nazwa, place)


# ---------------------------------------------------------------- CLI


def do_json(value):
    """Wartość bazy jako struktura zapisywalna w JSON (klucze na napisy)."""
    if isinstance(value, dict):
        return {str(key): do_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [do_json(item) for item in value]
    if isinstance(value, float) and value != value:  # NaN
        return None
    if isinstance(value, str):
        return value.encode("utf-8", "replace").decode("utf-8")
    return value


def rodzina(nazwa: str) -> str:
    return nazwa.split(".", 1)[0]


def podsumowanie(baza: Baza) -> dict:
    rodziny = Counter(rodzina(name) for name in baza.tabele)
    return {
        "tabel": len(baza.tabele),
        "wierszy": sum(table.wiersze for table in baza.tabele.values()),
        "tabel_ze_schematem": sum(1 for table in baza.tabele.values() if table.schemat),
        "czesci_z_poprawkami": sum(
            1 for table in baza.tabele.values() for czesc in table.czesci if czesc.poprawki
        ),
        "nazw_bez_rekordu": len(baza.manifest.bez_rekordu),
        "rodzin": len(rodziny),
        "najwieksze_rodziny": rodziny.most_common(12),
        "pliki_indeksu": list(baza.manifest.pliki_indeksu),
        "pliki_danych": list(baza.manifest.pliki_danych),
        "brakujace_pliki": sorted(
            name
            for name in (*baza.manifest.pliki_indeksu, *baza.manifest.pliki_danych)
            if name not in baza.pliki
        ),
    }


def sprawdz(baza: Baza, postep=None) -> dict:
    """Odczytaj każdy wiersz każdej tabeli; policz błędy zamiast je ukrywać."""
    bledy: Counter = Counter()
    przyklady: dict[str, str] = {}
    tabel = wierszy = 0
    for number, name in enumerate(baza.tabele, 1):
        try:
            for _key, _value in baza.wiersze(name):
                wierszy += 1
            tabel += 1
        except BazaError as error:
            kind = str(error).split(":", 1)[-1].strip()[:60] if ":" in str(error) else str(error)[:60]
            bledy[kind] += 1
            przyklady.setdefault(kind, f"{name}: {error}")
        if postep and number % 5000 == 0:
            postep(number, len(baza.tabele))
    return {
        "tabel_odczytanych": tabel,
        "tabel_z_bledem": sum(bledy.values()),
        "wierszy_odczytanych": wierszy,
        "bledy": dict(bledy.most_common()),
        "przyklady": przyklady,
    }


def main(argv=None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description="Czytnik bazy danych gry (MANIFEST/index/data).")
    parser.add_argument("katalogi", nargs="+", help="katalogi z plikami gry; późniejszy przykrywa")
    parser.add_argument("--manifest", help="plik MANIFEST (domyślnie z ostatniego katalogu)")
    parser.add_argument("--tabele", nargs="?", const="", metavar="PREFIKS",
                        help="wypisz tabele (nazwa, wiersze, kolumny) jako TSV")
    parser.add_argument("--tabela", metavar="NAZWA", help="wypisz wiersze tabeli jako JSONL")
    parser.add_argument("--limit", type=int, help="najwyżej tyle wierszy tabeli")
    parser.add_argument("--wyj", help="plik wyjściowy zamiast standardowego wyjścia")
    parser.add_argument("--sprawdz", action="store_true", help="odczytaj wszystkie tabele i policz błędy")
    arguments = parser.parse_args(argv)

    try:
        baza = Baza(arguments.katalogi, arguments.manifest)
        out = open(arguments.wyj, "w", encoding="utf-8") if arguments.wyj else sys.stdout
        try:
            if arguments.tabela:
                for number, (key, value) in enumerate(baza.wiersze(arguments.tabela)):
                    if arguments.limit is not None and number >= arguments.limit:
                        break
                    out.write(json.dumps({"klucz": key, "wartosc": do_json(value)}, ensure_ascii=False) + "\n")
            elif arguments.tabele is not None:
                for name, table in baza.tabele.items():
                    if not name.startswith(arguments.tabele):
                        continue
                    columns = baza.kolumny(name)
                    out.write(f"{name}\t{table.wiersze}\t{','.join(columns) if columns else ''}\n")
            elif arguments.sprawdz:
                report = sprawdz(baza, lambda done, total: print(f"  {done}/{total}", file=sys.stderr))
                out.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
                return 1 if report["tabel_z_bledem"] else 0
            else:
                out.write(json.dumps(podsumowanie(baza), ensure_ascii=False, indent=2) + "\n")
        finally:
            if out is not sys.stdout:
                out.close()
    except BazaError as error:
        print(f"BŁĄD: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
