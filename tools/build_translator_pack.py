#!/usr/bin/env python3
"""Render a translator package (SRW-style) from extracted locale entries.

The package mirrors the layout the translator already works with in the SRW
project:

    <out>/README.md        instructions for the translator
    <out>/widoki/*.md      numbered entries, one file per view
    <out>/tokeny.tsv       every non-translatable token, with its meaning

Each entry is rendered as

    1. [Group] first line of the text
       id: <stable id from the game>
       limit: <bytes of the original>
       EN: <original line 1>
       EN: <original line 2>
       PL:

`EN:` lines are frozen: the translator edits only the `PL:` lines, keeps the
numbering, and inherits a repeated original instead of retranslating it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Markup seen in the game's English texts. Anything matched here must survive
# translation unchanged, which is why it is listed in tokeny.tsv.
TOKEN_PATTERNS = (
    ("kolor", re.compile(r"#(?![Ee])[A-Za-z]")),
    ("zamkniecie", re.compile(r"#E")),
    ("podstawienie", re.compile(r"\{[^{}]*\}")),
    ("funkcja", re.compile(r"\$[A-Za-z]+\([^()]*\)")),
    ("warunek", re.compile(r"\[\[.*?\]\]")),
)

README = """# Paczka dla Tłumacza — Where Winds Meet

## 0. Co to jest

Teksty z gry w oryginale angielskim. Tłumaczysz **tylko** linie `PL:`.

## 1. Zasady

1. Nie zmieniaj numeracji ani kolejności elementów.
2. Nie zmieniaj linii `EN:` — to tekst źródłowy z gry, służy do porównania.
3. Nie usuwaj linii `id:` ani `limit:`.
4. `limit:` to liczba bajtów oryginału. Nie musisz się w nią wpisywać co do
   bajta, ale nie przekraczaj jej o więcej niż 20%.
5. Jeśli element powtarza wcześniejszy tekst, wpisz w `PL:` dokładnie ten sam
   tekst co poprzednio — nie tłumacz go drugi raz inaczej.
6. Tokeny z `tokeny.tsv` (`#Y`, `#E`, `$T(...)`, `{...}`, `[[...]]`) przepisz
   bez zmian, w tej samej liczbie i kolejności.
7. Pusty `PL:` znaczy „jeszcze nieprzetłumaczone”.
8. Kodowanie plików: UTF-8.

## 2. Format elementu

```text
1. [Postacie] Imię
   id: 0123456789abcdef
   limit: 15 B
   EN: Northmount West
   PL:
```

Element wielolinijkowy ma po jednej linii `EN:` na każdą linię oryginału;
w `PL:` zachowaj tę samą liczbę linii.

## 3. Czego nie ma w tej paczce

- mówcy i kolejności scen — nie są jeszcze odczytane z gry,
- tekstów z mapy głównej — trwa rozpracowanie jej indeksu,
- limitów pól interfejsu — do ustalenia.
"""


def render_entry(number: int, entry: dict, group: str) -> list[str]:
    text = entry["text"].replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    head = lines[0].strip() or "(pusty)"
    rendered = [f"{number}. [{group}] {head}"]
    rendered.append(f"   id: {entry['id']}")
    rendered.append(f"   limit: {len(text.encode('utf-8'))} B")
    for line in lines:
        rendered.append(f"   EN: {line}")
    for _ in lines:
        rendered.append("   PL:")
    return rendered


def collect_tokens(texts) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for text in texts:
        for name, pattern in TOKEN_PATTERNS:
            for match in pattern.findall(text):
                bucket = found.setdefault(name, [])
                if match not in bucket:
                    bucket.append(match)
    return found


def render_tokens(tokens: dict[str, list[str]]) -> str:
    rows = ["rodzaj\tprzyklad\tznaczenie"]
    meanings = {
        "kolor": "kolor tekstu; para z #E zamyka kolor",
        "zamkniecie": "zamyka poprzedni kolor",
        "podstawienie": "wstawiana wartość; nie zmieniaj wnętrza",
        "funkcja": "wywołanie funkcji gry; nie zmieniaj argumentów",
        "warunek": "wariant tekstu zależny od warunku; przepisz bez zmian",
    }
    for name, pattern in TOKEN_PATTERNS:
        for example in tokens.get(name, []):
            rows.append(f"{name}\t{example}\t{meanings[name]}")
    return "\n".join(rows) + "\n"


def build_pack(entries, out_dir: Path, *, group: str = "Tekst", view: str = "00_teksty") -> dict:
    out_dir = Path(out_dir)
    (out_dir / "widoki").mkdir(parents=True, exist_ok=True)
    body = [f"# {view}", "", "Numeracja jest stała. Tłumacz tylko linie `PL:`.", ""]
    for number, entry in enumerate(entries, 1):
        body.extend(render_entry(number, entry, group))
        body.append("")
    (out_dir / "widoki" / f"{view}.md").write_text("\n".join(body), encoding="utf-8")
    (out_dir / "README.md").write_text(README, encoding="utf-8")
    tokens = collect_tokens(entry["text"] for entry in entries)
    (out_dir / "tokeny.tsv").write_text(render_tokens(tokens), encoding="utf-8")
    return {"entries": len(entries), "tokens": sum(len(v) for v in tokens.values())}


def load_entries(path) -> list[dict]:
    entries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build a translator package from extracted entries.")
    parser.add_argument("entries", help="JSONL with one {id, text} object per line")
    parser.add_argument("out", help="output directory for the package")
    parser.add_argument("--grupa", default="Tekst", help="label shown in every entry header")
    arguments = parser.parse_args(argv)
    result = build_pack(load_entries(arguments.entries), Path(arguments.out), group=arguments.grupa)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
