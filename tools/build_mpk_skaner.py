#!/usr/bin/env python3
"""Buduje samowystarczalny kit Windows `WWM_MPK_Skaner_v7.zip` (bez danych gry).

Od v4 kit: (a) wycina SUROWE bloki trafionych kandydatów i WSZYSTKIE bloki
z `LT1.mpkinfo` do `wyciete/`, (b) zrzuca `Patch.mpkdb` (schema + wszystkie
wiersze, kolumny BLOB jako hex) do `mpkdb_dump.json`. Od v6 wycina
nieskompresowane grafy JSON Storyline z `Resources*.mpk`. Od v7 dodatkowo:
(c) kandydaci to PRAWDZIWE ścieżki VFS z bazy gry
(`index/mpk/sciezki_vfs.jsonl`: pełne `cutscenes.cine_path`,
`fenbao_cutscene_info.resources`/`.cutscene_graph`, ścieżki `.etsb`/`.ets`/
`.graph` z chunków `dataN`), (d) SONDA EZST — czysto-Pythonowy AES-ECB
odszyfrowuje prefiksy bloków EZST, a początek ramki zstd (Python 3.14+ albo
pakiet `zstandard`, opcjonalnie) jest dekompresowany w pamięci i przeszukiwany
pod sygnatury `.cine`/Storyline/`.etsb`/benchmark `4700001`; trafienia są
wycinane SUROWO. Pełne dekodowanie nadal po naszej stronie. Żaden krok
wycinania nie blokuje powstania ZIPa.

Eksportuje ze `status/index/`:
  * `index/mpk/sciezki_vfs.jsonl` → wszystkie ścieżki z katalogiem
    (+ warianty `.ets` ↔ `.etsb`),
  * `index/poi.jsonl` → pole `storyline` — ścieżki klienta
    (np. `client/dialogs/hjt/sxd_lingwei.etsb`) i ich warianty,
  * `index/cutsceny_meta.jsonl` → `film` — stare wzorce `.cine` (zostają
    jako uzupełnienie; realne ścieżki idą z `sciezki_vfs.jsonl`).

Wynik: `kandydaci.jsonl` + `mpk_skaner.py` + `SKANUJ.bat` + `CZYTAJ_TO.txt`
spakowane deterministycznie do `dist/WWM_MPK_Skaner_v7.zip`.

Kit NIE zawiera żadnych plików gry; kandydacje to same ścieżki (teksty),
już obecne w publicznym repozytorium.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
WERSJA = "v7"
NAZWA_ZIP = f"WWM_MPK_Skaner_{WERSJA}.zip"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)

README_BODY_PL = """CO TO JEST

Skaner paczek Where Winds Meet. Sprawdza, gdzie w instalacji gry leżą
indeksy plików (`Resources.mpkinfo`, `LocalData/Patch/*.mpkinfo`,
`Patch.mpkdb`) i czy któryś z indeksów zna już pliki, których szukamy:
`.cine` (osie cutscen) oraz `.etsb` (skrypty klienta, np. dialog POI).

Skaner NIE zmienia NICZEGO w grze i paczek nie rozpakowuje. Oprócz sondy
wycina SUROWE małe bloki: trafione przez sondaż (teraz z PRAWDZIWYMI
ścieżkami .cine/.graph/.etsb z bazy gry, nie zgadywanymi), WSZYSTKIE bloki
z `LT1.mpkinfo` (skrypty klienta, ~2,5 MB), zrzuca `Patch.mpkdb` do JSON
(`mpkdb_dump.json`) i — NOWOŚĆ w v7 — sonduje ZAWARTOŚĆ małych bloków EZST:
odszyfrowuje w pamięci sam początek bloku i szuka w nim sygnatur osi cutscen
(.cine), grafów scen (Storyline) i skryptów dialogów. Trafione bloki wycina
w SUROWEJ postaci — pełne dekodowanie odbywa się po stronie repozytorium.

JAK URUCHOMIĆ

1. Zamknij grę.
2. Rozpakuj CAŁY ten ZIP do jednego nowego folderu poza grą (np. na Pulpicie).
3. Kliknij dwa razy SKANUJ.bat.
   - Potrzebny jest Python 3.10 lub nowszy (https://www.python.org/downloads/ —
     podczas instalacji zaznacz "Add python.exe to PATH").
   - Niczego więcej nie musisz instalować: jeśli Pythonowi brakuje modułu
     zstd (potrzebnego sondzie EZST), SKANUJ.bat doinstaluje go SAM
     (jednorazowe pobranie małego pakietu "zstandard"). Gdy to się nie uda
     (np. brak internetu), skan i tak ruszy — sonda sprawdzi wtedy tylko
     bloki nieskompresowane i uczciwie zapisze to w raporcie.
   - Otworzy się OKNO WYBORU folderu gry (ten z folderami Package i
     LocalData oraz plikami Resources*.mpk) — wskaż go kliknięciem.
     Ścieżki NIE trzeba wpisywać. Alternatywnie możesz przeciągnąć folder
     gry na SKANUJ.bat.
4. Poczekaj na komunikat GOTOWE. Sonda EZST czyta początki setek tysięcy
   małych bloków, więc całość może potrwać od kilkunastu minut do ponad
   godziny (dysk + procesor). Postęp wypisuje się na bieżąco po każdej
   paczce. Powstanie folder MPK_SKANER_WYNIK i plik WWM_MPK_Skaner_WYNIK.zip.

CO ODESŁAĆ

Wyślij na Dysk Google (folder "Where Winds Meet") WYŁĄCZNIE plik
WWM_MPK_Skaner_WYNIK.zip (zwykle kilka MB). NIE wysyłaj plików .mpk
ani .mpkinfo — są za duże i niepotrzebne.

CO SKANER ZAPISUJE (folder MPK_SKANER_WYNIK)

- RAPORT.json      pełny raport maszynowy (paczki, indeksy, trafienia)
- PODSUMOWANIE.txt  ten sam raport w skrócie po polsku
- wyciete/         surowe bloki: trafienia sondaży + wszystkie z LT1.mpkinfo
                   + trafienia sondy EZST (ezst_*.bin, ezst_trafienia.jsonl)
                   + nieskompresowane grafy scen (storyline_wyciete.jsonl)
- mpkdb_dump.json  schema i wszystkie wiersze tabeli Patch.mpkdb
- SHA256.txt       skrót wynikowego ZIP-a

CZEGO SKANER NIE ROBI

- nie uruchamia gry i nie dotyka jej procesu,
- nie modyfikuje żadnego pliku gry (otwiera je tylko do odczytu),
- nie wysyła żadnych danych do sieci (jedyny kontakt z siecią to ewentualne
  jednorazowe POBRANIE pakietu "zstandard" przez SKANUJ.bat, zanim skan
  ruszy — sam skaner niczego nie wysyła),
- nie zapisuje zdekodowanej treści bloków — sygnatur szuka w pamięci,
  a na dysk trafiają wyłącznie SUROWE bloki.
"""

BAT_TEMPLATE = """@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
title WWM MPK SKANER
echo ===============================================
echo WWM MPK SKANER - sondowanie paczek .mpk
echo ===============================================
echo.
set "PYEXE="
rem 1) py launcher (Python 3.10+)
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"
rem 2) python z PATH
if not defined PYEXE python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1 && set "PYEXE=python"
rem 3) brak Pythona 3.10+ - instrukcja
if not defined PYEXE goto no_python
rem Sonda EZST dziala w pelni tylko z modulem zstd - sprawdz i w razie
rem braku doinstaluj pakiet zstandard automatycznie (jedyne pobranie z sieci).
%PYEXE% "narzedzia\\mpk_skaner.py" --sprawdz-zstd >nul 2>&1
if not errorlevel 1 goto zstd_ok
echo Dolaczam modul zstd do sondy EZST (jednorazowo, pakiet zstandard)...
%PYEXE% -m pip install --user zstandard
%PYEXE% "narzedzia\\mpk_skaner.py" --sprawdz-zstd >nul 2>&1
if not errorlevel 1 goto zstd_ok
echo UWAGA: nie udalo sie dolaczyc modulu zstd. Skan ruszy mimo to,
echo ale sonda EZST sprawdzi tylko bloki nieskompresowane (bedzie to w raporcie).
:zstd_ok
echo.
if "%~1"=="" (
  rem bez argumentow - skaner otworzy okno wyboru folderu gry
  %PYEXE% "narzedzia\\mpk_skaner.py" --wyjscie "%~dp0MPK_SKANER_WYNIK"
) else (
  rem przeciagniety na ikone folder gry
  %PYEXE% "narzedzia\\mpk_skaner.py" --wyjscie "%~dp0MPK_SKANER_WYNIK" --gra "%~1"
)
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" goto done
echo BLAD. Przeczytaj komunikat powyzej. Gra nie zostala zmieniona.
goto finish
:done
echo GOTOWE. Wynik: WWM_MPK_Skaner_WYNIK.zip
goto finish
:no_python
set "RESULT=1"
echo BLAD: potrzebny Python 3.10 lub nowszy z https://www.python.org/downloads/
echo Podczas instalacji zaznacz "Add python.exe to PATH".
:finish
echo.
pause
exit /b %RESULT%
"""


def _windows_lines(text: str) -> bytes:
    norm = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    return norm.encode("utf-8")


def _swap_ets(path: str) -> str | None:
    for src, dst in ((".etsb", ".ets"), (".ets", ".etsb")):
        if path.endswith(src):
            return path[: -len(src)] + dst
    return None


def kandydaci(index_dir: Path) -> list[dict]:
    kandydaci: list[dict] = []
    widziane: set[str] = set()

    def dodaj(sciezka: str, pochodzenie: str) -> None:
        sciezka = sciezka.strip()
        if sciezka and sciezka not in widziane:
            widziane.add(sciezka)
            kandydaci.append({"sciezka": sciezka, "pochodzenie": pochodzenie})

    poi = index_dir / "poi.jsonl"
    if poi.is_file():
        with open(poi, encoding="utf-8") as fh:
            for line in fh:
                try:
                    wpis = json.loads(line)
                except json.JSONDecodeError:
                    continue
                story = str(wpis.get("storyline") or "").strip()
                if "/" not in story:
                    continue
                dodaj(story, "poi_storyline")
                wariant = _swap_ets(story)
                if wariant:
                    dodaj(wariant, "poi_storyline_wariant_ext")
                # Prefiksy VFS potwierdzone na naszej instalacji (LT1):
                # bloki Lua leżą pod `LuaText/<sciezka-ze-zrodla-debug>`,
                # np. `LuaText/patch/patch_context.lua` — 238/240+2/240 trafień file_id.
                # POI storyline bez prefiksu nie trafiał nigdzie (0/312), więc kandydaci
                # z prefiksami są absolutnie potrzebni.
                for prefix in ("LuaText/", "LuaText/hexm/", "LuaText/hexm/client/storyline_data/"):
                    dodaj(prefix + story, f"poi_storyline_prefiks:{prefix.rstrip('/')}")
                    if wariant:
                        dodaj(prefix + wariant, f"poi_storyline_prefiks_wariant_ext:{prefix.rstrip('/')}")

    # Od v7: PRAWDZIWE ścieżki VFS z bazy gry (tools/sciezki_vfs.py) —
    # pełne `cutscenes.cine_path` (974 .cine; wzorzec qhrw trafiał tylko 14),
    # `fenbao_cutscene_info.resources`/`.cutscene_graph` oraz ścieżki
    # .etsb/.ets/.graph znalezione w chunkach dataN. Hashowalne są tylko
    # wpisy z katalogiem w ścieżce.
    sciezki_vfs = index_dir / "mpk" / "sciezki_vfs.jsonl"
    if sciezki_vfs.is_file():
        with open(sciezki_vfs, encoding="utf-8") as fh:
            for line in fh:
                try:
                    wpis = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sciezka = str(wpis.get("sciezka") or "").strip()
                if "/" not in sciezka:
                    continue
                ext = str(wpis.get("ext") or "")
                dodaj(sciezka, f"vfs_{ext}")
                wariant = _swap_ets(sciezka)
                if wariant:
                    dodaj(wariant, f"vfs_{ext}_wariant_ext")

    meta = index_dir / "cutsceny_meta.jsonl"
    filmy: set[str] = set()
    if meta.is_file():
        with open(meta, encoding="utf-8") as fh:
            for line in fh:
                try:
                    wpis = json.loads(line)
                except json.JSONDecodeError:
                    continue
                film = str(wpis.get("film") or "").strip()
                if film:
                    filmy.add(film)
    wzorce = (
        "Char/e_01_cutscene/qhrw/{f}/{f}.cine",
        "Char/e_01_cutscene/{f}/{f}.cine",
        "Char/e_01_cutscene/qhrw/{f}.cine",
        "Char/cutscene/{f}/{f}.cine",
        "Char/{f}/{f}.cine",
        "client/cine/{f}.cine",
        "client/cutscene/{f}/{f}.cine",
    )
    for film in sorted(filmy):
        for wzor in wzorce:
            dodaj(wzor.format(f=film), "cine_wzorzec")

    return kandydaci


def build(output: Path, index_dir: Path) -> dict:
    if not (index_dir / "poi.jsonl").is_file():
        raise SystemExit(f"brak katalogu wyciągu: {index_dir} (uruchom z korzenia repo)")

    kand = kandydaci(index_dir)
    pochodne = Counter(k["pochodzenie"] for k in kand)
    kandydaci_jsonl = "".join(
        json.dumps(k, ensure_ascii=False, separators=(",", ":")) + "\n" for k in kand
    ).encode("utf-8")

    prefiksy = sum(v for k, v in pochodne.items() if k.startswith("poi_storyline_prefiks"))
    readme = (
        "Where Winds Meet — MPK Skaner\n"
        f"wersja: {WERSJA}\n"
        f"kandydatów ścieżek: {len(kand)} "
        f"(poi_storyline: {pochodne.get('poi_storyline', 0)}, "
        f"poi_storyline_wariant_ext: {pochodne.get('poi_storyline_wariant_ext', 0)}, "
        f"poi_storyline_prefiks: {prefiksy}, "
        f"cine_wzorzec: {pochodne.get('cine_wzorzec', 0)})\n"
        "\n"
        + README_BODY_PL
    )

    files: dict[str, bytes] = {
        "CZYTAJ_TO.txt": b"\xef\xbb\xbf" + _windows_lines(readme),
        "SKANUJ.bat": _windows_lines(BAT_TEMPLATE),
        "narzedzia/mpk_skaner.py": (TOOLS_DIR / "mpk_skaner.py").read_bytes(),
        "narzedzia/kandydaci.jsonl": kandydaci_jsonl,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = ZipInfo(filename=name, date_time=FIXED_ZIP_TIME)
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            if name.endswith(".bat"):
                info.external_attr = 0o755 << 16
            archive.writestr(info, files[name])

    with ZipFile(output) as check:
        if check.testzip() is not None or set(check.namelist()) != set(files):
            raise RuntimeError("wygenerowane archiwum nie przeszło weryfikacji")
        for name, expected in files.items():
            if check.read(name) != expected:
                raise RuntimeError(f"niezgodność zawartości w archiwum dla {name}")

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "ok": True,
        "zip": str(output),
        "bajtow": output.stat().st_size,
        "sha256": digest,
        "kandydatow": len(kand),
        "pochodzenie": dict(sorted(pochodne.items())),
        "plikow_w_zip": len(files),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--indeks", default=str(ROOT / "index"), help="katalog wyciągu index/")
    parser.add_argument("--output", default=str(ROOT / "dist" / NAZWA_ZIP), help="ścieżka wynikowego ZIP-a")
    args = parser.parse_args(argv)
    wynik = build(Path(args.output), Path(args.indeks))
    print(json.dumps(wynik, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
