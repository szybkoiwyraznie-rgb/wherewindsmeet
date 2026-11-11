#!/usr/bin/env python3
"""Render a translator package (SRW-style) from extracted locale entries.

Package layout:

    <out>/README.md          instructions for the translator
    <out>/widoki/<name>.md   numbered entries, split over several files
    <out>/tokeny.tsv         every non-translatable token with its meaning
    <out>/manifest.json      per-entry data for the importer (not for the translator)

Each element is either a full entry

    1. [Tekst] first line of the source
       id: 0123456789abcdef
       limit: 15 B
       EN: Northmount West
       PL:

or an inherited repeat of an earlier text, which the translator copies instead
of retranslating:

    2. [Tekst] Northmount West
       id: fedcba9876543210
       copy_of: 0123456789abcdef
       limit: 15 B

Numbering is fixed and never renumbered afterwards: the importer matches on
`id`, so entries may be added later without shifting anything.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

TOKEN_PATTERNS = (
    ("kolor", re.compile(r"#(?![Ee])[A-Za-z]")),
    ("zamkniecie", re.compile(r"#E")),
    ("podstawienie", re.compile(r"\{[^{}]*\}")),
    ("funkcja", re.compile(r"\$[A-Za-z]+\([^()]*\)")),
    ("warunek", re.compile(r"\[\[.*?\]\]")),
)

TOKEN_MEANINGS = {
    "kolor": "kolor tekstu; para z #E zamyka kolor",
    "zamkniecie": "zamyka poprzedni kolor",
    "podstawienie": "wstawiana wartość; nie zmieniaj wnętrza",
    "funkcja": "wywołanie funkcji gry; nie zmieniaj argumentów",
    "warunek": "wariant zależny od warunku; przepisz bez zmian",
}

README = """# Paczka dla Tłumacza — Where Winds Meet

## 0. Co to jest

Teksty z gry w oryginale angielskim. Tłumaczysz **tylko** linie `PL:`.

## 1. Zasady

1. Nie zmieniaj numeracji ani kolejności elementów.
2. Nie zmieniaj linii `EN:` — to tekst źródłowy z gry.
3. Nie usuwaj linii `id:`, `copy_of:` ani `limit:`.
4. `limit:` to liczba bajtów oryginału. Trzymaj się jej: polski tekst bywa
   dłuższy, ale nie przekraczaj limitu o więcej niż 20%.
5. Element z `copy_of:` powtarza wcześniejszy tekst. Wpisz w `PL:` dokładnie to
   samo, co przy wskazanym elemencie — nie tłumacz go inaczej drugi raz.
   Patcher sam podstawi tłumaczenie z `copy_of`, więc `PL:` możesz zostawić puste.
6. Tokeny z `tokeny.tsv` (`#Y`, `#E`, `$T(...)`, `{...}`, `[[...]]`) przepisz bez
   zmian, w tej samej liczbie i kolejności.
7. Pusty `PL:` znaczy „jeszcze nieprzetłumaczone”.
8. Kodowanie: UTF-8, bez BOM. Końce linii w pliku: LF.

## 2. Element wielolinijkowy

Każda linia oryginału ma własną linię `EN:` i własną `PL:` — zachowaj tę samą
liczbę linii:

```text
7. [Tekst] Zaproszenie
   id: 0011223344556677
   limit: 34 B
   EN: Przybywaj do nas
   EN: o świcie.
   PL:
   PL:
```

Tekst jednej linii nie może zawierać znaku tabulacji ani końca linii.

## 3. Czego ta paczka jeszcze nie ma

- mówcy i kolejności scen — nie są jeszcze odczytane z gry,
- podziału na widoki interfejsu — trwa ustalanie,
- limitów pól interfejsu innych niż długość oryginału.
"""


def normalise(text: str) -> tuple[str, bool]:
    """Collapse CR/CRLF to LF; report whether the source used CRLF or CR."""
    used_crlf = "\r" in text
    return text.replace("\r\n", "\n").replace("\r", "\n"), used_crlf


def render_entry(number: int, entry: dict, group: str, *, copy_of: str | None = None) -> list[str]:
    text, _ = normalise(entry["text"])
    lines = text.split("\n")
    head = lines[0].strip() or "(pusty)"
    if len(head) > 120:
        head = head[:117] + "..."
    rendered = [f"{number}. [{group}] {head}"]
    rendered.append(f"   id: {entry['id']}")
    if copy_of:
        rendered.append(f"   copy_of: {copy_of}")
    rendered.append(f"   limit: {len(entry['text'].encode('utf-8'))} B")
    if copy_of:
        return rendered
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
    for name, _pattern in TOKEN_PATTERNS:
        for example in tokens.get(name, []):
            rows.append(f"{name}\t{example}\t{TOKEN_MEANINGS[name]}")
    return "\n".join(rows) + "\n"


def build_pack(
    entries,
    out_dir: Path,
    *,
    group: str = "Tekst",
    view: str = "00_teksty",
    per_file: int = 25000,
) -> dict:
    out_dir = Path(out_dir)
    views_dir = out_dir / "widoki"
    views_dir.mkdir(parents=True, exist_ok=True)

    seen: dict[str, str] = {}
    manifest = []
    body: list[str] = []
    tokens = {}

    written = 0

    def flush(index: int) -> None:
        nonlocal written
        if not body:
            return
        header = [
            f"# {view} — część {index + 1}",
            "",
            "Numeracja jest stała i ciągła w całej paczce. Tłumacz tylko linie `PL:`.",
            "",
        ]
        (views_dir / f"{view}_{index + 1:03d}.md").write_text("\n".join(header + body), encoding="utf-8")
        written += 1
        body.clear()

    number = 0
    for entry in entries:
        number += 1
        first = seen.get(entry["text"])
        if first is None:
            seen[entry["text"]] = entry["id"]
        copy_of = None if first is None else first
        text, crlf = normalise(entry["text"])
        manifest.append(
            {
                "n": number,
                "id": entry["id"],
                "bytes": len(entry["text"].encode("utf-8")),
                "lines": text.count("\n") + 1,
                "crlf": crlf,
                "copy_of": copy_of,
            }
        )
        body.extend(render_entry(number, entry, group, copy_of=copy_of))
        body.append("")
        for name, pattern in TOKEN_PATTERNS:
            for match in pattern.findall(text):
                tokens.setdefault(name, [])
                if match not in tokens[name]:
                    tokens[name].append(match)
        if number % per_file == 0:
            flush(written)

    flush(written)
    (out_dir / "README.md").write_text(README, encoding="utf-8")
    (out_dir / "tokeny.tsv").write_text(render_tokens(tokens), encoding="utf-8")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return {
        "entries": number,
        "unique": len(seen),
        "inherited": number - len(seen),
        "files": written,
        "tokens": sum(len(v) for v in tokens.values()),
    }


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
    parser.add_argument("--widok", default="00_teksty", help="base name of the view files")
    parser.add_argument("--na-plik", type=int, default=25000, help="entries per view file")
    arguments = parser.parse_args(argv)
    result = build_pack(
        load_entries(arguments.entries),
        Path(arguments.out),
        group=arguments.grupa,
        view=arguments.widok,
        per_file=arguments.na_plik,
    )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
