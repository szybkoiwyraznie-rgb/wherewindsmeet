#!/usr/bin/env python3
"""Render a translator package (SRW-style) from extracted locale entries.

Package layout:

    <out>/README.md          instructions for the translator
    <out>/widoki/<name>.md   numbered entries, split over several files
    <out>/tokeny.tsv         every non-translatable token with its meaning
    <out>/manifest.json      per-entry data for the importer (not for the translator)

Every distinct source text appears exactly once:

    1. [Tekst] Northmount West
       id: 0123456789abcdef
       limit: 15 B
       PL:

A text that occurs many times in the game is still a single element — the
patcher fills every occurrence with the same translation. Repeats are counted,
not rendered, so the package stays close to the size of the text itself.

Multi-line texts carry their lines under `EN:` (one `PL:` per line): the header
line is the first line only when the text is a single line.

Numbering is fixed and never renumbered afterwards.
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
5. Każdy tekst występuje w paczce **raz**, nawet jeśli w grze powtarza się
   wiele razy. Patcher sam podstawi to samo tłumaczenie we wszystkich miejscach,
   więc nie tłumacz tego samego tekstu dwa razy.
6. Tokeny z `tokeny.tsv` (`#Y`, `#E`, `$T(...)`, `{...}`, `[[...]]`) przepisz bez
   zmian, w tej samej liczbie i kolejności.
7. Pusty `PL:` znaczy „jeszcze nieprzetłumaczone”.
8. Kodowanie: UTF-8, bez BOM. Końce linii w pliku: LF.

## 2. Element wielolinijkowy

Tekst jednej linii stoi w nagłówku elementu. Tekst wielolinijkowy ma nagłówek
bez treści, a każdą linię pod `EN:` — z taką samą liczbą linii `PL:`:

```text
7. [Tekst]
   id: 0011223344556677
   limit: 34 B
   EN: Przybywaj do nas
   EN: o świtie.
   PL:
   PL:
```

## 3. Czego ta paczka jeszcze nie ma

- mówcy i kolejności scen — nie są jeszcze odczytane z gry,
- podziału na widoki interfejsu — trwa ustalanie,
- limitów pól interfejsu innych niż długość oryginału.
"""


def normalise(text: str) -> tuple[str, bool]:
    """Collapse CR/CRLF to LF; report whether the source used CRLF or CR."""
    used_crlf = "\r" in text
    return text.replace("\r\n", "\n").replace("\r", "\n"), used_crlf


def render_entry(number: int, entry: dict, group: str) -> list[str]:
    text, _ = normalise(entry["text"])
    lines = text.split("\n")
    head = lines[0].strip()
    rendered = []
    if len(lines) == 1:
        if len(head) > 160:
            head = head[:157] + "..."
        rendered.append(f"{number}. [{group}] {head}" if head else f"{number}. [{group}] (pusty)")
    else:
        rendered.append(f"{number}. [{group}]")
    rendered.append(f"   id: {entry['id']}")
    rendered.append(f"   limit: {len(entry['text'].encode('utf-8'))} B")
    if len(lines) > 1:
        for line in lines:
            rendered.append(f"   EN: {line}")
        for _ in lines:
            rendered.append("   PL:")
    else:
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
    per_file: int = 20000,
) -> dict:
    out_dir = Path(out_dir)
    views_dir = out_dir / "widoki"
    views_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    crlf_ids = []
    body: list[str] = []
    tokens: dict[str, list[str]] = {}
    number = 0
    inherited = 0
    written = 0

    def flush() -> None:
        nonlocal written
        if not body:
            return
        header = [
            f"# {view} — część {written + 1}",
            "",
            "Numeracja jest stała i ciągła w całej paczce. Tłumacz tylko linie `PL:`.",
            "",
        ]
        (views_dir / f"{view}_{written + 1:03d}.md").write_text(
            "\n".join(header + body), encoding="utf-8"
        )
        written += 1
        body.clear()

    for entry in entries:
        text = entry["text"]
        if text in seen:
            inherited += 1
            continue
        seen.add(text)
        number += 1
        normalised, crlf = normalise(text)
        if crlf:
            crlf_ids.append(entry["id"])
        body.extend(render_entry(number, entry, group))
        body.append("")
        for name, pattern in TOKEN_PATTERNS:
            for match in pattern.findall(normalised):
                tokens.setdefault(name, [])
                if match not in tokens[name]:
                    tokens[name].append(match)
        if number % per_file == 0:
            flush()

    flush()
    (out_dir / "README.md").write_text(README, encoding="utf-8")
    (out_dir / "tokeny.tsv").write_text(render_tokens(tokens), encoding="utf-8")
    (out_dir / "manifest.json").write_text(
        json.dumps(
            {
                "elements": number,
                "inherited": inherited,
                "files": written,
                "groups": [group],
                "crlf_ids": crlf_ids,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {
        "elements": number,
        "inherited": inherited,
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
    parser.add_argument("--na-plik", type=int, default=20000, help="entries per view file")
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
