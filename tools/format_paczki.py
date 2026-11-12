#!/usr/bin/env python3
"""Wspólne zasady zapisu pakietu dla tłumacza: jedna linia na tekst, tokeny, elementy.

Generator (`tools/buduj_paczke.py`) i import zwrotki (`tools/import_zwrotki.py`)
muszą rozumieć plik `.md` identycznie, więc cała umowa jest w jednym miejscu.

Element w pliku:

    14. [Kwestia — 红线 (Ruby)] 哇，这是什么暗号吗？
       klucz: 693cf29aef2cf70a
       tokeny: zachowaj dokładnie: #Y, #E
       EN: Whoa, what symbol is that?
       PL: tu wpisuje tłumacz

- `klucz:` wiąże element z tekstem gry: 16 znaków szesnastkowych to klucz tekstu
  źródłowego (jedno tłumaczenie dla wszystkich miejsc z tym samym tekstem),
  a `@` + 16 znaków to jeden konkretny identyfikator tekstu (kwestie zależne od
  płci bohatera).
- Tekst zawsze stoi w jednej linii. Znaki, których w jednej linii nie da się
  pokazać, są zakodowane: nowa linia jako `\\n`, tabulator jako `\\t`, powrót
  karetki jako `\\r`, a prawdziwy ukośnik wsteczny jako `\\\\`.
- Import bierze tylko linie `klucz:` i `PL:`; reszta pliku jest dla człowieka.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterator, NamedTuple

_KODY = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_ODKODY = {"\\": "\\", "n": "\n", "r": "\r", "t": "\t"}


def zakoduj(text: str) -> str:
    """Tekst gry jako jedna linia pliku."""
    return "".join(_KODY.get(char, char) for char in text)


def odkoduj(line: str) -> str:
    """Odwrotność `zakoduj`; nieznana sekwencja z ukośnikiem zostaje bez zmian."""
    out = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line) and line[index + 1] in _ODKODY:
            out.append(_ODKODY[line[index + 1]])
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


# Kody gry, które muszą przejść do tłumaczenia bez zmian. Kolejność wariantów
# ma znaczenie: dłuższe i bardziej szczegółowe wzorce stoją pierwsze.
TOKEN = re.compile(
    r"\[\[|\]\]"  # nawiasy bloku warunkowego [[{4}?…]]
    r"|</?[A-Z]+(?:\s[^<>\n]*)?>"  # <LINK id='…'>, </LINK>, <IMAGE …>
    r"|(?:\|[^|<>\n]*)+>"  # końcówka odnośnika <nazwa|780|#C|15>
    r"|\{[^{}\n]*\}"  # {}, {0}, {name}, {1:.1f}
    r"|\$[A-Za-z_][A-Za-z_0-9]*(?:\([^()\n]*\))?"  # $T(2001), $E, $STEADY_CRI
    r"|%(?:\d+\$)?[-0-9.]*[sdf%]"  # %s, %d, %02d, %.2f, %%
    r"|#[0-9a-f][0-9a-fA-F]{5}(?![0-9a-fA-F])"  # kolor #a66b3c
    r"|#[A-Z]"  # #Y … #E, #R, #G, #H, #C
    r"|\[#[^\[\]\n]{1,12}\]"  # emotikony [#201], [#微笑]
    r"|@[Tt]"
    r"|(?:\\\\)+[nt\"'v]?"  # dosłowny ukośnik z tekstu gry (po zakodowaniu podwojony): \\n, \\"
)


def tokeny(zakodowany: str) -> list[str]:
    """Kody gry w tekście zakodowanym do jednej linii, w kolejności wystąpienia."""
    return TOKEN.findall(zakodowany)


def rozne_tokeny(zakodowany: str) -> list[str]:
    """Kody bez powtórzeń, w kolejności pierwszego wystąpienia (do linii `tokeny:`)."""
    return list(dict.fromkeys(tokeny(zakodowany)))


def roznica_tokenow(zrodlo: str, przeklad: str) -> tuple[list[str], list[str]]:
    """(brakujące w przekładzie, nadmiarowe w przekładzie), oba teksty zakodowane."""
    source, target = Counter(tokeny(zrodlo)), Counter(tokeny(przeklad))
    return sorted((source - target).elements()), sorted((target - source).elements())


def brzegi(text: str) -> tuple[str, str]:
    """Białe znaki z początku i końca tekstu gry — import dopisuje je do przekładu."""
    stripped = text.strip()
    if not stripped:
        return "", ""
    start = text.index(stripped[0])
    return text[:start], text[start + len(stripped):]


_KLUCZ = re.compile(r"^\s+klucz:\s*(@?[0-9a-f]{16})\s*$")
_PL = re.compile(r"^\s+PL:(.*)$")
_ELEMENT = re.compile(r"^\d+\. \[")


class Wpis(NamedTuple):
    klucz: str  # 16 znaków klucza tekstu albo `@` + 16 znaków id tekstu
    pl: str  # treść po `PL:`, bez białych znaków na brzegach, jeszcze zakodowana
    linia: int  # numer linii `PL:` w pliku (od 1)
    ciag_dalszy: bool  # po `PL:` stoi jeszcze linia tekstu — przekład złamany na dwie linie


def czytaj_wpisy(tekst_pliku: str) -> Iterator[Wpis]:
    """Wszystkie pary `klucz:` + `PL:` z pliku pakietu, także z pustym `PL:`."""
    lines = tekst_pliku.splitlines()
    pending: str | None = None
    for number, line in enumerate(lines, 1):
        match = _KLUCZ.match(line)
        if match:
            pending = match.group(1)
            continue
        match = _PL.match(line)
        if match and pending is not None:
            following = lines[number] if number < len(lines) else ""
            continued = bool(following.strip()) and not (
                _ELEMENT.match(following) or following.lstrip().startswith(("#", "-", "(", "—", "|"))
            )
            yield Wpis(pending, match.group(1).strip(), number, continued)
            pending = None
        elif _ELEMENT.match(line):
            pending = None
