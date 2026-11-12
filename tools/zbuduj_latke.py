#!/usr/bin/env python3
"""Łatka tłumaczenia: przepisuje mapy tekstów gry polskimi przekładami z magazynu.

    python3 tools/zbuduj_latke.py --indeks index --magazyn tlumaczenie \
        --zh translate_words_map_zh_cn [translate_words_map_zh_cn_diff ...] \
        --mapa Package/HD/oversea/locale/translate_words_map_en path/en \
        --mapa Package/HD/oversea/locale/translate_words_map_en_diff path/pkg_diff \
        --mapa LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff path/patch_diff \
        --build-gry 25906190 --wyj dist/latka

Gra nie ma języka polskiego, więc przekład zastępuje teksty jednego z języków
klienta (tu: plików podanych w `--mapa` albo `--cel`, zwykle angielskich). Każdy
plik celu — mapa podstawowa i jej warstwy `_diff` — jest przepisywany osobno
i zapisywany w katalogu wyjściowym. Oryginały nie są zmieniane.

Skąd bierze się przekład jednego wpisu (identyfikatora tekstu):
1. z magazynu po identyfikatorze (`pl_warianty.jsonl`) — kwestie zależne od płci
   bohatera; pusty wariant dziedziczy po drugim wariancie tego samego tekstu;
2. z magazynu po kluczu tekstu źródłowego: klucz liczy się z tekstu chińskiego
   tego identyfikatora (`--zh`), a gdy chińskiego nie ma — z tekstu w pliku celu.

Wpis bez przekładu zostaje bez zmian. Po zapisaniu każdy plik jest czytany
z powrotem i porównywany wpis po wpisie: zmienić się mogły tylko wpisy
z przekładadem i tylko na ten przekład.

To narzędzie nie instaluje niczego w grze i **nie było sprawdzone w grze** —
patrz docs/PAKIET_TLUMACZA.md, rozdział o łatce.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    from tools import apply_translation as patcher
    from tools import indeks as indeks_mod
    from tools import locale_records as records
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import apply_translation as patcher
    from tools import indeks as indeks_mod
    from tools import locale_records as records
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz


class LatkaError(Exception):
    """Łatki nie da się zbudować albo wynik nie przeszedł kontroli."""


def normalizuj_sciezke_gry(raw: str) -> str:
    """Sprawdź i znormalizuj względną ścieżkę celu w instalacji gry."""
    cleaned = raw.replace("\\", "/").strip()
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if not cleaned or ":" in cleaned or "\x00" in cleaned or cleaned.startswith("/"):
        raise LatkaError(f"niebezpieczna ścieżka w grze: {raw!r}")
    parts = cleaned.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise LatkaError(f"niebezpieczna ścieżka w grze: {raw!r}")
    if parts[0].lower() == "package":
        parts[0] = "Package"
    elif len(parts) >= 2 and parts[0].lower() == "localdata" and parts[1].lower() == "patch":
        parts[0], parts[1] = "LocalData", "Patch"
    else:
        raise LatkaError(f"ścieżka w grze musi zaczynać się od Package/ albo LocalData/Patch/: {raw!r}")
    return "/".join(parts)


def wywnioskuj_sciezke_gry(path: Path) -> str | None:
    """Wyciągnij względną ścieżkę `Package/...` lub `LocalData/Patch/...`, jeśli widać ją w ścieżce."""
    parts = path.as_posix().split("/")
    for i, part in enumerate(parts):
        low = part.lower()
        if low == "package" and i + 1 < len(parts):
            return normalizuj_sciezke_gry("/".join(parts[i:]))
        if low == "localdata" and i + 2 < len(parts) and parts[i + 1].lower() == "patch":
            return normalizuj_sciezke_gry("/".join(parts[i:]))
    return None


def rodzenstwo_wariantow(warianty: dict[str, dict]) -> dict[str, list[str]]:
    """Klucz tekstu -> identyfikatory (hex) kwestii zależnych od płci z tym tekstem."""
    groups: dict[str, list[str]] = defaultdict(list)
    for ident in sorted(warianty):
        groups[warianty[ident]["k"]].append(ident)
    return groups


def _dopasuj_kolizje(warianty_zh: list[list[str]], current: str, magazyn: magazyn_mod.Magazyn) -> str | None:
    """Dobierz wariant tłumaczenia dla tekstu `zh`, który ma rozbieżne znaczenia w EN."""
    for key, rep_en in warianty_zh:
        if rep_en == current:
            return magazyn.po_kluczu.get(key)
    best_key, best_sim = None, 0.0
    for key, rep_en in warianty_zh:
        score = mapa_tekstow.podobienstwo_en(current, rep_en)
        if score > best_sim:
            best_key, best_sim = key, score
    if best_key is not None and best_sim >= 0.5:
        return magazyn.po_kluczu.get(best_key)
    return None


def przeklady_pliku(
    teksty: dict[int, str],
    zh: dict[int, str],
    magazyn: magazyn_mod.Magazyn,
    warianty: dict[str, dict],
    rodzenstwo: dict[str, list[str]],
    kolizje: dict[str, list[list[str]]] | None = None,
) -> dict[int, str]:
    """`id -> przekład` dla wpisów jednego pliku; tylko wpisy, które się zmienią."""
    wanted: dict[int, str] = {}
    for ident, current in teksty.items():
        hex_id = f"{ident:016x}"
        text = magazyn.po_id.get(hex_id)
        if text is None and hex_id in warianty:
            for sibling in rodzenstwo.get(warianty[hex_id]["k"], ()):
                if sibling in magazyn.po_id:
                    text = magazyn.po_id[sibling]
                    break
        if text is None:
            source = zh.get(ident, current)
            if kolizje and source in kolizje:
                text = _dopasuj_kolizje(kolizje[source], current, magazyn)
            else:
                text = magazyn.po_kluczu.get(mapa_tekstow.klucz(source))
        if text and text != current:
            wanted[ident] = text
    return wanted


def przepisz(
    path: Path,
    cel: Path,
    zh: dict[int, str],
    magazyn,
    warianty,
    rodzenstwo,
    poziom: int = 9,
    *,
    plik_latki: str | None = None,
    sciezka_w_grze: str | None = None,
    kolizje: dict[str, list[list[str]]] | None = None,
) -> dict:
    """Przepisz jeden plik mapy do `cel` i zwróć raport; rzuca `LatkaError` przy niezgodności."""
    try:
        data = path.read_bytes()
        teksty, _removed = mapa_tekstow.wczytaj_warstwe(path)
        wanted = przeklady_pliku(teksty, zh, magazyn, warianty, rodzenstwo, kolizje=kolizje)
        patched, stats = patcher.apply_translations(data, wanted, level=poziom, text_map={})
        check = patcher.verify(data, patched, wanted, text_map={})
    except (OSError, mapa_tekstow.MapaError, patcher.PatchError, records.LayoutError) as error:
        raise LatkaError(f"{path.name}: {error}") from error
    if check["changed"] != len(wanted) or stats["ids_not_in_map"]:
        raise LatkaError(f"{path.name}: zmieniono {check['changed']} wpisów, oczekiwano {len(wanted)}")
    cel.parent.mkdir(parents=True, exist_ok=True)
    cel.write_bytes(patched)
    entry = {
        "plik": path.name,
        "plik_latki": plik_latki or cel.name,
        "wpisow": len(teksty),
        "przetlumaczonych": len(wanted),
        "procent": round(100 * len(wanted) / len(teksty), 2) if teksty else 0,
        "bajtow_przed": len(data),
        "bajtow_po": len(patched),
        "sha256_przed": mapa_tekstow.sha256_pliku(path),
        "sha256_po": mapa_tekstow.sha256_pliku(cel),
    }
    if sciezka_w_grze is not None:
        entry["sciezka_w_grze"] = sciezka_w_grze
    return entry


def main(argv=None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description="Zbuduj łatkę: mapy tekstów z polskimi przekładami.")
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--magazyn", default="tlumaczenie")
    parser.add_argument("--zh", nargs="+", required=True, help="mapa zh_cn i jej warstwy _diff, w kolejności nakładania")
    parser.add_argument("--cel", action="append", default=[], help="plik mapy do przepisania (można podać kilka razy)")
    parser.add_argument("--mapa", nargs=2, action="append", default=[], metavar=("SCIEZKA_W_GRZE", "PLIK"),
                        help="para: względna ścieżka w grze (np. Package/HD/oversea/locale/...) i plik źródłowy")
    parser.add_argument("--build-gry", default="", help="opcjonalny buildid Steam, dla którego powstała łatka")
    parser.add_argument("--wyj", required=True, help="katalog na przepisane pliki i raport latka.json")
    parser.add_argument("--poziom", type=int, default=9, help="poziom kompresji zstd")
    arguments = parser.parse_args(argv)

    if not arguments.cel and not arguments.mapa:
        print(json.dumps({"ok": False, "powod": "podaj co najmniej jedno --cel albo --mapa"}, ensure_ascii=False))
        return 1

    out = Path(arguments.wyj)
    try:
        items: list[tuple[Path, str | None]] = []
        for raw_path in arguments.cel:
            path = Path(raw_path)
            items.append((path, wywnioskuj_sciezke_gry(path)))
        for game_rel, raw_path in arguments.mapa:
            items.append((Path(raw_path), normalizuj_sciezke_gry(game_rel)))
    except LatkaError as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1

    use_tree = bool(arguments.mapa) or len({path.name for path, _ in items}) != len(items)
    if use_tree:
        if any(game_rel is None for _, game_rel in items):
            print(json.dumps({"ok": False, "powod": "dwa pliki celu mają tę samą nazwę — podaj pary przez --mapa SCIEZKA_W_GRZE PLIK"}, ensure_ascii=False))
            return 1
        seen_rel = set()
        planned: list[tuple[Path, str, str | None]] = []
        for path, game_rel in items:
            key = game_rel.casefold()
            if key in seen_rel:
                print(json.dumps({"ok": False, "powod": f"powtórzona ścieżka w grze: {game_rel}"}, ensure_ascii=False))
                return 1
            seen_rel.add(key)
            planned.append((path, f"pliki/{game_rel}", game_rel))
    else:
        planned = [(path, path.name, game_rel) for path, game_rel in items]

    if any(out.resolve() == path.parent.resolve() for path, _, _ in planned):
        print(json.dumps({"ok": False, "powod": "katalog wyjściowy nie może być katalogiem plików celu"}, ensure_ascii=False))
        return 1
    try:
        ix = indeks_mod.wczytaj(arguments.indeks, teksty=False, sceny=False)
        magazyn = magazyn_mod.wczytaj(arguments.magazyn)
        if not len(magazyn):
            raise LatkaError("magazyn przekładów jest pusty — nie ma czego wstawiać")
        zh = mapa_tekstow.zloz(arguments.zh)
        siblings = rodzenstwo_wariantow(ix.warianty)
        out.mkdir(parents=True, exist_ok=True)
        files = [
            przepisz(
                path,
                out / patch_rel,
                zh,
                magazyn,
                ix.warianty,
                siblings,
                arguments.poziom,
                plik_latki=patch_rel,
                sciezka_w_grze=game_rel,
                kolizje=ix.kolizje,
            )
            for path, patch_rel, game_rel in planned
        ]
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, mapa_tekstow.MapaError, LatkaError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    report = {
        "format": "wwm-latka-v1",
        "przekladow_w_magazynie": len(magazyn),
        "pliki": files,
        "uwaga": "łatka nie była sprawdzona w grze; przed podmianą plików zrób kopię oryginałów",
    }
    if arguments.build_gry:
        report["build_gry"] = arguments.build_gry
    (out / "latka.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, **report}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
