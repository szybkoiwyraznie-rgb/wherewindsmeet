#!/usr/bin/env python3
"""Czytanka WWM do czytania — dialog linia po linii, trzy pliki.

To nie jest zestaw techniczny: żadnych znaczników czasu, kluczy ani tabel.
Każda kwestia to jedna linia postaci `- **Mówca:** tekst`, bez pustych linii
między kwestiami.

Pliki (po jednym na rodzaj treści):

- `01_sceny.md` — wszystkie sceny dialogowe po kolei: prolog, potem krainy
  w kolejności odwiedzania, w krainie po numerze dialogu,
- `02_cutsceny.md` — filmy otwierające i napisy przerywników (pule `text_msg`),
  w kolejności, w jakiej lecą,
- `03_reszta.md` — przedmioty, sztuki walki, encyklopedia, postacie, zadania
  i reszta tekstów, pogrupowane rodzajem i podane jako „nazwa — opis”.

Domyślnie pokazujemy tylko kwestie z polskim przekładem; `--zakres wszystko`
wstawia w to miejsce jawny znacznik `[brak przekładu]`.

Użycie:
    python3 tools/czytanka_czysta.py --wyj out/czytanka --zip dist/WWM_Czytanka.zip
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402
from tools import kolejnosc_gry  # noqa: E402

BEZ_PRZEKLADU = "[brak przekładu]"
BEZ_MAPY = ":sceny-bez-mapy:"
_KOLOR = re.compile(r"#[0-9a-fA-F]{6}|#[A-Z]")
_ODNOSNIK = re.compile(r"<([^<>|]{1,80})(\|[^<>]*)?>")
_SPACJE = re.compile(r"\s+")

KATEGORIE = (
    (("kongfu", "xinfa", "jianghu_skill", "qishu", "buff", "skill", "talent", "school_skill"),
     "Sztuki walki i umiejętności"),
    (("equip", "stuff", "fashion", "item", "bag", "weapon", "armor", "title"),
     "Przedmioty, stroje i tytuły"),
    (("encyclopedia", "manual", "ever_know", "book", "clue", "letter", "email", "jianwen", "envelop"),
     "Encyklopedia, księgi i poszlaki"),
    (("task", "guider", "quest", "storyline", "expedition"),
     "Zadania i wątki"),
    (("fuben", "boss", "monster", "enemy", "combat"),
     "Walka i przeciwnicy"),
    (("world_view", "school", "menpai", "shili", "region", "space", "place", "area", "scene_load", "loading"),
     "Świat, sekty i miejsca"),
    (("person", "npc", "amity", "voice", "cutscene_person", "entity_attr"),
     "Postacie i relacje"),
    (("ui", "setting", "tips", "guide", "sys", "option", "hud", "button"),
     "Interfejs i komunikaty"),
)


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


# W danych gry ta sama postać gracza bywa nazwana różnie; dla czytelnika to zawsze „Ty”.
GRACZ = {nazwa: "Ty" for nazwa in (
    "你", "我", "玩家", "主角", "player", "Player", "PLAYER", "You", "主角（玩家）",
)}
# Techniczne nazwy torów i grupy entity — nie są mówcami.
TECHNICZNE = {"Entity轨道组", "轨道组", "entity", "Entity", "旁白占位"}


def _nazwa_klucza(ix, klucz: str | None, pl: dict[str, str]) -> str:
    if not klucz:
        return ""
    if klucz in pl:
        return pl[klucz]
    tekst = ix.teksty.get(klucz)
    return _czysty(tekst.en or tekst.zrodlo) if tekst is not None else ""


def _mowca(scena: dict, indeks_mowcy, ix, pl: dict[str, str]) -> str:
    """Imię mówcy: polskie, a gdy brak przekładu — angielskie.

    Obsada sceny to `[nazwa_zh, typ, id_osoby, klucz]`. Klucz bywa nazwą
    rekwizytu (np. skrzyni), więc wiarygodniejsze jest `postacie[id]`, a klucz
    bierzemy tylko wtedy, gdy jego chiński tekst zgadza się z nazwą w obsadzie.
    """
    obsada = scena.get("o") or []
    if indeks_mowcy is None or not (0 <= indeks_mowcy < len(obsada)):
        if len(obsada) != 1:
            return ""
        indeks_mowcy = 0
    osoba = obsada[indeks_mowcy]
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


def _linia(mowca: str, tekst: str) -> str:
    return f"- **{mowca}:** {tekst}" if mowca else f"- {tekst}"


def _scena_linie(numer: int, scena: dict, ix, pl: dict[str, str], zakres: str,
                 statystyka: dict) -> list[str]:
    linie: list[str] = []
    for element in scena.get("e") or []:
        if element[0] != "k":
            continue
        klucz = element[2]
        tekst = pl.get(klucz)
        if tekst is None:
            if zakres == "przetlumaczone":
                statystyka["pominiete"] += 1
                continue
            zrodlo = ix.teksty.get(klucz)
            tekst = _czysty(zrodlo.zrodlo) if zrodlo is not None else ""
            if not tekst:
                continue
            tekst = f"{BEZ_PRZEKLADU} {tekst}"
        else:
            statystyka["linii"] += 1
        mowca = _mowca(scena, element[1] if len(element) > 1 else None, ix, pl)
        linie.append(_linia(mowca, tekst))
    if not linie:
        return []
    statystyka["scen"] += 1
    return linie


def _sceny(ix, pl, krainy, mapa_kraina, zakres, statystyka) -> list[str]:
    wedlug: dict[str, list[int]] = {k["kraina"]: [] for k in krainy}
    mapa_projektu: dict[str, dict[int, int]] = {}
    for scena in ix.sceny.values():
        projekt = str(scena.get("p") or "").split(".")[0]
        for mapa in scena.get("m") or []:
            mapa_projektu.setdefault(projekt, {})
            mapa_projektu[projekt][mapa] = mapa_projektu[projekt].get(mapa, 0) + 1
    for numer, scena in ix.sceny.items():
        if not scena.get("e"):
            continue
        mapy = list(scena.get("m") or [])
        if not mapy:
            projekt = str(scena.get("p") or "").split(".")[0]
            liczby = mapa_projektu.get(projekt) or {}
            if liczby:
                mapy = [max(liczby, key=liczby.get)]
        kraina = next((mapa_kraina[m]["kraina"] for m in mapy if m in mapa_kraina), None)
        if kraina is not None:
            wedlug[kraina].append(numer)
        else:
            wedlug.setdefault(BEZ_MAPY, []).append(numer)

    prolog_scen = {n for n, sc in ix.sceny.items()
                   if str(sc.get("p") or "").split(".")[0].endswith("qiancen")}
    prolog_otwarty = False
    out: list[str] = []

    grupy = [(k["kraina"], sorted(wedlug.get(k["kraina"], []))) for k in krainy]
    grupy.append(("Sceny bez przypisanej mapy", sorted(wedlug.get(BEZ_MAPY, []))))
    for tytul, numery in grupy:
        blok: list[str] = []
        for numer in numery:
            linie = _scena_linie(numer, ix.sceny[numer], ix, pl, zakres, statystyka)
            if not linie:
                continue
            if not blok:
                blok += [f"# {tytul}", ""]
            if numer in prolog_scen and not prolog_otwarty:
                blok += ["# Prolog", ""]
                prolog_otwarty = True
            blok.append(f"## Scena {numer}")
            blok.extend(linie)
            blok.append("")
        if blok:
            out.extend(blok)
    return out


def _cutsceny(ix, pl, porzadek, zakres, statystyka) -> list[str]:
    out: list[str] = ["# Cutsceny", ""]

    filmy: dict[int, list[dict]] = {}
    napisy: list[dict] = []
    for klucz, wystapienia in porzadek.items():
        for wiersz in wystapienia:
            if wiersz["z"] == "film" and wiersz["d"] is not None:
                filmy.setdefault(int(wiersz["d"]), []).append({**wiersz, "k": klucz})
            elif wiersz["z"].startswith("napis"):
                napisy.append({**wiersz, "k": klucz})
    mowcy = {w["wiersz"]: w.get("mowca_en") for w in ix.cutsceny_kontekst.get("napis", [])}

    tytuly = {1: "Pieśń o lampionach", 2: "Utwór pingtan „Szpila feniksa”",
              3: "Bitwa na Moście Zhongdu"}
    for numer in sorted(filmy):
        tytul = tytuly.get(numer, f"Film {numer}")
        blok: list[str] = []
        for wiersz in sorted(filmy[numer], key=lambda x: (x["t"] or 0, x["i"] or 0)):
            tekst = pl.get(wiersz["k"])
            if tekst is None:
                if zakres == "przetlumaczone":
                    statystyka["pominiete"] += 1
                    continue
                zrodlo = ix.teksty.get(wiersz["k"])
                tekst = f"{BEZ_PRZEKLADU} {_czysty(zrodlo.zrodlo)}" if zrodlo else ""
                if not tekst:
                    continue
            else:
                statystyka["linii"] += 1
            blok.append(_linia("", tekst))
        if blok:
            out += [f"## Film {numer} — {tytul}", ""] + blok + [""]

    napisy.sort(key=lambda w: w["i"] or 0)
    bloki: list[list[dict]] = []
    for wiersz in napisy:
        if bloki and (wiersz["i"] or 0) - (bloki[-1][-1]["i"] or 0) <= 6:
            bloki[-1].append(wiersz)
        else:
            bloki.append([wiersz])
    for blok_wierszy in bloki:
        linie: list[str] = []
        for wiersz in blok_wierszy:
            tekst = pl.get(wiersz["k"])
            if tekst is None:
                if zakres == "przetlumaczone":
                    statystyka["pominiete"] += 1
                    continue
                zrodlo = ix.teksty.get(wiersz["k"])
                tekst = f"{BEZ_PRZEKLADU} {_czysty(zrodlo.zrodlo)}" if zrodlo else ""
                if not tekst:
                    continue
            else:
                statystyka["linii"] += 1
            linie.append(_linia(_czysty(mowcy.get(wiersz["i"]) or ""), tekst))
        if not linie:
            continue
        pierwszy, ostatni = blok_wierszy[0]["i"], blok_wierszy[-1]["i"]
        naglowek = f"## Cutscena {pierwszy}" if pierwszy == ostatni else f"## Cutscena {pierwszy}–{ostatni}"
        out += [naglowek, ""] + linie + [""]
    return out


def _reszta(ix, pl, uzyte: set[str], statystyka: dict) -> list[str]:
    """Wszystko, co nie jest sceną ani cutsceną: „nazwa — opis”, po rodzajach.

    Wiersz tekstu to `w = (tabela, wiersz)` albo `(tabela, wiersz, klucz_nazwy)`;
    trzeci element wskazuje nazwę własną wiersza (np. imię przedmiotu przy opisie),
    więc nie zgadujemy, co jest nazwą, a co opisem.
    """
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
        if nazwa and nazwa not in zbior:
            sekcje.setdefault(etykieta, {})[nazwa] = []
            zbior.add(nazwa)
        if nazwa:
            if tekst != nazwa and tekst not in nazwa and nazwa not in tekst:
                opis = sekcje[etykieta][nazwa]
                if tekst not in opis:
                    opis.append(tekst)
        else:
            linia = f"- {tekst}"
            if len(linia) >= 4 and linia not in zbior:
                zbior.add(linia)
                bez_nazwy.setdefault(etykieta, []).append(linia)
        statystyka["linii"] += 1

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
    krainy = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))
    mapa_kraina = {mapa: k for k in krainy for mapa in k["mapy"]}
    porzadek: dict[str, list[dict]] = {}
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if wiersz.get("k"):
            porzadek.setdefault(wiersz["k"], []).append(wiersz)

    wyj.mkdir(parents=True, exist_ok=True)
    statystyka = {"scen": 0, "linii": 0, "pominiete": 0, "plikow": 0}

    uzyte: set[str] = set()
    tresc_scen = _sceny(ix, pl, krainy, mapa_kraina, zakres, statystyka)
    for scena in ix.sceny.values():
        uzyte.update(e[2] for e in scena.get("e") or [] if e[0] == "k")
    (wyj / "01_sceny.md").write_text(
        _naglowek("Sceny", "Prolog, potem krainy w kolejności odwiedzania, w krainie po numerze dialogu.")
        + "\n".join(tresc_scen) + "\n", encoding="utf-8")
    statystyka["plikow"] += 1

    tresc_cut = _cutsceny(ix, pl, porzadek, zakres, statystyka)
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if str(wiersz.get("z", "")).startswith("napis"):
            uzyte.add(wiersz["k"])
    (wyj / "02_cutsceny.md").write_text(
        _naglowek("Cutsceny", "Filmy otwierające i napisy przerywników, w kolejności odtwarzania.")
        + "\n".join(tresc_cut) + "\n", encoding="utf-8")
    statystyka["plikow"] += 1

    tresc_reszta = _reszta(ix, pl, uzyte, statystyka)
    (wyj / "03_reszta.md").write_text(
        _naglowek("Reszta tekstów", "Przedmioty, sztuki walki, encyklopedia, postacie, zadania i pozostałe.")
        + "\n".join(tresc_reszta) + "\n", encoding="utf-8")
    statystyka["plikow"] += 1

    (wyj / "README.md").write_text(_readme(statystyka, zakres), encoding="utf-8")
    statystyka["plikow"] += 1
    return statystyka


def _naglowek(tytul: str, opis: str, *, pierwszy: bool = True) -> str:
    return f"# Where Winds Meet — {tytul}\n\n{opis}\n\n"


def _readme(statystyka: dict, zakres: str) -> str:
    return f"""# Czytanka Where Winds Meet

Trzy pliki, po jednym na rodzaj treści:

| plik | zawartość |
|---|---|
| `01_sceny.md` | dialogi scen: prolog, krainy w kolejności odwiedzania, sceny po numerze |
| `02_cutsceny.md` | filmy otwierające i napisy przerywników |
| `03_reszta.md` | przedmioty, sztuki walki, encyklopedia, postacie, zadania, reszta |

Kwestie są podane linia po linii: `- **Mówca:** tekst`. Bez czasów, bez kluczy,
bez tabel. Zakres: **{zakres}** (``przetlumaczone`` pomija kwestie bez polskiego,
``wszystko`` wstawia `{BEZ_PRZEKLADU}`).

Statystyka: {statystyka['scen']} scen, {statystyka['linii']} kwestii,
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

        with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED) as paczka:
            for plik in sorted(wyj.glob("*.md")):
                paczka.write(plik, plik.name)
        print(f"{a.zip}: {Path(a.zip).stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
