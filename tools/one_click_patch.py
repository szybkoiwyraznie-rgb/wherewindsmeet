#!/usr/bin/env python3
"""Jedno polecenie: częściowa lub pełna zwrotka tłumacza -> one-clickowy ZIP łatki Windows.

    python3 tools/one_click_patch.py \
        --zwrotka zwrotka.zip [plik1.md plik2.md ...] \
        --dane-gry WWM_DANE_20261111_...zip \
        --wyj-zip dist/WWM_LATKA_PL.zip

Lub przy jawnych plikach map:

    python3 tools/one_click_patch.py \
        --zwrotka zwrotka_czesc1.md zwrotka_czesc2.md \
        --zh translate_words_map_zh_cn translate_words_map_zh_cn_diff \
        --mapa Package/HD/oversea/locale/translate_words_map_en pkg_en \
        --mapa Package/HD/oversea/locale/translate_words_map_en_diff pkg_en_diff \
        --mapa LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff patch_en_diff \
        --build-gry 25906190 \
        --wyj-zip dist/WWM_LATKA_PL.zip

Co robi w jednym przebiegu:
1. wczytuje istniejący magazyn `--magazyn` (o ile istnieje i nie podano `--tylko-zwrotka`),
2. waliduje i dokłada wpisy ze zwrotki (`--zwrotka`: pliki `.md`, katalogi albo `.zip`) —
   puste `PL:` pomija bez błędu, więc działa na dowolnym wycinku tłumaczenia,
3. wykrywa mapy tekstów i `build_gry` z paczki kolektora (`--dane-gry`: katalog lub
   `WWM_DANE_*.zip` / `WWM_AKTUALIZACJA_*.zip`) albo korzysta z jawnych `--zh`/`--mapa`/`--cel`,
4. przepisuje binarne mapy gry z obsługą wariantów płci oraz kolizji fabularnych
   (`index/kolizje.jsonl`) i weryfikuje każdy zmieniony wpis,
5. pakuje wynik razem z `instalator/` (`ZAINSTALUJ.bat`, `PRZYWROC.bat`, `SPRAWDZ_STAN.bat`)
   do jednego gotowego archiwum `WWM_LATKA_PL.zip` dla Windows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
import zipfile

try:
    from tools import build_installer_kit
    from tools import import_zwrotki
    from tools import indeks as indeks_mod
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
    from tools import zbuduj_latke
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import build_installer_kit
    from tools import import_zwrotki
    from tools import indeks as indeks_mod
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
    from tools import zbuduj_latke


class OneClickError(Exception):
    """Nie udało się przygotować one-clickowej paczki łatki."""


def _priorytet_warstwy_zh(rel_or_name: str) -> tuple[int, str]:
    low = rel_or_name.replace("\\", "/").lower()
    is_diff = "_diff" in Path(low).name
    if not is_diff:
        return (0, low)
    if "localdata/patch/" in low:
        return (2, low)
    if "package/" in low:
        return (1, low)
    return (1, low)


def _rozpakuj_dane_zip(zip_path: Path, cel_dir: Path) -> Path:
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as error:
        raise OneClickError(f"{zip_path}: to nie jest poprawny plik ZIP") from error
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/") or ":" in name or "\x00" in name:
                raise OneClickError(f"{zip_path}: niebezpieczna ścieżka w archiwum: {info.filename!r}")
            low = name.lower()
            base = Path(low).name
            if base == "raport.json" or "translate_words_map_" in base:
                dest = cel_dir / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(info))
    return cel_dir


def _wykryj_z_raportu(raport_path: Path, jezyk_celu: str) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]], str]:
    try:
        data = json.loads(raport_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise OneClickError(f"{raport_path}: nieczytelny RAPORT.json: {error}") from error
    root = raport_path.parent
    zh_pairs: list[tuple[str, Path]] = []
    target_pairs: list[tuple[str, Path]] = []
    target_base = f"translate_words_map_{jezyk_celu.lower()}"
    target_diff = f"translate_words_map_{jezyk_celu.lower()}_diff"

    for row in data.get("files", ()):
        if row.get("status") not in ("copied", "duplicate"):
            continue
        source = str(row.get("source") or "").replace("\\", "/")
        stored_as = str(row.get("stored_as") or "").replace("\\", "/")
        if not source or not stored_as:
            continue
        file_path = root / stored_as
        if not file_path.is_file():
            continue
        name = Path(source).name.lower()
        norm_rel = zbuduj_latke.normalizuj_sciezke_gry(source)
        if name in ("translate_words_map_zh_cn", "translate_words_map_zh_cn_diff"):
            zh_pairs.append((norm_rel, file_path))
        elif name in (target_base, target_diff):
            target_pairs.append((norm_rel, file_path))

    build_id = str(data.get("steam_build_id") or "").strip()
    if not re.fullmatch(r"\d+", build_id):
        build_id = ""
    return zh_pairs, target_pairs, build_id


def _wykryj_z_katalogu(katalog: Path, jezyk_celu: str) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]], str]:
    raport = katalog / "RAPORT.json"
    if not raport.is_file():
        raport = next(sorted(katalog.rglob("RAPORT.json")), None)
    if raport is not None and raport.is_file():
        return _wykryj_z_raportu(raport, jezyk_celu)

    zh_pairs: list[tuple[str, Path]] = []
    target_candidates: list[tuple[str | None, Path]] = []
    target_base = f"translate_words_map_{jezyk_celu.lower()}"
    target_diff = f"translate_words_map_{jezyk_celu.lower()}_diff"
    zh_re = re.compile(r"^(?:\d+_)?translate_words_map_zh_cn(_diff)?$", re.I)
    tgt_re = re.compile(rf"^(?:\d+_)?translate_words_map_{re.escape(jezyk_celu)}(_diff)?$", re.I)

    for file_path in sorted(katalog.rglob("*")):
        if not file_path.is_file():
            continue
        name = file_path.name
        if zh_re.fullmatch(name):
            rel = zbuduj_latke.wywnioskuj_sciezke_gry(file_path) or file_path.relative_to(katalog).as_posix()
            zh_pairs.append((rel, file_path))
        elif tgt_re.fullmatch(name):
            rel = zbuduj_latke.wywnioskuj_sciezke_gry(file_path)
            target_candidates.append((rel, file_path))

    target_pairs: list[tuple[str, Path]] = []
    unresolved_base: list[Path] = []
    unresolved_diff: list[Path] = []
    for rel, file_path in target_candidates:
        if rel is not None:
            target_pairs.append((rel, file_path))
        elif file_path.name.lower().endswith(target_diff):
            unresolved_diff.append(file_path)
        elif file_path.name.lower().endswith(target_base):
            unresolved_base.append(file_path)

    if len(unresolved_base) == 1:
        target_pairs.append((f"Package/HD/oversea/locale/{target_base}", unresolved_base[0]))
    elif len(unresolved_base) > 1:
        raise OneClickError(
            "w katalogu danych znaleziono kilka bazowych map języka docelowego bez ścieżki Package/ — "
            "wskaż paczkę WWM_DANE_*.zip z RAPORT.json albo użyj --mapa"
        )
    if len(unresolved_diff) == 1:
        target_pairs.append((f"Package/HD/oversea/locale/{target_diff}", unresolved_diff[0]))
    elif len(unresolved_diff) > 1:
        raise OneClickError(
            "w katalogu danych jest wiele warstw _diff bez RAPORT.json i bez ścieżek Package/ / LocalData/Patch/ — "
            "wskaż oryginalny ZIP z zbieracza (WWM_DANE_*.zip) albo podaj pary przez --mapa"
        )

    return zh_pairs, target_pairs, ""


def odkryj_mapy(
    dane_gry: list[str | Path],
    tmp_dir: Path,
    *,
    jezyk_celu: str = "en",
) -> tuple[list[Path], list[tuple[str, Path]], str]:
    """Rozpoznaj warstwy `zh_cn`, mapy celu z zachowaniem ścieżek gry i opcjonalny `build_id`."""
    zh_by_rel: dict[str, tuple[str, Path]] = {}
    by_game_rel: dict[str, tuple[str, Path]] = {}
    detected_build = ""

    for idx, raw in enumerate(dane_gry):
        path = Path(raw)
        if not path.exists():
            raise OneClickError(f"nie znaleziono ścieżki --dane-gry: {raw}")
        if path.is_file():
            if path.suffix.lower() != ".zip":
                raise OneClickError(f"plik --dane-gry musi być katalogiem albo archiwum .zip: {raw}")
            extracted = _rozpakuj_dane_zip(path, tmp_dir / f"dane_{idx}")
            z_part, pairs_part, build_part = _wykryj_z_katalogu(extracted, jezyk_celu)
        else:
            z_part, pairs_part, build_part = _wykryj_z_katalogu(path, jezyk_celu)
        for zh_rel, zh_path in z_part:
            zh_by_rel[zh_rel.casefold()] = (zh_rel, zh_path)
        for game_rel, file_path in pairs_part:
            by_game_rel[game_rel.casefold()] = (game_rel, file_path)
        if build_part:
            detected_build = build_part

    zh_sorted = sorted(zh_by_rel.values(), key=lambda item: _priorytet_warstwy_zh(item[0]))
    dedup_zh = [path for _, path in zh_sorted]
    pairs = [by_game_rel[k] for k in sorted(by_game_rel)]
    return dedup_zh, pairs, detected_build


def zbuduj_ze_zwrotki(
    *,
    indeks_dir: str | Path = "index",
    zwrotki: list[str | Path] = (),
    magazyn_dir: str | Path | None = "tlumaczenie",
    tylko_zwrotka: bool = False,
    zapisz_magazyn: bool = False,
    dane_gry: list[str | Path] = (),
    zh_paths: list[str | Path] = (),
    mapa_pairs: list[tuple[str, str | Path]] = (),
    cel_paths: list[str | Path] = (),
    wyj_zip: str | Path = "dist/WWM_LATKA_PL.zip",
    build_gry: str = "",
    jezyk_celu: str = "en",
    poziom: int = 9,
    pomin_bledne: bool = False,
    mimo_tokenow: bool = False,
    tylko_magazyn: bool = False,
) -> tuple[dict, int]:
    """Import zwrotek -> budowa map -> gotowy one-click ZIP Windows. Zwraca (raport, exit_code)."""
    if not zwrotki and not tylko_magazyn:
        raise OneClickError("podaj co najmniej jedną ścieżkę --zwrotka (albo użyj --tylko-magazyn)")

    ix = indeks_mod.wczytaj(indeks_dir, sceny=False)
    if tylko_zwrotka or magazyn_dir is None or not Path(magazyn_dir).exists():
        magazyn = magazyn_mod.Magazyn()
    else:
        magazyn = magazyn_mod.wczytaj(magazyn_dir)
    przekladow_przed = len(magazyn)

    import_raport: dict | None = None
    if zwrotki:
        import_raport = import_zwrotki.importuj(
            ix,
            import_zwrotki.pliki_zwrotki(zwrotki),
            magazyn,
            mimo_tokenow=mimo_tokenow,
        )
        if import_raport["odrzucone"] and not pomin_bledne:
            return {
                "ok": False,
                "etap": "import",
                "powod": (
                    f"zwrotka zawiera {import_raport['odrzucone']} odrzuconych wpisów "
                    "(popraw je albo uruchom z --pomin-bledne, żeby zbudować łatkę tylko z poprawnych)"
                ),
                "import": import_raport,
            }, 2

    if not len(magazyn):
        raise OneClickError("po imporcie magazyn przekładów jest pusty — zwrotka nie zawiera żadnego wypełnionego `PL:`")

    if zapisz_magazyn:
        if magazyn_dir is None:
            raise OneClickError("nie podano ścieżki --magazyn do zapisu")
        magazyn_mod.zapisz(magazyn_dir, magazyn)

    with tempfile.TemporaryDirectory(prefix="wwm-one-click-") as tmp:
        tmp_dir = Path(tmp)
        auto_zh, auto_pairs, auto_build = (
            odkryj_mapy(list(dane_gry), tmp_dir / "dane", jezyk_celu=jezyk_celu)
            if dane_gry
            else ([], [], "")
        )
        final_zh = [Path(p) for p in zh_paths] if zh_paths else auto_zh
        if not final_zh:
            raise OneClickError("brak mapy źródłowej zh_cn — wskaż --dane-gry albo --zh")

        merged_pairs: dict[str, tuple[str, Path]] = {
            rel.casefold(): (rel, p) for rel, p in auto_pairs
        }
        for rel, raw_path in mapa_pairs:
            norm = zbuduj_latke.normalizuj_sciezke_gry(rel)
            merged_pairs[norm.casefold()] = (norm, Path(raw_path))
        final_pairs = [merged_pairs[k] for k in sorted(merged_pairs)]
        final_cel = [Path(p) for p in cel_paths]
        if not final_pairs and not final_cel:
            raise OneClickError("brak docelowych map języka gry — wskaż --dane-gry, --mapa albo --cel")

        resolved_build = build_gry.strip() or auto_build
        latka_dir = tmp_dir / "latka"
        argv = [
            "--indeks", str(indeks_dir),
            "--magazyn", str(tmp_dir / "magazyn"),
            "--wyj", str(latka_dir),
            "--poziom", str(poziom),
            "--zh", *[str(p) for p in final_zh],
        ]
        magazyn_mod.zapisz(tmp_dir / "magazyn", magazyn)
        for p in final_cel:
            argv.extend(["--cel", str(p)])
        for game_rel, p in final_pairs:
            argv.extend(["--mapa", game_rel, str(p)])
        if resolved_build:
            argv.extend(["--build-gry", resolved_build])

        rc = zbuduj_latke.main(argv)
        if rc != 0:
            raise OneClickError("budowa binarnych map łatki (zbuduj_latke) nie powiodła się")

        latka_manifest = json.loads((latka_dir / "latka.json").read_text(encoding="utf-8"))
        out_zip = Path(wyj_zip)
        digest, size, members = build_installer_kit.build_zip(out_zip, latka_dir=latka_dir)

    report = {
        "ok": True,
        "format": "wwm-one-click-v1",
        "zip": str(out_zip),
        "bajtow": size,
        "sha256": digest,
        "plikow_w_zip": len(members),
        "build_gry": latka_manifest.get("build_gry", ""),
        "magazyn_zapisany": bool(zapisz_magazyn),
        "przekladow_przed": przekladow_przed,
        "przekladow_po": len(magazyn),
        "import": (
            {
                "plikow": import_raport["plikow"],
                "liczby": import_raport["liczby"],
                "odrzucone": import_raport["odrzucone"],
                "problemy_wg_rodzaju": import_raport["problemy_wg_rodzaju"],
                "problemy": import_raport["problemy"],
            }
            if import_raport is not None
            else None
        ),
        "pliki_gry": latka_manifest["pliki"],
    }
    return report, 0


def main(argv: list[str] | None = None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zwrotka", nargs="+", default=[], help="pliki .md, katalogi albo .zip ze zwrotką tłumacza")
    parser.add_argument("--tylko-magazyn", action="store_true", help="zbuduj ZIP łatki wyłącznie z --magazyn bez nowej zwrotki")
    parser.add_argument("--indeks", default="index", help="katalog wyciągu index/")
    parser.add_argument("--magazyn", default="tlumaczenie", help="katalog magazynu przekładów (używany jako baza, jeśli istnieje)")
    parser.add_argument("--tylko-zwrotka", action="store_true", help="nie wczytuj bazowego --magazyn; użyj wyłącznie wpisów z --zwrotka")
    parser.add_argument("--zapisz-magazyn", action="store_true", help="zapisz przyjęte wpisy z --zwrotka do katalogu --magazyn")
    parser.add_argument("--dane-gry", nargs="+", default=[], help="katalog z mapami albo archiwa WWM_DANE_*.zip / WWM_AKTUALIZACJA_*.zip")
    parser.add_argument("--jezyk-celu", default="en", help="kod języka mapy celu z --dane-gry (domyślnie: en)")
    parser.add_argument("--zh", nargs="+", default=[], help="jawne pliki mapy zh_cn i jej warstw _diff")
    parser.add_argument("--mapa", nargs=2, action="append", default=[], metavar=("SCIEZKA_W_GRZE", "PLIK"))
    parser.add_argument("--cel", action="append", default=[], help="jawny plik mapy celu")
    parser.add_argument("--build-gry", default="", help="opcjonalny buildid Steam (domyślnie z RAPORT.json w --dane-gry)")
    parser.add_argument("--wyj-zip", default="dist/WWM_LATKA_PL.zip", help="ścieżka wynikowego ZIP-a instalatora Windows")
    parser.add_argument("--raport", help="opcjonalny plik JSON z pełnym raportem")
    parser.add_argument("--poziom", type=int, default=9, help="poziom kompresji zstd (domyślnie: 9)")
    parser.add_argument("--pomin-bledne", action="store_true", help="zbuduj łatkę z poprawnych wpisów mimo odrzuconych wierszy")
    parser.add_argument("--mimo-tokenow", action="store_true", help="przyjmij także wpisy z niezgodnymi tokenami gry")
    args = parser.parse_args(argv)

    try:
        report, code = zbuduj_ze_zwrotki(
            indeks_dir=args.indeks,
            zwrotki=args.zwrotka,
            magazyn_dir=args.magazyn,
            tylko_zwrotka=args.tylko_zwrotka,
            zapisz_magazyn=args.zapisz_magazyn,
            dane_gry=args.dane_gry,
            zh_paths=args.zh,
            mapa_pairs=[(g, p) for g, p in args.mapa],
            cel_paths=args.cel,
            wyj_zip=args.wyj_zip,
            build_gry=args.build_gry,
            jezyk_celu=args.jezyk_celu,
            poziom=args.poziom,
            pomin_bledne=args.pomin_bledne,
            mimo_tokenow=args.mimo_tokenow,
            tylko_magazyn=args.tylko_magazyn,
        )
    except (
        OneClickError,
        import_zwrotki.ZwrotkaError,
        indeks_mod.IndeksError,
        magazyn_mod.MagazynError,
        mapa_tekstow.MapaError,
        zbuduj_latke.LatkaError,
        OSError,
        ValueError,
    ) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False, indent=1))
        return 1

    if args.raport:
        Path(args.raport).parent.mkdir(parents=True, exist_ok=True)
        Path(args.raport).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps(report, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
