#!/usr/bin/env python3
"""Buduje trwały indeks korpusu scen z prywatnych wyjść `tools/timeline.py`.

Dlaczego ten krok istnieje: wyniki ekstrakcji żyją w ignorowanym `local/`, który
może zniknąć, a dane źródłowe przychodzą prywatnym kanałem. Patcher i skrypty
budujące paczki nie mogą więc zależeć ani od `local/`, ani od plików z Dysku —
mają czytać **indeks z repozytorium**. Ten skrypt wykonuje się raz, na prywatnych
danych, i zapisuje wynik do wersjonowanego katalogu `index/`.

Co trafia do indeksu (i czego nie ma):

    index/manifest.json     liczby, pokrycie rejestru, inwentarz SHA-256, shardy
    index/sceny_NNN.jsonl   sceny z liniami; linia trzyma `text_id`, nie tekst
    index/teksty_NNN.jsonl  unikalne `text_id` -> tekst chiński (źródło przekładu)

Tekst stoi tylko w `teksty_*`, więc nie jest powtarzany przy każdej kwestii.
`tekst_mapa` dopisywany jest wyłącznie wtedy, gdy mapa źródłowa (`zh_cn`) ma dla
tego samego `text_id` dłuższą wersję — z dopiskiem scenicznym w nawiasach, który
scena już obcięła. Tłumaczy się wersję z mapy.

Pomijamy świadomie: `formatted_text` (jest w `teksty_*`), `chunk`/`chunk_index`
(szczegóły ekstrakcji, nie danych) oraz dosłowną wartość `skeleton` — w danych
źródłowych ten sam mówcy (ta sama para `mowca` + `speaker_no`) bywa zapisany raz
z pustym ciągiem, a raz bez wartości, więc indeks trzyma **pierwszą** napotkaną
postać. Żadne narzędzie potokowe tego pola nie używa; identyfikacja mówcy to
`mowca` i `speaker_no`.

Użycie:
    python3 tools/buduj_indeks.py --sceny local/sceny_data201.jsonl ... \
        --mapa google_drive/translate_words_map_zh_cn --wyj index
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    from tools import apply_translation as patcher  # noqa: PLC0415 - import pakietu
    from tools import locale_records as records  # noqa: PLC0415 - import pakietu
except ImportError:  # pragma: no cover - uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import apply_translation as patcher
    from tools import locale_records as records

FORMAT = "wwm-indeks-v1"
DEFAULT_SHARD_BYTES = 9 * 1024 * 1024  # limit repozytorium to 10 MiB na plik


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_scenes(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    """Sceny w kolejności podanych plików plus inwentarz każdego pliku."""
    scenes: list[dict] = []
    inventory: list[dict] = []
    for path in paths:
        count = 0
        lines = 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                scene = json.loads(line)
                scene["plik"] = path.stem.removeprefix("sceny_")
                scenes.append(scene)
                count += 1
                lines += len(scene.get("lines") or [])
        inventory.append(
            {
                "plik": path.name,
                "bajtow": path.stat().st_size,
                "sha256": sha256_of(path),
                "scen": count,
                "kwestii": lines,
            }
        )
    return scenes, inventory


def project_scene(scene: dict) -> dict:
    """Scena bez tekstu: linie trzymają tylko `text_id`.

    Ten sam `entity_tag` może w scenie oznaczać **dwóch** różnych mówców (różne
    `entity_no`), więc obsada jest kluczowana parą (mowca, speaker_no), a sama
    para trafia też do linii — inaczej odtworzenie sceny zgubiłoby numer.
    """
    cast: dict[tuple, dict] = {}
    rows = []
    for line in scene.get("lines") or []:
        tag = line.get("speaker")
        number = line.get("speaker_no")
        key = (tag, number)
        if key not in cast:
            cast[key] = {"mowca": tag, "speaker_no": number, "skeleton": line.get("skeleton")}
        rows.append(
            {
                "text_id": line.get("text_id"),
                "mowca": tag,
                "speaker_no": number,
                "czas": line.get("time"),
                "kolejnosc": line.get("order"),
                "source_id": line.get("source_id"),
            }
        )
    return {
        "scena": f"{scene['plik']}:{scene.get('chunk_index', 0):06d}",
        "plik": scene["plik"],
        "dialog_no": scene.get("dialog_no"),
        "projekt": scene.get("project"),
        "timeline_id": scene.get("timeline_id"),
        "start_time": scene.get("start_time"),
        "total_duration": scene.get("total_duration"),
        "obsada": list(cast.values()),
        "linie": rows,
    }


def map_texts(path: Path) -> dict[str, str]:
    """Unikalne `text_id` -> tekst z mapy źródłowej (kontener + zstd)."""
    texts: dict[str, str] = {}
    chunks = patcher.read_container(path.read_bytes())
    for chunk in chunks[1:]:
        kind, payload = patcher.split_chunk(chunk)
        try:
            blob = patcher.decompress(kind, payload)
        except Exception:  # noqa: BLE001 - uszkodzony chunk nie zatrzymuje budowy
            continue
        table = records.parse_table(blob)
        for entry in table["entries"]:
            if entry["id"] and entry["length"] and not entry["placeholder"]:
                texts[f"{entry['id']:016x}"] = entry["text"].decode("utf-8", "replace")
    return texts


def write_shards(records_list: list[dict], prefix: str, out: Path, limit: int) -> list[dict]:
    """Zapisuje rekordy do `prefix_NNN.jsonl`, żaden plik nie przekracza `limit`."""
    shards: list[dict] = []
    number = 0
    buffer: list[str] = []
    size = 0
    for record in records_list:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        width = len(line.encode("utf-8"))
        if buffer and size + width > limit:
            shards.append(_flush(buffer, prefix, number, out))
            number += 1
            buffer, size = [], 0
        buffer.append(line)
        size += width
    if buffer:
        shards.append(_flush(buffer, prefix, number, out))
    return shards


def _flush(lines: list[str], prefix: str, number: int, out: Path) -> dict:
    name = f"{prefix}_{number:03d}.jsonl"
    payload = "".join(lines).encode("utf-8")
    (out / name).write_bytes(payload)
    return {"plik": name, "linie": len(lines), "bajtow": len(payload)}


def build(scenes_paths: list[Path], mapa: Path | None, rejestr: Path | None,
          out: Path, limit: int, data: str | None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.jsonl"):
        stale.unlink()

    scenes, inventory = load_scenes(scenes_paths)
    projected = [project_scene(scene) for scene in scenes]

    # Unikalne teksty: scena jest źródłem, mapa źródłowa uzupełnia wersję dłuższą.
    texts: dict[str, str] = {}
    for scene in scenes:
        for line in scene.get("lines") or []:
            key = line.get("text_id")
            if key and key not in texts:
                texts[key] = line.get("formatted_text") or ""
    longer: dict[str, str] = {}
    if mapa is not None:
        source = map_texts(mapa)
        for key, text in texts.items():
            full = source.get(key)
            if full is not None and full != text:
                longer[key] = full

    text_rows = [
        {"text_id": key, "tekst_zh": texts[key], **({"tekst_mapa": longer[key]} if key in longer else {})}
        for key in sorted(texts)
    ]

    scene_shards = write_shards(projected, "sceny", out, limit)
    text_shards = write_shards(text_rows, "teksty", out, limit)

    coverage = None
    if rejestr is not None:
        from tools import manifest_keys  # noqa: PLC0415 - tylko gdy podano rejestr

        payload = manifest_keys.read_payload(rejestr)
        dialogues = manifest_keys.dialog_ids(manifest_keys.keys_from_payload(payload))
        ours = {s.get("dialog_no") for s in scenes if isinstance(s.get("dialog_no"), int)}
        coverage = {
            "dialog_timelines": len(dialogues),
            "scen_z_dialog_no": len(ours),
            "scen_poza_rejestrem": len(ours - dialogues),
            "pokrycie_procent": round(100 * len(ours) / len(dialogues), 1) if dialogues else 0.0,
            "brakuje_dialogow": len(dialogues - ours),
        }

    manifest = {
        "format": FORMAT,
        **({"utworzono": data} if data else {}),
        "liczby": {
            "scen": len(scenes),
            "kwestii": sum(len(s.get("lines") or []) for s in scenes),
            "unikalnych_tekstow": len(texts),
            "mowcow": len({ln.get("speaker") for s in scenes for ln in (s.get("lines") or [])}),
            "tekstow_z_dluzsza_wersja_mapy": len(longer),
        },
        **({"pokrycie": coverage} if coverage else {}),
        "zrodla": {
            **({"mapa": {"plik": mapa.name, "bajtow": mapa.stat().st_size,
                         "sha256": sha256_of(mapa)}} if mapa else {}),
            **({"rejestr": {"plik": rejestr.name, "bajtow": rejestr.stat().st_size,
                            "sha256": sha256_of(rejestr)}} if rejestr else {}),
            "sceny": inventory,
        },
        "shardy": {"sceny": scene_shards, "teksty": text_shards},
        "pominiete": [
            "formatted_text (jest w shardach tekstow)",
            "chunk, chunk_index (szczegoly ekstrakcji)",
            "doslowna wartosc skeleton: ten sam mowca bywa w zrodle zapisany z '' i bez wartosci, indeks trzyma pierwsza napotkana; narzedzia potokowe nie uzywaja tego pola",
        ],
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Zapisuje trwały indeks korpusu scen do wersjonowanego katalogu.",
    )
    parser.add_argument("--sceny", nargs="+", required=True, type=Path,
                        help="JSONL ze scenami z tools/timeline.py")
    parser.add_argument("--mapa", type=Path, default=None,
                        help="mapa źródłowa translate_words_map_zh_cn (opcjonalnie)")
    parser.add_argument("--rejestr", type=Path, default=None,
                        help="MANIFEST do liczenia pokrycia (opcjonalnie)")
    parser.add_argument("--wyj", type=Path, default=Path("index"), help="katalog wyniku")
    parser.add_argument("--limit", type=int, default=DEFAULT_SHARD_BYTES,
                        help="maksymalny rozmiar shardu w bajtach")
    parser.add_argument("--data", default=None, help="data do zapisu w manifeście")
    arguments = parser.parse_args(argv)
    manifest = build(arguments.sceny, arguments.mapa, arguments.rejestr,
                     arguments.wyj, arguments.limit, arguments.data)
    print(json.dumps({
        "scen": manifest["liczby"]["scen"],
        "kwestii": manifest["liczby"]["kwestii"],
        "unikalnych_tekstow": manifest["liczby"]["unikalnych_tekstow"],
        "shardy_scen": len(manifest["shardy"]["sceny"]),
        "shardy_tekstow": len(manifest["shardy"]["teksty"]),
        "pokrycie": (manifest.get("pokrycie") or {}).get("pokrycie_procent"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
