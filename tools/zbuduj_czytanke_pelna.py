#!/usr/bin/env python3
"""Pełna Czytanka WWM: trzy warstwy treści + chronologia z gry.

Układ pakietu (to jest ta „trójka”, o której mówi projekt):

1. **Chronologia** (`01_prolog.md`, `02_krainy/`) — gdzie treść pada w grze:
   prolog z transkryptu, potem krainy w kolejności odwiedzania, sceny po numerze
   dialogu. Buduje `tools/buduj_czytanke_gry.py`.
2. **Fabuła** (`03_fabula/`) + **kontekst** (`04_kontekst/`) — te same wydarzenia
   w wątkach zadań, z kartami postaci, encyklopedią, frakcjami, miejscami,
   przedmiotami i sztukami walki przypisanymi 1:1 do scen. Buduje
   `tools/buduj_czytanki.py` (`epizody.md` + `kontekst_scen.md`).
3. **Reszta** (`05_reszta/`) — wszystko pozostałe, podzielone według rodzaju
   danych (bohaterowie, zadania, przedmioty, encyklopedia, świat, walka,
   komunikaty, interfejs). Buduje ten sam `tools/buduj_czytanki.py`
   (`dodatkowe.md`).

Skrypt składa z tego jeden katalog i jedno archiwum, a na końcu sprawdza, ile
kluczy z magazynu tłumaczenia faktycznie widać w pakiecie — żeby nie trzeba było
wierzyć na słowo, że nic nie wypadło.

Użycie:
    python3 tools/zbuduj_czytanke_pelna.py --wyj out/czytanka_pelna \
        --zip dist/WWM_Czytanka_pelna_2026-11-14.zip
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import buduj_czytanke_gry  # noqa: E402

KATALOGI = {
    "epizody": "03_fabula",
    "kontekst_scen": "04_kontekst",
    "dodatkowe": "05_reszta",
}


def _uruchom(cmd: list[str]) -> None:
    wynik = subprocess.run(cmd, capture_output=True, text=True)
    if wynik.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)} → kod {wynik.returncode}\n{wynik.stderr[-4000:]}")


def _pl_w_magazynie(magazyn: Path) -> dict[str, str]:
    pl: dict[str, str] = {}
    for sciezka in sorted(magazyn.glob("pl_*.jsonl")):
        for linia in sciezka.open(encoding="utf-8"):
            rekord = json.loads(linia)
            klucz = rekord.get("k") or rekord.get("klucz")
            if klucz and isinstance(rekord.get("pl"), str):
                pl.setdefault(klucz, rekord["pl"].strip())
    return pl


_KOLOR = re.compile(r"#[0-9a-fA-F]{6}|#[A-Z]")


def _znormalizuj(tekst: str) -> str:
    """Złóż białe znaki, zdejmij znaczniki koloru i kreski tabel.

    Czytanki łamią długie komórki na kilka wierszy tabeli (kolejne fragmenty
    rozdzielone `|`), więc bez usunięcia kresek porównanie gubi tekst, który
    w pliku jest — tylko zawinięty.
    """
    tekst = re.sub(r"<[^<>]{0,80}>", "", tekst)          # odnośniki <imię|id|#Y>
    tekst = _KOLOR.sub("", tekst).replace("|", " ")
    return re.sub(r"\s+", " ", tekst).strip().lower()


def sprawdz_pokrycie(katalog: Path, magazyn: Path, *, proba: int = 600) -> dict:
    """Ile przetłumaczonych tekstów widać w pakiecie (próba losowa, po normalizacji).

    Tabele w czytankach łamią długie komórki na kilka linii i zdejmują znaczniki
    koloru, więc porównujemy tekst złożony w jedną całość, a nie bajt w bajt.
    """
    pl = _pl_w_magazynie(magazyn)
    tekst = _znormalizuj("\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in sorted(katalog.rglob("*.md"))))
    losuj = random.Random(20261114)
    dlugie = [k for k in sorted(pl) if len(_znormalizuj(pl[k])) >= 25]
    wybrane = losuj.sample(dlugie, min(proba, len(dlugie)))
    brak = [k for k in wybrane if _znormalizuj(pl[k])[:45] not in tekst]
    return {
        "kluczy_w_magazynie": len(pl),
        "proba": len(wybrane),
        "nieznalezione_w_probie": len(brak),
        "przyklady": [pl[k][:80] for k in brak[:5]],
    }


def zbuduj(*, index: str, magazyn: str, wyj: Path, zip_path: Path | None,
           limit_bajtow: int = 4_000_000) -> dict:
    if wyj.exists():
        shutil.rmtree(wyj)
    wyj.mkdir(parents=True)

    chronologia = wyj / "chronologia"
    fabula = wyj / "fabula"
    for katalog in (chronologia, fabula):
        katalog.mkdir()

    # 1. warstwa chronologiczna
    stat_chrono = buduj_czytanke_gry.buduj(
        index=index, magazyn=magazyn, wyj=chronologia, zakres="wszystko")
    (wyj / "01_prolog.md").write_text(
        (chronologia / "00_prolog.md").read_text(encoding="utf-8"), encoding="utf-8")
    (chronologia / "00_prolog.md").unlink()
    (wyj / "02_krainy").mkdir()
    for plik in sorted(chronologia.glob("*.md")):
        cel = "02_krainy" if plik.name[0] == "k" else ""
        plik.replace(wyj / cel / plik.name if cel else wyj / plik.name)
    chronologia.rmdir()

    # 2 i 3. fabuła, kontekst, reszta — z dotychczasowego budowniczego
    _uruchom([
        sys.executable, "tools/buduj_czytanki.py",
        "--indeks", index, "--magazyn", magazyn, "--zakres", "wszystko",
        "--wyj-katalog", str(fabula), "--podziel-powyzej", str(limit_bajtow),
        "--wersja", "v4",
    ])
    for prefiks, katalog in KATALOGI.items():
        cel = wyj / katalog
        cel.mkdir()
        pliki = sorted(fabula.glob(f"{prefiks}*.md"))
        if not pliki:
            raise SystemExit(f"brak pliku {prefiks}*.md w {fabula}")
        for plik in pliki:
            plik.replace(cel / plik.name)
    for reszta in sorted(fabula.glob("*.md")):
        reszta.replace(wyj / reszta.name)
    fabula.rmdir()

    pokrycie = sprawdz_pokrycie(wyj, Path(magazyn))
    (wyj / "README.md").write_text(_readme(stat_chrono, pokrycie), encoding="utf-8")

    wynik = {"katalog": str(wyj), "plikow": len(list(wyj.rglob("*.md"))),
             "chronologia": stat_chrono, "pokrycie": pokrycie}
    if zip_path:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as paczka:
            for plik in sorted(wyj.rglob("*.md")):
                paczka.write(plik, plik.relative_to(wyj).as_posix())
        wynik["zip"] = str(zip_path)
        wynik["zip_bajtow"] = zip_path.stat().st_size
    return wynik


def _readme(stat_chrono: dict, pokrycie: dict) -> str:
    return f"""# Czytanka Where Winds Meet — pakiet pełny

Trzy rodzaje treści, tak jak w ustaleniach projektu:

| katalog | co to jest |
|---|---|
| `01_prolog.md` | prolog w kolejności sprawdzonej z transkryptem gracza |
| `02_krainy/` | **chronologia**: krainy w kolejności odwiedzania, w każdej sceny po numerze dialogu, na końcu filmy, napisy puli i aneks scen bez mapy |
| `03_fabula/` | **fabuła**: te same wydarzenia w wątkach zadań, z numeracją `Epizod E / Scena E.S` |
| `04_kontekst/` | **kontekst 1:1 do fabuły**: postacie, encyklopedia, frakcje, miejsca, poezja lokacji, księgi, poszlaki, przedmioty, sztuki walki |
| `05_reszta/` | **cała pozostała treść wg rodzaju**: bohaterowie, zadania, przedmioty, encyklopedia, świat, walka, komunikaty, interfejs |

Kolejność czytania: `01` → `02` (jak gra pokazuje treść) albo `03` → `04`
(wątkami, z kontekstem). `05` to materiał do przejrzenia i weryfikacji przekładu;
nie jest częścią żadnej sceny.

Statystyka chronologii: {stat_chrono['scen']} scen, {stat_chrono['linii']} linii
(w tym {stat_chrono['linii_pl']} z polskim), {stat_chrono['krain']} krain,
{stat_chrono.get('napisow', 0)} wierszy puli napisów.

Sprawdzenie pokrycia magazynu: {pokrycie['kluczy_w_magazynie']} kluczy z polskim,
próba {pokrycie['proba']} losowych — nie znaleziono w pakiecie
{pokrycie['nieznalezione_w_probie']}.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    ap.add_argument("--wyj", default="out/czytanka_pelna")
    ap.add_argument("--zip", default="")
    ap.add_argument("--limit-bajtow", type=int, default=4_000_000)
    a = ap.parse_args(argv)

    wynik = zbuduj(index=a.index, magazyn=a.magazyn, wyj=Path(a.wyj),
                   zip_path=Path(a.zip) if a.zip else None, limit_bajtow=a.limit_bajtow)
    print(json.dumps(wynik, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
