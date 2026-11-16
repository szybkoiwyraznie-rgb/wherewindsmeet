#!/usr/bin/env python3
"""Czytanka WWM w kolejności, w jakiej teksty pojawiają się w grze.

Porządek (ustalony z właścicielem projektu):

1. **Prolog** — w kolejności spisanej z gry i sprawdzonej linia w linię
   (`zwrotki/prolog_wg_klucza.md`, narzędzie `tools/prolog_z_klucza.py`).
2. **Krainy** — w kolejności odwiedzania, wyliczonej z łańcucha zadań
   (`index/prowincje.json`, narzędzie `tools/prowincje.py`).
3. **Sceny w krainie** — numer dialogu rosnąco (numeracja autorska gry).
4. **W scenie** — kolejność z timeline (`time`/`order`), napisy puli po `id`,
   filmy po `time` (`index/kolejnosc_*.jsonl`).
5. **Warianty** — te same kwestie w innych odgałęzieniach: aneks w prologu,
   reszta zostaje w toku jako osobne sceny o własnych numerach.

Sceny, które prolog wyczerpuje, nie są powtarzane w krainach. Scena bez mapy
dziedziczy krainę po projekcie (`对话-*`); projekty bez żadnej mapy trafiają do
`95_bez_mapy.md` — nic nie znika, ale i nic nie jest zgadywane.

Użycie:
    python3 tools/buduj_czytanke_gry.py --wyj czytanka --zip czytanka.zip
    python3 tools/buduj_czytanke_gry.py --zakres przetlumaczone   # tylko z PL
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402
from tools import kolejnosc_gry, prolog_z_klucza  # noqa: E402

NIEWIDOCZNE = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")
NA_PLIK = 1500  # scen (albo wierszy napisów) w jednym pliku


def _komorka(tekst: str) -> str:
    tekst = NIEWIDOCZNE.sub("", tekst or "").replace("\r", " ")
    tekst = re.sub(r"\s*\n\s*", " ", tekst).strip()
    return tekst.replace("|", "\\|")


def _projekt(scena: dict) -> str:
    """Nazwa projektu dialogowego bez rozszerzenia (`对话-qiancen`)."""
    return str(scena.get("p") or "").split(".")[0]


def _mapa_projektu(ix) -> dict[str, int]:
    """Projekt → mapa, na której stoi najwięcej jego scen."""
    liczby: dict[str, dict[int, int]] = {}
    for scena in ix.sceny.values():
        projekt = _projekt(scena)
        if not projekt:
            continue
        for mapa in scena.get("m") or []:
            liczby.setdefault(projekt, {})
            liczby[projekt][mapa] = liczby[projekt].get(mapa, 0) + 1
    return {p: max(c, key=c.get) for p, c in liczby.items() if c}


def _wczytaj_pl(magazyn: str | Path) -> dict[str, str]:
    """Klucz → polski tekst z magazynu tłumaczenia."""
    pl: dict[str, str] = {}
    for sciezka in sorted(Path(magazyn).glob("pl_*.jsonl")):
        for linia in sciezka.open(encoding="utf-8"):
            rekord = json.loads(linia)
            klucz = rekord.get("k") or rekord.get("klucz")
            tekst = rekord.get("pl")
            if klucz and isinstance(tekst, str):
                pl.setdefault(klucz, tekst.strip())
    return pl


def _wczytaj_kolejnosc(katalog: str | Path) -> dict[str, list[dict]]:
    porzadek: dict[str, list[dict]] = {}
    for wiersz in kolejnosc_gry.wczytaj(Path(katalog)):
        if wiersz.get("k"):
            porzadek.setdefault(wiersz["k"], []).append(wiersz)
    return porzadek


def _linie_sceny(scena: dict) -> list[tuple[str, str]]:
    """(mówca, klucz tekstu) w kolejności z timeline."""
    obsada = scena.get("o") or []
    wynik: list[tuple[str, str]] = []
    for element in scena.get("e") or []:
        if element[0] != "k":
            continue
        klucz = element[2]
        indeks_mowcy = element[1] if len(element) > 1 and isinstance(element[1], int) else None
        mowca = ""
        if indeks_mowcy is not None and 0 <= indeks_mowcy < len(obsada):
            mowca = str(obsada[indeks_mowcy][0] or "")
        elif obsada:
            mowca = str(obsada[0][0] or "")
        wynik.append((mowca, klucz))
    return wynik


def _scena_md(numer: int, scena: dict, ix, pl: dict[str, str], zakres: str, statystyka: dict) -> list[str]:
    """Blok sceny albo pusta lista, gdy w danym zakresie nie ma czego pokazać."""
    wiersze = []
    for kto, klucz in _linie_sceny(scena):
        tekst = ix.teksty.get(klucz)
        if tekst is None:
            continue
        jest_pl = klucz in pl
        if zakres == "przetlumaczone" and not jest_pl:
            continue
        wiersze.append((kto, tekst.zrodlo, tekst.en or "—", pl.get(klucz, "—")))
        statystyka["linii"] += 1
        statystyka["linii_pl"] += 1 if jest_pl else 0
    if not wiersze:
        return []
    statystyka["scen"] += 1
    projekt = _projekt(scena).replace("对话-", "")
    mapy = ", ".join(str(m) for m in (scena.get("m") or [])[:3])
    naglowek = [f"## Scena {numer}" + (f" · {projekt}" if projekt else "")
                + (f" · mapa {mapy}" if mapy else ""), ""]
    tabela = ["| kto | chiński | angielski | polski |", "|---|---|---|---|"]
    for kto, zh, en, polski in wiersze:
        tabela.append(f"| {_komorka(kto)} | {_komorka(zh)} | {_komorka(en)} | {_komorka(polski)} |")
    return naglowek + tabela + [""]


def _nazwa_bazy(kolejnosc: int, kraina: str) -> str:
    bezpieczna = re.sub(r"[^0-9A-Za-z_\u3400-\u9fff]+", "_", kraina).strip("_") or "kraina"
    return f"k{kolejnosc + 1:02d}_{bezpieczna}"


def _zapisz(wyj: Path, baza: str, tytul: str, wstep: list[str], bloki: list[str],
            statystyka: dict, na_plik: int | None = None) -> None:
    """Zapisuje bloki, dzieląc na części po `na_plik` — duże krainy bywają ogromne."""
    na_plik = na_plik or NA_PLIK
    czesci = math.ceil(len(bloki) / na_plik) or 1
    for numer in range(czesci):
        czastka = bloki[numer * na_plik:(numer + 1) * na_plik]
        naglowek = [f"# {tytul}" + (f" — część {numer + 1} z {czesci}" if czesci > 1 else ""), ""]
        tresc = naglowek + wstep + czastka
        nazwa = baza if czesci == 1 else f"{baza}_cz{numer + 1:02d}"
        (wyj / f"{nazwa}.md").write_text("\n".join(tresc) + "\n", encoding="utf-8")
        statystyka["plikow"] += 1


def buduj(*, index: str, magazyn: str, wyj: Path, zakres: str) -> dict:
    ix = indeks_mod.wczytaj(index, teksty=True, sceny=True)
    pl = _wczytaj_pl(magazyn)
    porzadek = _wczytaj_kolejnosc(index)
    krainy = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))
    mapa_kraina = {mapa: k for k in krainy for mapa in k["mapy"]}

    wyj.mkdir(parents=True, exist_ok=True)
    statystyka = {"scen": 0, "linii": 0, "linii_pl": 0, "plikow": 0, "krain": len(krainy)}

    # --- prolog: sprawdzony tok z transkryptu gracza
    (wyj / "00_prolog.md").write_text(
        prolog_z_klucza.zbuduj(index, magazyn), encoding="utf-8")
    statystyka["plikow"] += 1
    klucze_prologu, sceny_prologu = prolog_z_klucza.zasieg(index, magazyn)
    statystyka["scen_prologu"] = len(sceny_prologu)

    # --- filmy otwierające: każda linia ma jawny czas
    filmy: dict[int, list[dict]] = {}
    for klucz, wystapienia in porzadek.items():
        for w in wystapienia:
            if w["z"] == "film" and w["d"] is not None:
                filmy.setdefault(int(w["d"]), []).append({**w, "k": klucz})
    bloki_filmow: list[str] = []
    for numer in sorted(filmy):
        blok = [f"## Film {numer}", "", "| czas | chiński | angielski | polski |", "|---|---|---|---|"]
        for w in sorted(filmy[numer], key=lambda x: (x["t"] or 0, x["i"] or 0)):
            tekst = ix.teksty.get(w["k"])
            if tekst is None:
                continue
            if zakres == "przetlumaczone" and w["k"] not in pl:
                continue
            blok.append(f"| {w['t']} s | {_komorka(tekst.zrodlo)} | {_komorka(tekst.en or '—')} "
                        f"| {_komorka(pl.get(w['k'], '—'))} |")
            statystyka["linii"] += 1
            statystyka["linii_pl"] += 1 if w["k"] in pl else 0
        if len(blok) > 4:
            bloki_filmow.append("\n".join(blok) + "\n")
    _zapisz(wyj, "90_filmy", "Filmy otwierające", [
        "Kolejność linii z `entry_collect_movie_subtitle_data`, czas w sekundach.",
        ""], bloki_filmow, statystyka)

    # --- krainy
    mapa_projektu = _mapa_projektu(ix)
    sceny_wg_krainy: dict[str, list[int]] = {k["kraina"]: [] for k in krainy}
    bez_krainy: list[int] = []
    for numer, scena in ix.sceny.items():
        if not scena.get("e") or numer in sceny_prologu:
            continue
        mapy = list(scena.get("m") or [])
        if not mapy:
            mapa = mapa_projektu.get(_projekt(scena))
            if mapa is not None:
                mapy = [mapa]
        kraina = next((mapa_kraina[m]["kraina"] for m in mapy if m in mapa_kraina), None)
        if kraina is None:
            bez_krainy.append(numer)
        else:
            sceny_wg_krainy[kraina].append(numer)

    for kraina in krainy:
        bloki = [b for numer in sorted(sceny_wg_krainy[kraina["kraina"]])
                 for b in ["\n".join(_scena_md(numer, ix.sceny[numer], ix, pl, zakres, statystyka))]
                 if b]
        if not bloki:
            continue
        mapy = ", ".join(str(m) for m in kraina["mapy"][:12])
        wstep = [
            f"Kraina nr {kraina['kolejnosc'] + 1} w kolejności odwiedzania "
            f"(mapy: {mapy}{'…' if len(kraina['mapy']) > 12 else ''}).",
            "",
            "Sceny w kolejności numerów dialogów — tak numeruje je gra.",
            "",
        ]
        _zapisz(wyj, _nazwa_bazy(kraina["kolejnosc"], kraina["kraina"]),
                kraina["kraina"], wstep, bloki, statystyka)

    # --- sceny bez przypisanej mapy
    if bez_krainy:
        wedlug_projektu: dict[str, list[int]] = {}
        for numer in sorted(bez_krainy):
            wedlug_projektu.setdefault(_projekt(ix.sceny[numer]) or "—", []).append(numer)
        bloki = []
        for projekt in sorted(wedlug_projektu):
            tresc: list[str] = []
            scen_w_bloku = 0
            for numer in wedlug_projektu[projekt]:
                scen_w_bloku += 1
                if scen_w_bloku == 1:
                    tresc += [f"## Projekt {projekt}", ""]
                tresc += _scena_md(numer, ix.sceny[numer], ix, pl, zakres, statystyka)
                if scen_w_bloku % NA_PLIK == 0:
                    bloki.append("\n".join(tresc) + "\n")
                    tresc, scen_w_bloku = [], 0
            if len(tresc) > 2:
                bloki.append("\n".join(tresc) + "\n")
        _zapisz(wyj, "95_bez_mapy", "Sceny bez przypisanej mapy", [
            "Projekty dialogowe, których żadna scena nie wskazuje mapy — ani",
            "bezpośrednio, ani przez resztę projektu. Nie da się ich wpisać w kolejność",
            "krain z danych gry, więc stoją osobno: po nazwie projektu i numerze",
            "dialogu. Nic nie zostało pominięte i nic nie jest zgadywane.", ""],
            bloki, statystyka, na_plik=max(1, math.ceil(len(bloki) / 12)))
        statystyka["bez_mapy"] = len(bez_krainy)
        statystyka["projekty_bez_mapy"] = len(wedlug_projektu)

    # --- pule napisów przerywników (poza prologiem)
    pule = sorted(
        (w for klucz, wystapienia in porzadek.items() for w in wystapienia
         if w["z"].startswith("napis") and klucz not in klucze_prologu),
        key=lambda w: w["i"] or 0,
    )
    wiersze: list[str] = []
    for w in pule:
        tekst = ix.teksty.get(w["k"])
        if tekst is None:
            continue
        if zakres == "przetlumaczone" and w["k"] not in pl:
            continue
        wiersze.append(f"| {w['i']} | {_komorka(tekst.zrodlo)} | {_komorka(tekst.en or '—')} "
                       f"| {_komorka(pl.get(w['k'], '—'))} |")
        statystyka["linii"] += 1
        statystyka["linii_pl"] += 1 if w["k"] in pl else 0
    bloki = []
    for start in range(0, len(wiersze), NA_PLIK):
        blok = ["| id | chiński | angielski | polski |", "|---|---|---|---|"]
        blok += wiersze[start:start + NA_PLIK]
        bloki.append("\n".join(blok) + "\n")
    _zapisz(wyj, "91_napisy_przerywnikow", "Napisy przerywników (pule)", [
        "Wiersze `text_msg`/`text_msg__grey`, które nie należą do prologu;",
        "kolejność rosnąca po `id` — tak silnik czyta napisy w obrębie bloku.", ""],
        bloki, statystyka, na_plik=1)
    statystyka["napisow"] = len(pule)

    statystyka["teksty_poza_narracja"] = _policz_poza_narracja(ix, pl)
    (wyj / "README.md").write_text(_readme(statystyka, zakres), encoding="utf-8")
    statystyka["plikow"] += 1
    return statystyka


def _policz_poza_narracja(ix, pl: dict[str, str]) -> int:
    """Ile przetłumaczonych kluczy nie leży w żadnej scenie (UI, przedmioty, zadania)."""
    uzyte = {e[2] for scena in ix.sceny.values() for e in scena.get("e") or [] if e[0] == "k"}
    return sum(1 for k in pl if k not in uzyte and k in ix.teksty)


def _readme(statystyka: dict, zakres: str) -> str:
    return f"""# Czytanka WWM — kolejność z gry

Pliki czytamy po kolei, tak jak gra pokazuje treść:

| plik | co zawiera |
|---|---|
| `00_prolog.md` | prolog w kolejności sprawdzonej z transkryptem gracza |
| `k01_…` … `k92_…` | krainy w kolejności odwiedzania, w każdej sceny po numerze dialogu |
| `90_filmy.md` | filmy otwierające (jawny czas każdej linii) |
| `91_napisy_przerywnikow.md` | pozostałe napisy puli `text_msg` |
| `95_bez_mapy.md` | dialogi projektów bez żadnej mapy (osobno, po projekcie) |

Zasady porządku: prolog → krainy w kolejności odwiedzania → scena po numerze
dialogu → w scenie kolejność z timeline → warianty w aneksie prologu.
Numer krainy pochodzi z `index/prowincje.json`, wyliczonego z łańcucha zadań
(`pian`, `pre_task`/`post_task`).

W każdej tabeli: mówca, tekst chiński, angielski i polski. Zakres: **{zakres}**
(``przetlumaczone`` chowa linie bez polskiego, ``wszystko`` je pokazuje z „—”).
Duże krainy są dzielone na części po {NA_PLIK} scen.

Statystyka: {statystyka['scen']} scen, {statystyka['linii']} linii
(w tym {statystyka['linii_pl']} z polskim), {statystyka['plikow']} plików,
krain: {statystyka['krain']}, scen wyczerpanych przez prolog:
{statystyka.get('scen_prologu', 0)}, scen bez mapy: {statystyka.get('bez_mapy', 0)}
w {statystyka.get('projekty_bez_mapy', 0)} projektach, wierszy puli napisów:
{statystyka.get('napisow', 0)}.

Poza tą czytanką zostaje {statystyka.get('teksty_poza_narracja', 0)} przetłumaczonych
kluczy, które nie są narracją (nazwy przedmiotów, umiejętności, cele zadań, UI) —
one żyją w paczce językowej i w rejestrze `tlumaczenie/`, nie w scenach.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    ap.add_argument("--wyj", default="czytanka", help="katalog wynikowy")
    ap.add_argument("--zakres", choices=("przetlumaczone", "wszystko"), default="wszystko")
    ap.add_argument("--zip", help="opcjonalna paczka zip z wynikiem")
    a = ap.parse_args(argv)

    wyj = Path(a.wyj)
    statystyka = buduj(index=a.index, magazyn=a.magazyn, wyj=wyj, zakres=a.zakres)
    print(f"{wyj}: {statystyka}")
    if a.zip:
        import zipfile

        with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED) as paczka:
            for plik in sorted(wyj.glob("*.md")):
                paczka.write(plik, plik.name)
        print(f"{a.zip}: {Path(a.zip).stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
