#!/usr/bin/env python3
"""Wiązanie napisów przerywników z cutscenami i metadane cutscen — z bazy gry.

Po co: w wyciągu `index/` napis przerywnika ma tylko identyfikator wiersza
(`text_msg`, 590000–592694) i czasem nazwę nagrania — **nie ma numeru cutsceny**.
Ten program czyta bazę gry (`local/dane`: `MANIFEST` + `data*` + `index*`) i bierze
z niej to, co naprawdę jest w danych:

1. **numer cutsceny z nazwy nagrania** — `sound_data` trzyma dla tekstu jego
   nagranie, a nagrania przerywników mają w nazwie kod filmu
   (`vo_sm_sxdm4_cs_zlxl_hx_02` → `zlxl`), który odpowiada `cutscenes.cine_name`
   (`sq001_zlxl`). Wiązanie zapisujemy tylko wtedy, gdy kod wskazuje **dokładnie
   jedną** cutscenę; sprzeczne odrzucamy.
2. **przestrzeń i czas trwania cutsceny** — `cutscenes.cutscene_space_no`
   i `cutscenes.cine_duration`; `tools/chronologia.py` kładzie dzięki temu cutscenę
   w jej krainie, nawet gdy scena-kotwica nie ma mapy.

Czego baza **nie** daje (sprawdzone na pakiecie aktualizacji z 2026-11-13, tryb
`--audyt` wypisuje dowody):

* osie czasu cutscen (`.cine`) nie są w tym pakiecie w żadnej rodzinie tabel;
* `dialog_timelines.<dialog_no>` (75 007 tabel) to osie czasu **dialogów**: każdy
  `EntityTextSpan` ma `time`, `duration`, `source_id`, `text` i `formatted_text`
  (gotowy chiński tekst), ale napisy puli nie występują tam ani jako identyfikator
  (0 trafień na 404 861 `source_id`/`text`), ani jako tekst inaczej niż przypadkowo
  (pojedyncze linie rozsiane po setkach dialogów);
* żadna inna tabela nie wskazuje wierszy puli ani ich hashy (`text_msg.content`).

Użycie:
    python3 tools/cutsceny_z_bazy.py --dane local/dane --index index
    python3 tools/cutsceny_z_bazy.py --dane local/dane --audyt
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import baza_gry, indeks as indeks_mod  # noqa: E402

# Wiersze puli napisów przerywników w `text_msg` (patrz `index/cutsceny_kontekst.jsonl`).
PULA_NAPISOW = (590000, 592694)

# Kod filmu w nazwie nagrania stoi po `_cs_`: `vo_sm_sxdm4_cs_zlxl_hx_02`.
ZNACZNIK_FILMU = "_cs_"

# `cine_name` w bazie ma prefiks zadania (`sq001_zlxl`), nazwa nagrania go nie ma.
PREFIKS_ZADANIA = "sq"


class CutscenyError(Exception):
    """Baza nie daje się odczytać albo wyciąg nie ma potrzebnych plików."""


def norm(tekst: str) -> str:
    """Tekst bez różnic w białych znakach — gra zapisuje te same zdania różnie."""
    return " ".join((tekst or "").split())


def kod_cine(nazwa) -> str | None:
    """`sq001_zlxl` → `zlxl`; `sq001_zlxl_mobile` → `zlxl_mobile`."""
    if not isinstance(nazwa, str):
        return None
    kod = nazwa.strip()
    if not kod:
        return None
    glowka, _, reszta = kod.partition("_")
    if (
        reszta
        and glowka.lower().startswith(PREFIKS_ZADANIA)
        and glowka[len(PREFIKS_ZADANIA):].isdigit()
    ):
        return reszta
    return kod


def kody_cutscen(wiersze) -> dict[str, set[int]]:
    """Kod filmu → numery cutscen, które ten kod mają w `cine_name`/`cutscene_action`."""
    kody: dict[str, set[int]] = defaultdict(set)
    for no, wiersz in wiersze:
        if not isinstance(wiersz, dict):
            continue
        try:
            numer = int(wiersz.get("no", no) or no)
        except (TypeError, ValueError):
            continue
        for pole in ("cine_name", "cutscene_action"):
            kod = kod_cine(wiersz.get(pole))
            if kod:
                kody[kod].add(numer)
    return {kod: numery for kod, numery in kody.items()}


def kod_z_nagrania(nagranie: str, kody: dict[str, set[int]]) -> str | None:
    """Kod filmu z nazwy nagrania; przy kilku kandydatach wygrywa najdłuższy."""
    if not isinstance(nagranie, str) or ZNACZNIK_FILMU not in nagranie.lower():
        return None
    ogon = nagranie.lower().split(ZNACZNIK_FILMU, 1)[1]
    kandydaci = [kod for kod in kody if kod.lower() == ogon or ogon.startswith(kod.lower() + "_")]
    return max(kandydaci, key=len) if kandydaci else None


def wiaz_napisy(
    pula: dict[str, list[tuple[int, str]]],
    nagrania: dict[str, set[str]],
    kody: dict[str, set[int]],
) -> tuple[list[dict], dict]:
    """Napisy puli, dla których nazwa nagrania wskazuje dokładnie jedną cutscenę.

    `pula`: znormalizowany tekst → [(wiersz `text_msg`, klucz przekładu)].
    `nagrania`: znormalizowany tekst → nazwy nagrań z `sound_data`.
    `kody`: kod filmu → numery cutscen.
    """
    wiazania: dict[int, tuple[str, int, str]] = {}
    sprzeczne: set[int] = set()
    bez_nagrania = bez_kodu = 0
    for tekst, wiersze in pula.items():
        nazwy = nagrania.get(tekst) or set()
        if not nazwy:
            bez_nagrania += len(wiersze)
            continue
        cele: dict[int, str] = {}
        for nazwa in nazwy:
            kod = kod_z_nagrania(nazwa, kody)
            if not kod:
                continue
            numery = kody[kod]
            if len(numery) == 1:
                cele[next(iter(numery))] = kod
        if not cele:
            bez_kodu += len(wiersze)
            continue
        for wiersz, klucz in wiersze:
            if len(cele) > 1:
                sprzeczne.add(wiersz)
                continue
            no, kod = next(iter(cele.items()))
            wiazania[wiersz] = (klucz, no, kod)
    wynik = [
        {"no": no, "wiersz": wiersz, "k": klucz, "dowod": f"vo:{kod}"}
        for wiersz, (klucz, no, kod) in wiazania.items()
        if wiersz not in sprzeczne
    ]
    wynik.sort(key=lambda r: (r["no"], r["wiersz"]))
    statystyka = {
        "napisy_puli": sum(len(w) for w in pula.values()),
        "wiazan": len(wynik),
        "sprzecznych": len(sprzeczne),
        "bez_nagrania": bez_nagrania,
        "bez_kodu_filmu": bez_kodu,
        "cutsceny": dict(Counter(r["no"] for r in wynik)),
    }
    return wynik, statystyka


def metadane(wiersze, fenbao: dict[int, dict] | None = None) -> list[dict]:
    """Cutscena → przestrzeń, czas trwania i plik filmu (tylko to, co jest w danych)."""
    fenbao = fenbao or {}
    wynik: list[dict] = []
    for no, wiersz in wiersze:
        if not isinstance(wiersz, dict):
            continue
        try:
            numer = int(wiersz.get("no", no) or no)
        except (TypeError, ValueError):
            continue
        przestrzen = wiersz.get("cutscene_space_no")
        if isinstance(przestrzen, bool) or not isinstance(przestrzen, int):
            przestrzen = None
        elif przestrzen in (0, 255):
            przestrzen = None
        czas = wiersz.get("cine_duration")
        if isinstance(czas, bool) or not isinstance(czas, (int, float)):
            czas = None
        wpis: dict = {"no": numer}
        if przestrzen is not None:
            wpis["przestrzen"] = przestrzen
        if czas:
            wpis["czas_s"] = round(float(czas), 1)
        if isinstance(wiersz.get("cine_name"), str) and wiersz["cine_name"]:
            wpis["film"] = wiersz["cine_name"]
        pakiet = (fenbao.get(numer) or {}).get("fenbao")
        if isinstance(pakiet, str) and pakiet:
            wpis["pakiet"] = pakiet
        if len(wpis) > 1:
            wynik.append(wpis)
    wynik.sort(key=lambda r: r["no"])
    return wynik


# --------------------------------------------------------------------------- baza


def _wiersze_cutscen(baza):
    for klucz, wiersz in baza.wiersze("cutscenes"):
        yield klucz, wiersz


def _nagrania(baza) -> dict[str, set[str]]:
    """Tekst → nazwy nagrań (`sound_data`); tylko wiersze z tekstem i nagraniem."""
    mapa: dict[str, set[str]] = defaultdict(set)
    for _klucz, wiersz in baza.wiersze("sound_data"):
        if not isinstance(wiersz, dict):
            continue
        tekst, nagranie = wiersz.get("text"), wiersz.get("audio_name")
        if isinstance(tekst, str) and isinstance(nagranie, str) and tekst.strip() and nagranie:
            mapa[norm(tekst)].add(nagranie)
    return mapa


def _fenbao(baza) -> dict[int, dict]:
    mapa: dict[int, dict] = {}
    for klucz, wiersz in baza.wiersze("fenbao_cutscene_info"):
        if not isinstance(wiersz, dict):
            continue
        try:
            mapa[int(wiersz.get("id", klucz))] = wiersz
        except (TypeError, ValueError):
            continue
    return mapa


def pula_z_wyciagu(index: str | Path) -> dict[str, list[tuple[int, str]]]:
    """Tekst puli napisów → [(wiersz `text_msg`, klucz)] z wyciągu `index/`."""
    katalog = Path(index)
    zrodla = json.loads((katalog / "zrodla.json").read_text(encoding="utf-8"))
    rzedy = {numer for numer, wpis in enumerate(zrodla)
             if wpis and str(wpis[0]).split(".")[0] == "text_msg"}
    if not rzedy:
        raise CutscenyError("wyciąg nie ma źródła `text_msg` w `zrodla.json`")
    wyciag = indeks_mod.wczytaj(katalog, teksty=True, sceny=False)
    pula: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for klucz, tekst in wyciag.teksty.items():
        w = tekst.w or ()
        if len(w) < 2 or w[0] not in rzedy:
            continue
        try:
            wiersz = int(w[1])
        except (TypeError, ValueError):
            continue
        if not (PULA_NAPISOW[0] <= wiersz <= PULA_NAPISOW[1]):
            continue
        zh = norm(tekst.zrodlo)
        if zh:
            pula[zh].append((wiersz, klucz))
    return dict(pula)


def zbuduj(katalog: str | Path = "local/dane", index: str | Path = "index") -> dict:
    """Policz wiązania i metadane, zapisz `index/cutsceny_napisy.jsonl` i `..._meta.jsonl`."""
    baza = baza_gry.Baza([katalog])
    pula = pula_z_wyciagu(index)
    kody = kody_cutscen(_wiersze_cutscen(baza))
    nagrania = _nagrania(baza)
    napisy, statystyka = wiaz_napisy(pula, nagrania, kody)
    meta = metadane(_wiersze_cutscen(baza), _fenbao(baza))

    katalog_index = Path(index)
    _zapisz_jsonl(katalog_index / "cutsceny_napisy.jsonl", napisy)
    _zapisz_jsonl(katalog_index / "cutsceny_meta.jsonl", meta)
    return {
        "napisy": statystyka,
        "kodow_filmowych": len(kody),
        "meta": {"wpisow": len(meta),
                 "z_przestrzenia": sum(1 for m in meta if m.get("przestrzen")),
                 "z_czasem": sum(1 for m in meta if m.get("czas_s"))},
    }


def _zapisz_jsonl(sciezka: Path, wiersze: list[dict]) -> None:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_text(
        "".join(json.dumps(w, ensure_ascii=False, separators=(",", ":")) + "\n" for w in wiersze),
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- audyt


def _chodz(wezel, funkcja, glebokosc: int = 0) -> None:
    """Odwiedź wszystkie wartości (także wnętrza słowników i list)."""
    if glebokosc > 8:
        return
    if isinstance(wezel, dict):
        for wartosc in wezel.values():
            if isinstance(wartosc, (dict, list)):
                _chodz(wartosc, funkcja, glebokosc + 1)
            else:
                funkcja(wartosc)
    elif isinstance(wezel, list):
        for element in wezel:
            if isinstance(element, (dict, list)):
                _chodz(element, funkcja, glebokosc + 1)
            else:
                funkcja(element)


def audyt(katalog: str | Path = "local/dane", index: str | Path = "index") -> dict:
    """Sprawdź, czy napisy puli mają w bazie jakiekolwiek odwołanie — i wypisz dowody."""
    baza = baza_gry.Baza([katalog])
    pula = pula_z_wyciagu(index)

    # content hash i numer wiersza każdego napisu puli
    hashe: dict[int, int] = {}
    wiersze_puli: set[int] = set()
    for klucz, wartosc in baza.wiersze("text_msg"):
        if isinstance(wartosc, dict) and isinstance(wartosc.get("content"), int):
            if PULA_NAPISOW[0] <= klucz <= PULA_NAPISOW[1]:
                hashe[wartosc["content"]] = klucz
                wiersze_puli.add(klucz)
    for klucz, wartosc in baza.wiersze("text_msg__grey"):
        if isinstance(wartosc, dict) and isinstance(wartosc.get("content"), int):
            if PULA_NAPISOW[0] <= klucz <= PULA_NAPISOW[1]:
                hashe.setdefault(wartosc["content"], klucz)
                wiersze_puli.add(klucz)

    # Hash tekstu jest unikalny (64-bit), więc trafienie w niego cokolwiek znaczy.
    # Numer wiersza to zwykła liczba — inne tabele mają własne identyfikatory
    # w tym samym zakresie, więc takie trafienia zbieramy osobno jako przypadki.
    rodziny_hash: Counter = Counter()
    rodziny_id: Counter = Counter()
    przyklady: list[tuple[str, str, object]] = []

    def sprawdz(wartosc) -> None:
        if isinstance(wartosc, bool):
            return
        if isinstance(wartosc, int):
            if wartosc in hashe:
                rodziny_hash[_rodzina] += 1
                if len(przyklady) < 10:
                    przyklady.append((_rodzina, _tabela, wartosc))
            elif wartosc in wiersze_puli:
                rodziny_id[_rodzina] += 1

    _rodzina = _tabela = ""
    for nazwa in sorted(baza.tabele):
        if nazwa in ("text_msg", "text_msg__grey"):
            continue
        _rodzina = nazwa.split(".")[0]
        _tabela = nazwa
        try:
            for _klucz, wartosc in baza.wiersze(nazwa):
                _chodz(wartosc, sprawdz)
        except baza_gry.BazaError:
            continue    # pojedyncza nieczytelna tabela nie przerywa audytu

    # osobno: osie czasu dialogów — identyfikatory i gotowe teksty
    identyfikatory = 0
    trafienia_id = 0
    tekst_pula = set(pula)
    trafienia_tekstu: Counter = Counter()

    def licz_id(wartosc) -> None:
        nonlocal identyfikatory, trafienia_id
        if isinstance(wartosc, bool):
            return
        if isinstance(wartosc, int):
            identyfikatory += 1
            if wartosc in hashe:
                trafienia_id += 1

    for nazwa in baza.tabele:
        if not nazwa.startswith("dialog_timelines."):
            continue
        for klucz, wartosc in baza.wiersze(nazwa):
            if klucz != "timeline":
                continue
            _chodz(wartosc, licz_id)
            for tekst in _teksty_osi(wartosc):
                if norm(tekst) in tekst_pula:
                    trafienia_tekstu[nazwa] += 1

    return {
        "napisy_puli": len(wiersze_puli),
        "hashy_puli": len(hashe),
        "odwolania_po_hashu": dict(rodziny_hash),
        "odwolania_po_numerze_wiersza": dict(rodziny_id),
        "przyklady_odwolan": przyklady,
        "osie_dialogow_identyfikatory": identyfikatory,
        "osie_dialogow_trafienia_id": trafienia_id,
        "osie_dialogow_dialogi_z_tekstem_puli": len(trafienia_tekstu),
        "osie_dialogow_najwiecej_w_dialogu": max(trafienia_tekstu.values(), default=0),
        "osie_dialogow_trafien_tekstu": sum(trafienia_tekstu.values()),
    }


def _teksty_osi(wezel, glebokosc: int = 0) -> list[str]:
    """Gotowe teksty (`formatted_text`) z osi czasu."""
    if glebokosc > 8 or not isinstance(wezel, (dict, list)):
        return []
    wynik: list[str] = []
    if isinstance(wezel, dict):
        tekst = wezel.get("formatted_text")
        if isinstance(tekst, str):
            wynik.append(tekst)
        for wartosc in wezel.values():
            wynik.extend(_teksty_osi(wartosc, glebokosc + 1))
    else:
        for element in wezel:
            wynik.extend(_teksty_osi(element, glebokosc + 1))
    return wynik


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Napisy przerywników i metadane cutscen z bazy gry.")
    parser.add_argument("--dane", default="local/dane", help="katalog z plikami bazy gry")
    parser.add_argument("--index", default="index", help="katalog wyciągu (wynik trafia tutaj)")
    parser.add_argument("--audyt", action="store_true",
                        help="sprawdź odwołania do puli napisów w całej bazie (wolno: ~5 min)")
    parser.add_argument("--raport", default="out/audyt_cutscen.json", help="gdzie zapisać wynik audytu")
    args = parser.parse_args(argv)

    try:
        if args.audyt:
            wynik = audyt(args.dane, args.index)
            raport = Path(args.raport)
            raport.parent.mkdir(parents=True, exist_ok=True)
            raport.write_text(json.dumps(wynik, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(json.dumps(wynik, ensure_ascii=False, indent=1))
        statystyka = zbuduj(args.dane, args.index)
    except (baza_gry.BazaError, CutscenyError) as blad:
        print(f"błąd: {blad}", file=sys.stderr)
        return 1
    print(json.dumps(statystyka, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
