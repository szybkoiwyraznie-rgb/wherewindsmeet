#!/usr/bin/env python3
"""Czytanka WWM do czytania — trzy pliki w układzie ustalonym z właścicielem.

1. `01_sceny_i_cutsceny.md` — sceny **i** cutsceny razem, chronologicznie:
   filmy otwierające, prolog w kolejności sprawdzonej z transkryptem, potem krainy
   w kolejności odwiedzania (sceny po numerze dialogu), na końcu pozostałe pule
   napisów przerywników.
2. `02_kontekst_scen_i_cutscen.md` — kontekst do tych samych jednostek i w tej
   samej kolejności: postacie, encyklopedia, frakcje, miejsca, przedmioty, sztuki
   walki — wszystko, co pada w danej scenie. Hasło ma pełną kartę przy pierwszym
   wystąpieniu.
3. `03_reszta.md` — cała reszta przekładów, której nie ma w 01 ani w 02,
   pogrupowana według rodzaju danych.

Format kwestii w 01: jedna linia `- **Mówca:** tekst`, bez czasów, kluczy i tabel.

Użycie:
    python3 tools/czytanka_czysta.py --wyj out/czytanka --zip dist/WWM_Czytanka.zip
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402
from tools import chronologia as chronologia_mod  # noqa: E402
from tools import kolejnosc_gry, powiazania_czytanek  # noqa: E402

BEZ_PRZEKLADU = "[brak przekładu]"
BEZ_MAPY = ":sceny-bez-mapy:"
_KOLOR = re.compile(r"#[0-9a-fA-F]{6}|#[A-Z]")
_ODNOSNIK = re.compile(r"<([^<>|]{1,80})(\|[^<>]*)?>")
_SPACJE = re.compile(r"\s+")

# W danych gracza ta sama postać bywa nazwana różnie; dla czytelnika to zawsze „Ty”.
GRACZ = {nazwa: "Ty" for nazwa in (
    "你", "我", "玩家", "主角", "player", "Player", "PLAYER", "You", "主角（玩家）",
)}
TECHNICZNE = {"Entity轨道组", "轨道组", "entity", "Entity", "旁白占位"}

KATEGORIE = (
    (("kongfu", "xinfa", "jianghu_skill", "qishu", "buff", "skill", "talent"),
     "Sztuki walki i umiejętności"),
    (("equip", "stuff", "fashion", "item", "bag", "weapon", "armor", "title"),
     "Przedmioty, stroje i tytuły"),
    (("encyclopedia", "manual", "ever_know", "book", "clue", "letter", "email",
      "jianwen", "envelop", "poem", "kaoju"),
     "Encyklopedia, księgi i poszlaki"),
    (("task", "guider", "quest", "storyline", "expedition"),
     "Zadania i wątki"),
    (("fuben", "boss", "monster", "enemy", "combat"),
     "Walka i przeciwnicy"),
    (("world_view", "school", "menpai", "shili", "region", "space", "place",
      "area", "loading", "expedition_history"),
     "Świat, sekty i miejsca"),
    (("person", "npc", "amity", "voice", "entity_attr"),
     "Postacie i relacje"),
    (("ui", "setting", "tips", "guide", "sys", "option", "hud", "button"),
     "Interfejs i komunikaty"),
)

_NAZWA = re.compile(r"name|title|bowu|imie", re.I)
_OPIS = re.compile(r"desc|describe|content|text|story|intro|history|word|tip", re.I)


def _czysty(tekst: str) -> str:
    """Zdejmij kody kolorów i odnośniki rich-text, złóż białe znaki."""
    tekst = _ODNOSNIK.sub(lambda m: m.group(1), tekst or "")
    tekst = _KOLOR.sub("", tekst)
    return _SPACJE.sub(" ", tekst).strip()


def _kategoria(tabela: str) -> str:
    nazwa = tabela.lower()
    for slowa, etykieta in KATEGORIE:
        if any(slowo in nazwa for slowo in slowa):
            return etykieta
    return "Pozostałe teksty"


def _magazyn(katalog: Path) -> dict[str, str]:
    pl: dict[str, str] = {}
    for sciezka in sorted(katalog.glob("pl_*.jsonl")):
        for linia in sciezka.open(encoding="utf-8"):
            rekord = json.loads(linia)
            klucz = rekord.get("k") or rekord.get("klucz")
            tekst = rekord.get("pl")
            if klucz and isinstance(tekst, str) and tekst.strip():
                pl.setdefault(klucz, _czysty(tekst))
    return pl


def _nazwa_klucza(ix, klucz: str | None, pl: dict[str, str]) -> str:
    if not klucz:
        return ""
    if klucz in pl:
        return pl[klucz]
    tekst = ix.teksty.get(klucz)
    return _czysty(tekst.en or tekst.zrodlo) if tekst is not None else ""


def _mowca(osoba: list, ix, pl: dict[str, str]) -> str:
    """Imię mówcy: polskie, a gdy brak przekładu — angielskie z danych gry."""
    nazwa_zh = _czysty(str(osoba[0] or ""))
    if nazwa_zh in GRACZ:
        return GRACZ[nazwa_zh]
    if nazwa_zh in TECHNICZNE:
        return ""
    osoba_id = osoba[2] if len(osoba) > 2 else None
    wiersz = ix.postacie.get(osoba_id) if isinstance(osoba_id, int) else None
    if wiersz and wiersz.get("n"):
        nazwa = _nazwa_klucza(ix, wiersz["n"], pl)
        if nazwa:
            return nazwa
    klucz = osoba[3] if len(osoba) > 3 else None
    tekst = ix.teksty.get(klucz) if klucz else None
    if tekst is not None and tekst.zrodlo == nazwa_zh:
        nazwa = _nazwa_klucza(ix, klucz, pl)
        if nazwa:
            return nazwa
    return nazwa_zh


def _mowca_w_scenie(scena: dict, indeks_mowcy, ix, pl) -> str:
    obsada = scena.get("o") or []
    if indeks_mowcy is None or not (0 <= indeks_mowcy < len(obsada)):
        if len(obsada) != 1:
            return ""
        indeks_mowcy = 0
    return _mowca(obsada[indeks_mowcy], ix, pl)


@dataclass
class Jednostka:
    """Scena albo cutscena: jednostka czytanki i kontekstu."""

    rodzaj: str                      # scena | cutscena | film | prolog
    etykieta: str                    # np. „Scena 10094”, „Film 2 — …”
    sekcja: str                      # np. „# 燕南”
    linie: list[tuple[str, str]] = field(default_factory=list)   # (mówca, klucz)
    przestrzenie: set[int] = field(default_factory=set)


def _wczytaj_porzadek(index: str) -> dict[str, list[dict]]:
    porzadek: dict[str, list[dict]] = {}
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if wiersz.get("k"):
            porzadek.setdefault(wiersz["k"], []).append(wiersz)
    return porzadek


TYTULY_FILMOW = {1: "Pieśń o lampionach", 2: "Utwór pingtan „Szpila feniksa”",
                 3: "Bitwa na Moście Zhongdu"}


def _mowca_klucza(klucz: str, ix, pl, porzadek, mowcy_napisow) -> tuple[str, set[int]]:
    """Mówca i przestrzenie dla pojedynczego klucza tekstu z chronologii."""
    przestrzenie: set[int] = set()
    for wiersz in porzadek.get(klucz) or []:
        if wiersz["z"] == "dialog" and wiersz["d"]:
            scena = ix.sceny.get(int(wiersz["d"])) or {}
            przestrzenie.update(int(m) for m in scena.get("m") or [] if str(m).isdigit())
            for element in scena.get("e") or []:
                if element[0] == "k" and element[2] == klucz:
                    return _mowca_w_scenie(scena, element[1] if len(element) > 1 else None,
                                           ix, pl), przestrzenie
        elif str(wiersz["z"]).startswith("napis"):
            nazwa = _czysty(mowcy_napisow.get(wiersz["i"]) or "")
            if nazwa:
                return nazwa, przestrzenie
    return "", przestrzenie


def _nazwy_krain(ix, pl, porzadki: list[dict]) -> dict[str, str]:
    """Chińska nazwa krainy → polska, jeśli przekład jest w magazynie."""
    zh_klucz = {t.zrodlo: k for k, t in ix.teksty.items() if t.zrodlo}
    nazwy: dict[str, str] = {}
    for porzadek in porzadki:
        for nazwa in porzadek.get("nazwy") or []:
            klucz = zh_klucz.get(nazwa)
            if klucz and klucz in pl and pl[klucz]:
                nazwy.setdefault(porzadek["kraina"], pl[klucz])
    return nazwy


def _jednostki_z_chronologii(ix, pl, porzadek, chronologia: list[dict],
                             krainy: list[dict] | None = None) -> list[Jednostka]:
    """Chronologia jest zapisana w `index/chronologia.jsonl`; tu tylko czytamy kolejność."""
    nazwy_pl = _nazwy_krain(ix, pl, krainy or [])

    def sekcja(nazwa: str) -> str:
        polska = nazwy_pl.get(nazwa)
        return f"# {nazwa} — {polska}" if polska and polska != nazwa else f"# {nazwa}"
    mowcy_napisow = {w["wiersz"]: w.get("mowca_en")
                     for w in ix.cutsceny_kontekst.get("napis", []) if w.get("wiersz")}

    def klucze_filmu(numer: int) -> list[str]:
        wiersze = [w for klucz, wystapienia in porzadek.items() for w in wystapienia
                   if w["z"] == "film" and w["d"] is not None and int(w["d"]) == numer]
        wiersze.sort(key=lambda w: (w["t"] or 0, w["i"] or 0))
        return [w["k"] for w in wiersze]

    jednostki: list[Jednostka] = []
    for wiersz in chronologia:
        rodzaj = wiersz["t"]
        if rodzaj == "film":
            numer = int(wiersz["n"])
            jednostki.append(Jednostka(
                "film", f"Film {numer} — {TYTULY_FILMOW.get(numer, f'Film {numer}')}",
                "# Filmy otwierające", [("", k) for k in klucze_filmu(numer)]))
        elif rodzaj == "prolog":
            linie, przestrzenie = [], set()
            for klucz in wiersz.get("k") or []:
                mowca, gdzie = _mowca_klucza(klucz, ix, pl, porzadek, mowcy_napisow)
                przestrzenie |= gdzie
                linie.append((mowca, klucz))
            jednostki.append(Jednostka("prolog", wiersz.get("e") or "Prolog",
                                       "# Prolog", linie, przestrzenie))
        elif rodzaj == "scena":
            numer = int(wiersz["n"])
            scena = ix.sceny.get(numer) or {}
            linie = []
            for element in scena.get("e") or []:
                if element[0] != "k":
                    continue
                mowca = _mowca_w_scenie(scena, element[1] if len(element) > 1 else None, ix, pl)
                linie.append((mowca, element[2]))
            jednostki.append(Jednostka(
                "scena", f"Scena {numer}", sekcja(wiersz["s"]), linie,
                {int(m) for m in scena.get("m") or [] if str(m).isdigit()}))
        elif rodzaj == "cutscena":
            numer = int(wiersz["n"])
            linie = [(_mowca_klucza(k, ix, pl, porzadek, mowcy_napisow)[0], k)
                     for k in wiersz.get("k") or []]
            jednostki.append(Jednostka("cutscena", f"Cutscena {numer}", sekcja(wiersz["s"]), linie))
    return jednostki


def _linia(mowca: str, tekst: str) -> str:
    return f"- **{mowca}:** {tekst}" if mowca else f"- {tekst}"


def _plik_scen(jednostki: list[Jednostka], pl: dict[str, str], zakres: str,
               statystyka: dict) -> tuple[list[str], set[str]]:
    out: list[str] = []
    uzyte: set[str] = set()
    ostatnia_sekcja = None
    for jednostka in jednostki:
        linie = []
        for mowca, klucz in jednostka.linie:
            uzyte.add(klucz)
            tekst = pl.get(klucz)
            if tekst is None:
                if zakres == "przetlumaczone":
                    statystyka["pominiete"] += 1
                    continue
                tekst = BEZ_PRZEKLADU
            else:
                statystyka["linii"] += 1
            linie.append(_linia(mowca, tekst))
        if not linie:
            continue
        statystyka["jednostek"] += 1
        if jednostka.sekcja != ostatnia_sekcja:
            out += [jednostka.sekcja, ""]
            ostatnia_sekcja = jednostka.sekcja
        out.append(f"## {jednostka.etykieta}")
        out.extend(linie)
        out.append("")
    return out, uzyte


def _karta(baza, pl, tabela: str, rid: str) -> tuple[str, str]:
    kolumny = (baza.tabele.get(tabela) or {}).get(rid) or {}
    nazwa = ""
    opis = ""
    for kolumna, klucze in kolumny.items():
        for klucz in klucze:
            tekst = pl.get(klucz)
            if not tekst:
                continue
            if not nazwa and _NAZWA.search(kolumna):
                nazwa = tekst
            elif len(tekst) > len(opis) and (_OPIS.search(kolumna) or not _NAZWA.search(kolumna)):
                opis = tekst
    if not nazwa and not opis:
        return "", ""
    if nazwa and opis and (opis in nazwa or nazwa in opis):
        opis = ""
    return nazwa, opis


def _plik_kontekstu(ix, jednostki: list[Jednostka], pl: dict[str, str], baza) -> tuple[list[str], set[str], int]:
    teksty = {}
    for numer, jednostka in enumerate(jednostki):
        if not jednostka.linie:
            continue
        zrodla = [ix.zh(klucz) for _m, klucz in jednostka.linie]
        teksty[f"u{numer}"] = ("\n".join(z for z in zrodla if z), jednostka.przestrzenie)
    wzmianki = powiazania_czytanek.skanuj_wzmianki_we_scenach(baza, teksty) \
        if hasattr(powiazania_czytanek, "skanuj_wzmianki_we_scenach") \
        else powiazania_czytanek.skanuj_wzmianki_w_scenach(baza, teksty)

    out: list[str] = []
    widziane: dict[tuple[str, str], str] = {}
    uzyte: set[str] = set()
    ostatnia_sekcja = None
    ktory = 0
    for numer, jednostka in enumerate(jednostki):
        if not jednostka.linie:
            continue
        karty: list[str] = []
        for tabela, ridy in (wzmianki.get(f"u{numer}") or {}).items():
            for rid in ridy:
                para = (tabela, rid)
                if para in widziane:
                    continue
                nazwa, opis = _karta(baza, pl, tabela, rid)
                if not nazwa and not opis:
                    continue
                widziane[para] = jednostka.etykieta
                kolumny = (baza.tabele.get(tabela) or {}).get(rid) or {}
                uzyte.update(k for klucze in kolumny.values() for k in klucze)
                karty.append(f"- **{nazwa}:** {opis}" if nazwa and opis
                             else (f"- **{nazwa}**" if nazwa else f"- {opis}"))
        if not karty:
            continue
        ktory += 1
        if jednostka.sekcja != ostatnia_sekcja:
            out += [jednostka.sekcja, ""]
            ostatnia_sekcja = jednostka.sekcja
        out += [f"## {jednostka.etykieta}", ""] + karty + [""]
    return out, uzyte, ktory


def _reszta(ix, pl, uzyte: set[str], statystyka: dict) -> list[str]:
    """Co nie trafiło do 01 ani 02 — pogrupowane rodzajem: „nazwa — opis”."""
    sekcje: dict[str, dict[str, list[str]]] = {}
    bez_nazwy: dict[str, list[str]] = {}
    widziane: dict[str, set[str]] = {}
    for klucz, tekst in pl.items():
        if klucz in uzyte:
            continue
        zrodlo = ix.teksty.get(klucz)
        if zrodlo is None or not zrodlo.w:
            continue
        numer = zrodlo.w[0]
        nazwa_tabeli = ix.zrodla[numer][0] if isinstance(numer, int) and numer < len(ix.zrodla) else str(numer)
        etykieta = _kategoria(nazwa_tabeli)
        nazwa = _nazwa_klucza(ix, zrodlo.w[2], pl) if len(zrodlo.w) > 2 else ""
        zbior = widziane.setdefault(etykieta, set())
        if nazwa:
            if nazwa not in zbior:
                sekcje.setdefault(etykieta, {})[nazwa] = []
                zbior.add(nazwa)
            if tekst != nazwa and tekst not in nazwa and nazwa not in tekst:
                if tekst not in sekcje[etykieta][nazwa]:
                    sekcje[etykieta][nazwa].append(tekst)
        else:
            linia = f"- {tekst}"
            if len(linia) >= 4 and linia not in zbior:
                zbior.add(linia)
                bez_nazwy.setdefault(etykieta, []).append(linia)
        statystyka["reszta"] += 1

    out: list[str] = []
    for etykieta in sorted(set(sekcje) | set(bez_nazwy)):
        out += [f"# {etykieta}", ""]
        for nazwa in sorted(sekcje.get(etykieta, {}), key=str.lower):
            opis = " · ".join(sekcje[etykieta][nazwa])
            out.append(f"- **{nazwa}:** {opis}" if opis else f"- **{nazwa}**")
        out.extend(sorted(bez_nazwy.get(etykieta, []), key=str.lower))
        out.append("")
    return out


def zbuduj(*, index: str, magazyn: str, wyj: Path, zakres: str) -> dict:
    ix = indeks_mod.wczytaj(index, teksty=True, sceny=True)
    pl = _magazyn(Path(magazyn))
    porzadek = _wczytaj_porzadek(index)
    chronologia = chronologia_mod.wczytaj(index)
    krainy = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))

    wyj.mkdir(parents=True, exist_ok=True)
    statystyka = {"jednostek": 0, "linii": 0, "pominiete": 0, "reszta": 0, "plikow": 0,
                  "kontekst": 0}

    jednostki = _jednostki_z_chronologii(ix, pl, porzadek, chronologia, krainy)
    tresc, uzyte = _plik_scen(jednostki, pl, zakres, statystyka)
    (wyj / "01_sceny_i_cutsceny.md").write_text(
        _naglowek("Sceny i cutsceny",
                  "Filmy otwierające, prolog w kolejności z gry, potem krainy po kolei: "
                  "sceny i cutsceny przemieszane w kolejności występowania.") + "\n".join(tresc) + "\n",
        encoding="utf-8")
    statystyka["plikow"] += 1

    baza = powiazania_czytanek.zbuduj_baze(ix)
    tresc_kontekstu, uzyte_kontekstu, ktore = _plik_kontekstu(ix, jednostki, pl, baza)
    statystyka["kontekst"] = ktore
    (wyj / "02_kontekst_scen_i_cutscen.md").write_text(
        _naglowek("Kontekst scen i cutscen",
                  "Te same jednostki i ta sama kolejność co w pliku 01: postacie, encyklopedia, "
                  "frakcje, miejsca, przedmioty i sztuki walki wymienione w scenie. Każde hasło "
                  "ma pełną kartę przy pierwszym wystąpieniu.") + "\n".join(tresc_kontekstu) + "\n",
        encoding="utf-8")
    statystyka["plikow"] += 1

    tresc_reszty = _reszta(ix, pl, uzyte | uzyte_kontekstu, statystyka)
    (wyj / "03_reszta.md").write_text(
        _naglowek("Reszta", "Przekłady, których nie ma w plikach 01 i 02, pogrupowane rodzajem.")
        + "\n".join(tresc_reszty) + "\n", encoding="utf-8")
    statystyka["plikow"] += 1

    (wyj / "README.md").write_text(_readme(statystyka, zakres), encoding="utf-8")
    statystyka["plikow"] += 1
    return statystyka


def _naglowek(tytul: str, opis: str) -> str:
    return f"# Where Winds Meet — {tytul}\n\n{opis}\n\n"


def _readme(statystyka: dict, zakres: str) -> str:
    return f"""# Czytanka Where Winds Meet

| plik | zawartość |
|---|---|
| `01_sceny_i_cutsceny.md` | sceny i cutsceny razem, chronologicznie: filmy, prolog, krainy po kolei, pozostałe napisy |
| `02_kontekst_scen_i_cutscen.md` | kontekst do tych samych jednostek w tej samej kolejności: postacie, encyklopedia, frakcje, miejsca, przedmioty, sztuki walki |
| `03_reszta.md` | przekłady spoza 01 i 02, pogrupowane rodzajem |

Kwestie w 01: `- **Mówca:** tekst`, jedna kwestia na linię, bez czasów i tabel.
Zakres: **{zakres}**.

Statystyka: {statystyka['jednostek']} jednostek, {statystyka['linii']} kwestii,
{statystyka['kontekst']} jednostek z kontekstem, {statystyka['reszta']} pozycji w reszcie,
{statystyka['pominiete']} kwestii bez polskiego pominięto.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    ap.add_argument("--wyj", default="out/czytanka")
    ap.add_argument("--zakres", choices=("przetlumaczone", "wszystko"), default="przetlumaczone")
    ap.add_argument("--zip")
    a = ap.parse_args(argv)

    wyj = Path(a.wyj)
    statystyka = zbuduj(index=a.index, magazyn=a.magazyn, wyj=wyj, zakres=a.zakres)
    print(json.dumps(statystyka, ensure_ascii=False))
    if a.zip:
        import zipfile

        Path(a.zip).parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED) as paczka:
            for plik in sorted(wyj.glob("*.md")):
                paczka.write(plik, plik.name)
        print(f"{a.zip}: {Path(a.zip).stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
