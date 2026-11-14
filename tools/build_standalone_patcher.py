#!/usr/bin/env python3
"""Buduje samowystarczalną paczkę łatki `WWM_LATKA_PL.zip` bez żadnych binarek gry.

Eksportuje z `index/` i magazynu tłumaczeń (`tlumaczenie/` lub zwrotki) czysty
plan tekstowy `plan_latki.json` (`wwm-plan-latki-v1`) i pakuje go razem z
lokalnym patcherem Pythona (`patcher_wwm.py`) oraz skryptami Windows
(`ZAINSTALUJ.bat`, `PRZYWROC.bat`, `SPRAWDZ_STAN.bat`, `CZYTAJ_TO.txt`).

Nie pobiera ani nie modyfikuje plików binarnych gry z Dysku Google: patcher
przepisuje mapy lokalnie u gracza na podstawie jego plików na dysku.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

try:
    from tools import indeks as indeks_mod
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
    from tools import zbuduj_latke
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import indeks as indeks_mod
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
    from tools import zbuduj_latke


ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
PLAN_FORMAT = "wwm-plan-latki-v1"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
REQUIREMENTS_TXT = "zstandard>=0.23.0\n"
PACKAGED_TOOLS = (
    "apply_translation.py",
    "locale_container.py",
    "locale_records.py",
    "mapa_tekstow.py",
)

README_BODY_PL = """JAK ZAINSTALOWAĆ

1. Zamknij grę i poczekaj, aż Steam zakończy aktualizacje.
2. Rozpakuj CAŁE archiwum ZIP do jednego nowego folderu poza grą (np. na Pulpicie).
3. Kliknij dwa razy ZAINSTALUJ.bat.
   - Potrzebny jest Python 3.10 lub nowszy (https://www.python.org/downloads/ —
     podczas instalacji zaznacz "Add python.exe to PATH").
   - Przy pierwszym uruchomieniu skrypt automatycznie utworzy lokalne środowisko
     w folderze narzedzia\\.venv i pobierze małą bibliotekę zstandard (ok. 0.5 MB).
   - Patcher znajdzie instalację Steam gry (możesz też przeciągnąć folder gry
     na plik .bat), zapisze zweryfikowaną kopię zapasową oryginałów poza grą,
     przepisze mapy lokalnie na Twoim komputerze i sprawdzi SHA-256 każdego pliku.

SPRAWDZANIE STANU I PRZYWRACANIE

- SPRAWDZ_STAN.bat — tylko odczyt: sprawdza, czy w grze są oryginały czy spolszczenie
  oraz czy kopia zapasowa jest kompletna.
- PRZYWROC.bat — przywraca oryginalne pliki gry z zapisanej kopii zapasowej
  (z weryfikacją SHA-256). Jeśli aktualizacja gry nadpisała w międzyczasie część
  plików nową wersją, PRZYWROC.bat bezpiecznie je pomija (zostawiając nowsze pliki
  z gry) i cofa tylko pozostałe pliki, w których nadal jest spolszczenie.

AKTUALIZACJE GRY

Ponieważ paczka zawiera czysty plan tłumaczeń (plan_latki.json) i działa na
Twoich plikach gry na dysku, po drobnych poprawkach/patchach gry nie trzeba
pobierać ciężkich plików binarnych — wystarczy ponownie kliknąć ZAINSTALUJ.bat
(wykryje zaktualizowane pliki, zachowa ich nowe oryginały i nałoży przekład).
"""


def _build_readme_text(plan: dict) -> str:
    wydanie = str(plan.get("wydanie") or "").strip()
    tytul = (
        f"Where Winds Meet — Spolszczenie PL (wydanie {wydanie})"
        if wydanie
        else "Where Winds Meet — Spolszczenie PL"
    )
    opis = str(plan.get("opis") or "").strip()
    przekladow = len(plan.get("po_kluczu", {})) + len(plan.get("po_id", {}))
    lines = [tytul]
    if opis or przekladow:
        szczegoly = []
        if przekladow:
            szczegoly.append(f"wpisów w planie: {przekladow:,}".replace(",", " "))
        if opis:
            szczegoly.append(f"dane gry: {opis}")
        lines.append(" · ".join(szczegoly))
    lines.append("")
    lines.append(README_BODY_PL)
    return "\n".join(lines)


def _windows_lines(text: str) -> bytes:
    norm = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    return norm.encode("utf-8")


def _make_bat(akcja: str, title: str, done_msg: str, *, need_zstd: bool) -> bytes:
    zstd_import = ", zstandard" if need_zstd else ""
    check_venv = '".venv\\Scripts\\python.exe" -c "import zstandard" >nul 2>&1' if need_zstd else '".venv\\Scripts\\python.exe" -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1'
    sys_venv_block = (
        """if defined WWM_USE_CURRENT_PYTHON goto use_env_py
if exist ".venv\\Scripts\\python.exe" goto check_venv
goto check_sys_py3
:use_env_py
set "PYEXE=python"
goto run
:check_venv
"""
        + check_venv
        + """
if errorlevel 1 goto check_sys_py3
set "PYEXE=.venv\\Scripts\\python.exe"
goto run
:check_sys_py3
py -3 -c "import sys"""
        + zstd_import
        + """; assert sys.version_info >= (3,10)" >nul 2>&1
if errorlevel 1 goto check_sys_py
set "PYEXE=py -3"
goto run
:check_sys_py
python -c "import sys"""
        + zstd_import
        + """; assert sys.version_info >= (3,10)" >nul 2>&1
if errorlevel 1 goto need_venv
set "PYEXE=python"
goto run"""
    )
    need_venv_block = (
        """:need_venv
set "HOSTPY="
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 set "HOSTPY=py -3"
if not defined HOSTPY python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1 && set "HOSTPY=python"
if not defined HOSTPY goto no_python"""
        + (
            """
echo Przygotowuje osobne srodowisko Python w folderze narzedzia\\.venv ...
%HOSTPY% -m venv ".venv"
if errorlevel 1 goto setup_fail
echo Pierwsze uruchomienie: pobieram biblioteke zstandard ^(ok. 0.5 MB^). Potrzebny internet.
".venv\\Scripts\\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto setup_fail
set "PYEXE=.venv\\Scripts\\python.exe\""""
            if need_zstd
            else """
set "PYEXE=%HOSTPY%\""""
        )
    )
    script = f"""@echo off
setlocal
cd /d "%~dp0narzedzia" || goto no_tools
chcp 65001 >nul
set "PYTHONUTF8=1"
title {title}
echo ===============================================
echo {title}
echo ===============================================
echo.
set "PYEXE="
{sys_venv_block}
{need_venv_block}
:run
%PYEXE% patcher_wwm.py --akcja {akcja} --plan "plan_latki.json" %*
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" goto done
echo BLAD. Przeczytaj komunikat powyzej. Zadna czesciowa zmiana nie zostala pozostawiona.
goto finish
:done
echo {done_msg}
goto finish
:no_python
set "RESULT=1"
echo BLAD: potrzebny Python 3.10 lub nowszy z https://www.python.org/downloads/
echo Podczas instalacji zaznacz "Add python.exe to PATH".
goto finish
:setup_fail
set "RESULT=1"
echo BLAD podczas przygotowania srodowiska Python lub pobierania zstandard.
goto finish
:no_tools
set "RESULT=1"
echo BLAD: brak katalogu narzedzia\\ obok tego pliku. Rozpakuj caly ZIP do jednego folderu.
:finish
echo.
pause
exit /b %RESULT%
"""
    script.encode("ascii")
    return _windows_lines(script)


def zbuduj_plan(
    ix: indeks_mod.Indeks,
    magazyn: magazyn_mod.Magazyn,
    *,
    jezyk_celu: str = "en",
    build_gry: str = "",
    wydanie: str = "",
) -> dict:
    """Zbuduj czysty plan łatki `wwm-plan-latki-v1` wyłącznie z `index/` i magazynu."""
    if not len(magazyn):
        raise ValueError("magazyn przekładów jest pusty — nie ma czego eksportować do planu łatki")

    # 1. Warianty płci (po_id) + dziedziczenie po rodzeństwie, bez plików gry.
    po_id: dict[str, str] = {}
    siblings = zbuduj_latke.rodzenstwo_wariantow(ix.warianty)
    for ident_hex, row in sorted(ix.warianty.items()):
        text = magazyn.po_id.get(ident_hex)
        if text is None:
            for sib in siblings.get(row["k"], ()):
                if sib in magazyn.po_id:
                    text = magazyn.po_id[sib]
                    break
        if text:
            po_id[ident_hex] = text
    for ident_hex, text in sorted(magazyn.po_id.items()):
        if text:
            po_id[ident_hex] = text

    # 2. Przekłady po kluczu SHA-256 tekstu źródłowego.
    po_kluczu = {k: v for k, v in sorted(magazyn.po_kluczu.items()) if v}

    # 3. Kolizje znaczeniowe tylko dla tekstów `zh`, które faktycznie mają choć jeden przekład.
    kolizje: dict[str, list[list[str]]] = {}
    for zh_text, variants in sorted(ix.kolizje.items()):
        if any(var_key in po_kluczu for var_key, _rep_en in variants):
            kolizje[zh_text] = variants

    # 4. Bezpieczny fallback po jednoznacznym `EN` (np. gdyby nowy patch dodał wpis tylko w EN bez ZH).
    en_to_keys: dict[str, set[str]] = defaultdict(set)
    for k, row in ix.teksty.items():
        if row.en:
            en_to_keys[row.en].add(k)

    en_jednoznaczne: dict[str, str] = {}
    for en_text, keys in sorted(en_to_keys.items()):
        translated_vals = {po_kluczu[k] for k in keys if k in po_kluczu}
        if len(translated_vals) == 1 and len(translated_vals) > 0:
            # Jeśli wszystkie klucze dające ten napis EN nie są przetłumaczone, ale ten jeden ma przekład
            # i tekst ma dokładnie 1 klucz w indeksie albo wszystkie warianty mają dokładnie to samo tłumaczenie:
            if len(keys) == 1 or len(translated_vals) == 1 and all((k in po_kluczu or not ix.teksty[k].zrodlo) for k in keys):
                en_jednoznaczne[mapa_tekstow.klucz(en_text)] = next(iter(translated_vals))

    opis = str(ix.manifest.get("wejscia", {}).get("opis") or "").strip()
    plan = {
        "format": PLAN_FORMAT,
        "wydanie": wydanie.strip(),
        "jezyk_celu": jezyk_celu.lower(),
        "opis": opis,
        "oczekiwany_build": build_gry.strip(),
        "po_id": po_id,
        "po_kluczu": po_kluczu,
        "kolizje": kolizje,
        "en_jednoznaczne": en_jednoznaczne,
    }
    return plan


def build_standalone_zip(output: Path, plan: dict) -> tuple[str, int, dict[str, bytes]]:
    """Zapisz deterministyczny standalone ZIP instalacyjny (zero binarek gry) i zweryfikuj go."""
    if plan.get("format") != PLAN_FORMAT:
        raise ValueError(f"niepoprawny format planu: {plan.get('format')!r}")

    wydanie_ascii = str(plan.get("wydanie") or "").encode("ascii", "ignore").decode("ascii").strip()
    suffix = f" {wydanie_ascii}" if wydanie_ascii else ""

    files: dict[str, bytes] = {
        "CZYTAJ_TO.txt": b"\xef\xbb\xbf" + _windows_lines(_build_readme_text(plan)),
        "ZAINSTALUJ.bat": _make_bat(
            "instaluj",
            f"WHERE WINDS MEET - SPOLSZCZENIE PL{suffix} - INSTALACJA",
            "GOTOWE. Spolszczenie zainstalowane lokalnie z Twoich plikow gry, kopia oryginalow zapisana.",
            need_zstd=True,
        ),
        "PRZYWROC.bat": _make_bat(
            "przywroc",
            f"WHERE WINDS MEET - SPOLSZCZENIE PL{suffix} - PRZYWRACANIE",
            "GOTOWE. Przywrocono oryginalne pliki gry z kopii zapasowej.",
            need_zstd=False,
        ),
        "SPRAWDZ_STAN.bat": _make_bat(
            "stan",
            f"WHERE WINDS MEET - SPOLSZCZENIE PL{suffix} - SPRAWDZENIE STANU",
            "GOTOWE. Sprawdzenie zakonczone (bez zmian w grze).",
            need_zstd=False,
        ),
        "narzedzia/requirements.txt": REQUIREMENTS_TXT.encode("ascii"),
        "narzedzia/plan_latki.json": (json.dumps(plan, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"),
        "narzedzia/patcher_wwm.py": (TOOLS_DIR / "patcher_wwm.py").read_bytes(),
        "narzedzia/tools/__init__.py": b"",
    }
    for mod_name in PACKAGED_TOOLS:
        files[f"narzedzia/tools/{mod_name}"] = (TOOLS_DIR / mod_name).read_bytes()

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = ZipInfo(filename=name, date_time=FIXED_ZIP_TIME)
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[name])

    with ZipFile(output) as check:
        if check.testzip() is not None or set(check.namelist()) != set(files):
            raise RuntimeError("wygenerowane archiwum standalone nie przeszło weryfikacji")
        for name, expected in files.items():
            if check.read(name) != expected:
                raise RuntimeError(f"niezgodność zawartości w archiwum dla {name}")

    raw = output.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw), files


def main(argv: list[str] | None = None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--indeks", default="index", help="katalog wyciągu index/")
    parser.add_argument("--magazyn", default="tlumaczenie", help="katalog magazynu przekładów")
    parser.add_argument("--jezyk-celu", default="en", help="kod języka mapy celu w grze (domyślnie: en)")
    parser.add_argument("--build-gry", default="", help="opcjonalny wymuszany buildid Steam")
    parser.add_argument("--wydanie", default="", help="opcjonalny numer/etykieta wydania (np. v0.1.0)")
    parser.add_argument("--output", required=True, help="ścieżka wynikowego ZIP-a standalone")
    args = parser.parse_args(argv)

    ix = indeks_mod.wczytaj(args.indeks, sceny=False)
    magazyn = magazyn_mod.wczytaj(args.magazyn)
    plan = zbuduj_plan(ix, magazyn, jezyk_celu=args.jezyk_celu, build_gry=args.build_gry, wydanie=args.wydanie)
    digest, size, files = build_standalone_zip(Path(args.output), plan)
    print(
        json.dumps(
            {
                "ok": True,
                "format": PLAN_FORMAT,
                "zip": str(args.output),
                "bajtow": size,
                "sha256": digest,
                "plikow_w_zip": len(files),
                "po_id": len(plan["po_id"]),
                "po_kluczu": len(plan["po_kluczu"]),
                "kolizje": len(plan["kolizje"]),
                "en_jednoznaczne": len(plan["en_jednoznaczne"]),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
