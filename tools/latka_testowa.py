#!/usr/bin/env python3
"""Buduje małą, odwracalną łatkę testową UI i/lub prologu z polskimi znakami (ZIP z instalatorem Windows).

    python3 tools/latka_testowa.py \
      --indeks index \
      --zh path/translate_words_map_zh_cn [path/translate_words_map_zh_cn_diff ...] \
      --mapa Package/HD/oversea/locale/translate_words_map_en path/pkg_en \
      --mapa Package/HD/oversea/locale/translate_words_map_en_diff path/pkg_en_diff \
      --mapa LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff path/patch_en_diff \
      --build-gry 25906190 \
      --zakres ui+prolog \
      --wyj-zip dist/WWM_LATKA_TEST_PL.zip

Nie dotyka katalogu `tlumaczenie/`. W osobnym folderze tymczasowym tworzy
tymczasowy magazyn wyłącznie dla wybranych etykiet menu głównego/ustawień oraz
pierwszych napisów w prologu gry (tabele `text_msg` / `text_msg__grey`,
wiersze 590336–590351) zawierających wszystkie polskie znaki diakrytyczne
(ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż), przepuszcza go przez
`tools/zbuduj_latke.py` i pakuje razem ze skryptami `instalator/`
(`ZAINSTALUJ.bat`, `PRZYWROC.bat`, `SPRAWDZ_STAN.bat`). Szczegóły próby:
docs/TEST_W_GRZE.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

try:
    from tools import build_installer_kit
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
    from tools import zbuduj_latke
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import build_installer_kit
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
    from tools import zbuduj_latke


TEST_LABELS: dict[str, str] = {
    "Settings": "Ustawienia [PL: ą ć ę ł ń ó ś ź ż]",
    "Audio": "Dźwięk [Ą Ć Ę Ł Ń Ó Ś Ź Ż]",
    "Controls": "Sterowanie [PL]",
    "Display": "Wyświetlanie [PL]",
    "Language": "Język [ąęółńśźż]",
    "Storage": "Pamięć i pliki [PL]",
    "Text Magnification": "Powiększenie tekstu [PL]",
    "Parental Controls": "Kontrola rodzicielska [PL]",
    "New Game": "Nowa gra [PL]",
    "Exit": "Wyjście [PL]",
}

# Pierwsze napisy w cutscence prologu gry (tabele `text_msg` i `text_msg__grey`,
# wiersze 590336–590351). Dopasowywane parą (EN, ZH.strip()), żeby nie podmienić
# krótkich zwrotów w innych dialogach.
PROLOG_LINES: tuple[tuple[str, str, str], ...] = (
    ("It's you.", "是你", "To ty [PL: ą ć ę ł ń ó ś ź ż]."),
    ("Yes. Coming to catch you.", "是啊 来抓你", "Tak. Przyszliśmy cię pojmać [Ą Ć Ę Ł Ń Ó Ś Ź Ż]."),
    ("Even at the end of the road,", "穷途末路", "Nawet u kresu drogi [ą ć ę ł ń ó ś ź ż],"),
    ("a drink to wet your throat.", "尚有一饮入喉", "łyk trunku zwilży gardło [Ą Ć Ę Ł Ń Ó Ś Ź Ż]."),
    ("Well? How is it?", "如何", "I jak? Smakuje [ą ć ę ł ń ó ś ź ż]?"),
    ("Bland.", "淡", "Mdłe [Ą Ć Ę Ł Ń Ó Ś Ź Ż]."),
    ("Retrieve the Zhenguan Jade!", "夺下镇冠珏", "Odbierzcie Nefryt Zhenguan [ąęółńśźż]!"),
)

ZAKRESY = ("ui", "prolog", "ui+prolog")


def zbuduj_paczke_testowa(
    *,
    indeks_dir: str | Path,
    zh_paths: list[str | Path],
    cel_paths: list[str | Path],
    mapa_pairs: list[tuple[str, str | Path]],
    wyj_zip: str | Path,
    build_gry: str = "",
    poziom: int = 9,
    zakres: str = "ui+prolog",
) -> dict:
    """Zbuduj testowy ZIP instalacyjny dla wybranych napisów UI i/lub prologu; nie modyfikuje oryginałów."""
    if not cel_paths and not mapa_pairs:
        raise ValueError("podaj co najmniej jedno --cel albo --mapa")
    if zakres not in ZAKRESY:
        raise ValueError(f"nieznany zakres testu: {zakres!r} (dozwolone: {', '.join(ZAKRESY)})")

    use_ui = zakres in ("ui", "ui+prolog")
    use_prolog = zakres in ("prolog", "ui+prolog")
    prolog_by_pair = {(en, zh_key): pl for en, zh_key, pl in PROLOG_LINES}

    zh = mapa_tekstow.zloz(zh_paths)
    store = magazyn_mod.Magazyn()
    matched_ui: dict[str, int] = {}
    matched_prolog: dict[str, int] = {}

    target_files = [Path(p) for p in cel_paths] + [Path(p) for _, p in mapa_pairs]
    for path in target_files:
        teksty, _removed = mapa_tekstow.wczytaj_warstwe(path)
        for ident, current in teksty.items():
            zh_raw = zh.get(ident)
            if use_ui and current in TEST_LABELS:
                source = zh_raw if zh_raw is not None else current
                store.ustaw(mapa_tekstow.klucz(source), TEST_LABELS[current])
                matched_ui[current] = matched_ui.get(current, 0) + 1
            if use_prolog and zh_raw is not None:
                prolog_pl = prolog_by_pair.get((current, zh_raw.strip()))
                if prolog_pl:
                    store.ustaw(mapa_tekstow.klucz(zh_raw), prolog_pl)
                    matched_prolog[current] = matched_prolog.get(current, 0) + 1

    if not len(store):
        raise ValueError(f"nie znaleziono żadnej z testowych etykiet dla zakresu {zakres!r} w podanych plikach mapy")

    matched_labels = dict(matched_ui)
    for label, count in matched_prolog.items():
        matched_labels[label] = matched_labels.get(label, 0) + count

    with tempfile.TemporaryDirectory(prefix="wwm-test-latka-") as tmp:
        tmp_dir = Path(tmp)
        mag_dir = tmp_dir / "magazyn"
        latka_dir = tmp_dir / "latka"
        magazyn_mod.zapisz(mag_dir, store)

        argv = [
            "--indeks", str(indeks_dir),
            "--magazyn", str(mag_dir),
            "--wyj", str(latka_dir),
            "--poziom", str(poziom),
            "--zh", *[str(p) for p in zh_paths],
        ]
        for path in cel_paths:
            argv.extend(["--cel", str(path)])
        for game_rel, path in mapa_pairs:
            argv.extend(["--mapa", game_rel, str(path)])
        if build_gry:
            argv.extend(["--build-gry", build_gry])

        rc = zbuduj_latke.main(argv)
        if rc != 0:
            raise RuntimeError("zbuduj_latke.py zakończyło się błędem")

        latka_manifest = json.loads((latka_dir / "latka.json").read_text(encoding="utf-8"))
        out_zip = Path(wyj_zip)
        digest, size, zip_members = build_installer_kit.build_zip(out_zip, latka_dir=latka_dir)

    return {
        "ok": True,
        "zakres": zakres,
        "zip": str(out_zip),
        "bajtow": size,
        "sha256": digest,
        "plikow_w_zip": len(zip_members),
        "dopasowane_etykiety": dict(sorted(matched_labels.items())),
        "dopasowane_ui": dict(sorted(matched_ui.items())),
        "dopasowane_prolog": dict(sorted(matched_prolog.items())),
        "slotow_testowych": len(store),
        "pliki_gry": latka_manifest["pliki"],
        "build_gry": latka_manifest.get("build_gry", ""),
    }


def main(argv: list[str] | None = None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description="Zbuduj małą łatkę testową UI i/lub prologu dla polskich znaków z instalatorem Windows.")
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--zh", nargs="+", required=True, help="mapa zh_cn i jej warstwy _diff")
    parser.add_argument("--cel", action="append", default=[], help="plik mapy docelowej")
    parser.add_argument("--mapa", nargs=2, action="append", default=[], metavar=("SCIEZKA_W_GRZE", "PLIK"))
    parser.add_argument("--build-gry", default="")
    parser.add_argument("--zakres", choices=ZAKRESY, default="ui+prolog", help="co podmienić: ui, prolog, czy ui+prolog (domyślnie)")
    parser.add_argument("--wyj-zip", required=True, help="ścieżka wynikowego archiwum ZIP do przetestowania w Windows")
    parser.add_argument("--poziom", type=int, default=9)
    args = parser.parse_args(argv)

    try:
        report = zbuduj_paczke_testowa(
            indeks_dir=args.indeks,
            zh_paths=args.zh,
            cel_paths=args.cel,
            mapa_pairs=[(g, p) for g, p in args.mapa],
            wyj_zip=args.wyj_zip,
            build_gry=args.build_gry,
            poziom=args.poziom,
            zakres=args.zakres,
        )
    except (OSError, ValueError, RuntimeError, mapa_tekstow.MapaError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
