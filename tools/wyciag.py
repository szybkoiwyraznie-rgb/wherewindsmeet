#!/usr/bin/env python3
"""Wyciąg z bazy gry do wersjonowanego katalogu `index/` (format `wwm-indeks-v2`).

Jedno przejście po plikach gry (baza `MANIFEST -> indexN -> dataN` oraz mapy
tekstów) zapisuje w repozytorium wszystko, czego potrzebują dalsze kroki —
pakiet dla tłumacza, import zwrotu, audyt aktualizacji — tak żeby **nie
musiały już czytać plików gry**:

    index/manifest.json          liczby, pokrycie, SHA-256 wejść, lista plików
    index/teksty_X.jsonl         unikalny tekst źródłowy: zh, en, liczba id, główne źródło
    index/zrodla.json            lista „tabela :: pole” (numer = pierwsza liczba w `w`)
    index/sceny_N.jsonl          dialog: obsada, elementy, odwołania, miejsca
    index/warianty.jsonl         kwestie zależne od płci bohatera: id tekstu, klucz, wersja en
    index/pola_dialogow.json     lista pól wskazujących dialogi (numer = pierwsza liczba w `r`)
    index/dymki_N.jsonl          rozmowy w dymkach (`debate_guider_dialog_data`)
    index/zadania.jsonl          zadania: łańcuch pre/post, grupa, dialogi, teksty
    index/grupy_zadan.jsonl      grupy zadań (rozdziały wątku głównego, historie poboczne)
    index/wybory.jsonl           pytania i wybory gracza (`branch_data`) z dialogami
    index/opcje_npc.jsonl        opcje rozmowy z NPC (`npc_talk_options`)
    index/postacie.jsonl         byt -> nazwa i tytuł z tabliczki nad głową
    index/encyklopedia.jsonl     postacie z encyklopedii gry (`world_view_person_*`)
    index/miejsca.jsonl          przestrzeń -> nazwa
    index/zamiany_dialogow.jsonl podmiany dialogów (w tym wersje językowe)

Tekst jest zapisany raz, w `teksty_X.jsonl`; wszystkie inne pliki wskazują go
kluczem (`tools/mapa_tekstow.klucz`: 16 znaków SHA-256 tekstu źródłowego).
Klucza nie ma w wierszu tekstu — wylicza się go z pola `zh` (albo `en`, gdy
`zr` = `en`). Pliki dzielone są stałą regułą (pierwszy znak klucza, numer
dialogu modulo), więc aktualizacja gry zmienia tylko wiersze, które naprawdę
się zmieniły.

Zakres tekstów: identyfikator jest „w grze”, jeśli ma wersję angielską (klient
zachodni go zna) albo jeśli wskazuje go tabela lub dialog. Identyfikatory tylko
z mapy chińskiej, których nic nie wskazuje, są liczone w manifeście i pomijane.

Użycie:
    python3 tools/wyciag.py --baza KATALOG... --zh MAPA [DIFF...] --en MAPA [DIFF...] --wyj index
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

try:
    from tools import baza_gry, mapa_tekstow, sceny_z_bazy, zrodla_tekstow
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import baza_gry, mapa_tekstow, sceny_z_bazy, zrodla_tekstow

FORMAT = "wwm-indeks-v2"
LIMIT_PLIKU = 10 * 1024 * 1024  # limit repozytorium na jeden plik
CZESCI_SCEN = 8  # sceny_N.jsonl: N = numer dialogu modulo 8
CZESCI_DYMKOW = 2
MAKS_ODWOLAN_SCENY = 4
PROG_TRAFIEN = 3
PROG_UDZIALU = 0.5

# Pole (albo tabela) o takiej nazwie może trzymać numer dialogu. O przyjęciu
# pola decyduje pomiar: co najmniej połowa jego liczb musi być numerami dialogów.
_SLOWA_DIALOGU = re.compile(r"dialog|talk|say|popo|speech|bubble")
_PRZESTRZEN = re.compile(r"^spaces\.s(\d+)\.")
RODZAJ_KOD = {"kwestia": "k", "plansza": "p", "wizytowka_imie": "wi", "wizytowka_tytul": "wt", "inne": "i"}


def _liczby(value) -> list[int]:
    """Wszystkie liczby całkowite z wartości: liczba, napis z cyfr, listy zagnieżdżone."""
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, str) and value.isdigit():
        return [int(value)]
    if isinstance(value, list):
        return [number for item in value for number in _liczby(item)]
    return []


class Obserwator:
    """Zbiera z jednego przejścia bazy tabele powiązań i odwołania do dialogów."""

    def __init__(self, dialogi: set[int]):
        self.dialogi = dialogi
        self.zadania: dict[int, dict] = {}
        self.grupy: dict[int, dict] = {}
        self.kolejnosc_grup: dict[int, list[int]] = {}
        self.typy_zadan: dict[int, dict] = {}
        self.streszczenia: list[dict] = []
        self.wybory: dict[str, dict] = {}
        self.nastepstwa: dict[int, list[int]] = {}
        self.opcje_npc: dict[int, dict] = {}
        self.tabliczki: dict[int, tuple[int, int]] = {}  # byt -> (id nazwy, id tytułu)
        self.seryjne: dict[int, tuple[int, int]] = {}  # numer seryjny -> (przestrzeń, byt)
        self.miejsca: dict[int, dict] = {}
        self.osoby: dict[int, dict] = {}
        self.wydarzenia_osob: dict[int, dict] = {}
        self.tozsamosci: list[dict] = []
        self.dymki: dict[str, list] = {}
        self.zamiany: list[dict] = []
        # odwołania do dialogów
        self.pola: list[tuple[str, str]] = []
        self._numer_pola: dict[tuple[str, str], int] = {}
        self.trafienia: Counter = Counter()
        self.liczby: Counter = Counter()
        self.odwolania: dict[int, list[tuple[int, str]]] = defaultdict(list)
        self.przestrzenie_dialogu: dict[int, set[int]] = defaultdict(set)

    # ------------------------------------------------------------ odwołania

    def _pole(self, kind: str, path: str) -> int:
        key = (kind, path)
        number = self._numer_pola.get(key)
        if number is None:
            number = self._numer_pola[key] = len(self.pola)
            self.pola.append(key)
        return number

    def _odwolania(self, kind: str, name: str, key, row) -> None:
        space = _PRZESTRZEN.match(name)
        space_no = int(space.group(1)) if space else None
        row_key = str(key) if kind == name else f"{name}#{key}"

        def walk(value, path: str, hot: bool) -> None:
            if isinstance(value, dict):
                for item_key, item in value.items():
                    part = zrodla_tekstow._pole(item_key)
                    walk(item, f"{path}.{part}" if path else part, hot or bool(_SLOWA_DIALOGU.search(part)))
            elif isinstance(value, list):
                for item in value:
                    walk(item, path + "[]", hot)
            elif hot and not isinstance(value, bool):
                if isinstance(value, int):
                    number = value
                elif isinstance(value, str) and value.isdigit():
                    number = int(value)
                else:
                    return
                field = self._pole(kind, path)
                self.liczby[field] += 1
                if number in self.dialogi:
                    self.trafienia[field] += 1
                    self.odwolania[number].append((field, row_key))
                    if space_no is not None:
                        self.przestrzenie_dialogu[number].add(space_no)

        walk(row, "", bool(_SLOWA_DIALOGU.search(kind)))

    def wiarygodne_pola(self) -> set[int]:
        """Pola, w których co najmniej połowa liczb to numery istniejących dialogów."""
        return {
            field
            for field, hits in self.trafienia.items()
            if hits >= PROG_TRAFIEN and hits / self.liczby[field] >= PROG_UDZIALU
        }

    # ------------------------------------------------------- tabele powiązań

    def __call__(self, kind: str, name: str, key, row) -> None:
        handler = getattr(self, "_t_" + kind.replace(".", "_").replace("*", "x"), None)
        if handler is not None:
            handler(name, key, row)
        self._odwolania(kind, name, key, row)

    def _t_tasks(self, _name, key, row) -> None:
        if not isinstance(row, dict):
            return
        # `process_interact_param` trzyma numer dialogu przy rozmowie z NPC; zostają
        # tylko liczby będące numerami dialogów, reszta to parametry innych interakcji.
        talk = [n for n in _liczby(row.get("process_interact_param")) if n in self.dialogi]
        self.zadania[row.get("no", key)] = {
            "grupa": row.get("group"),
            "typ": row.get("task_type"),
            "pian": row.get("pian_id"),
            "pre": _liczby(row.get("pre_task")),
            "post": _liczby(row.get("post_task")),
            "nazwa": row.get("task_name"),
            "cel": row.get("task_target_str"),
            "opis": row.get("task_desc_str"),
            "przestrzen": row.get("task_space"),
            "dialogi": {
                "przyjecie": _liczby(row.get("fetch_play_dialogs")) + _liczby(row.get("fetch_dialogs_id")),
                "rozmowa": talk,
                "zakonczenie": _liczby(row.get("finish_play_dialogs")) + _liczby(row.get("finish_dialogs")),
            },
            "wybory": _liczby(row.get("finish_choice")) + _liczby(row.get("get_task_choice")),
        }

    def _t_task_group_info(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.grupy[row.get("id", key)] = {
                "nazwa": row.get("group_name"),
                "numer_tytulu": row.get("title_no"),
                "tytul": row.get("title_name"),
                "kolejnosc": row.get("group_sort"),
                "start": row.get("start_task"),
                "koniec": _liczby(row.get("end_task")),
                "przestrzen": row.get("space_no"),
            }

    def _t_group_tasks(self, _name, key, row) -> None:
        self.kolejnosc_grup[key] = _liczby(row)

    def _t_task_types(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.typy_zadan[row.get("id", key)] = {"nazwa": row.get("type_name"), "kolejnosc": row.get("show_order")}

    def _t_plot_recap_data(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.streszczenia.append(
                {
                    "id": row.get("id", key),
                    "grupa": row.get("group_id"),
                    "tekst": row.get("synopsis_text"),
                    "pierwsze": row.get("first_task"),
                    "ostatnie": _liczby(row.get("last_task")),
                }
            )

    def _t_branch_data(self, _name, key, row) -> None:
        if not isinstance(row, dict):
            return
        choices = []
        for field, value in row.items():
            if not isinstance(field, str) or not field.startswith("choice_") or not field[7:].isdigit():
                continue
            number = field[7:]
            choices.append(
                {
                    "nr": int(number),
                    "tekst": value,
                    "dialogi": _liczby(row.get("choice_dialogs_" + number)),
                    "typ": row.get("type_" + number),
                    "parametry": row.get("param_" + number),
                }
            )
        self.wybory[str(key)] = {
            "pytanie": row.get("ques_argue_no"),
            "krok": row.get("ques_each_no"),
            "tytul": row.get("main_title"),
            "po_dialogach": _liczby(row.get("ques_stop_dialogs")) + _liczby(row.get("first_ques_stop_dialogs")),
            "wybory": sorted(choices, key=lambda choice: choice["nr"]),
        }

    def _t_branch_dialog_subsequent(self, _name, key, row) -> None:
        self.nastepstwa[key] = _liczby(row)

    def _t_npc_talk_options(self, _name, key, row) -> None:
        if not isinstance(row, dict):
            return
        items = []
        for field, value in row.items():
            if isinstance(field, str) and field.startswith("dialog_item_") and field[12:].isdigit():
                number = field[12:]
                items.append(
                    {
                        "nr": int(number),
                        "tekst": value,
                        "typ": row.get("dialog_item_type_" + number),
                        "parametr": row.get("dialog_item_pram_" + number),
                    }
                )
        self.opcje_npc[row.get("no", key)] = {
            "dialogi": _liczby(row.get("dialog_id")),
            "opcje": sorted(items, key=lambda item: item["nr"]),
        }

    def _t_entity_init_data(self, _name, key, row) -> None:
        board = row.get("billboard_data") if isinstance(row, dict) else None
        if isinstance(board, dict) and (board.get("name") or board.get("title")):
            self.tabliczki[row.get("id", key)] = (board.get("name") or 0, board.get("title") or 0)

    def _t_spaces_x_entity(self, name, key, row) -> None:
        space = _PRZESTRZEN.match(name)
        if space and isinstance(row, dict) and isinstance(row.get("npc_no"), int) and isinstance(key, int):
            self.seryjne[key] = (int(space.group(1)), row["npc_no"])

    def _t_space_info(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.miejsca[key] = {"nazwa": row.get("name"), "robocza": row.get("fb_name")}

    def _t_world_view_person_info(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.osoby[row.get("id", key)] = {
                "nazwa": row.get("name"),
                "inna_nazwa": row.get("name_change"),
                "urodziny": row.get("birthday"),
                "historie": _liczby(row.get("story")),
                "kolejnosc": row.get("show_order"),
            }

    def _t_world_view_person_event(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.wydarzenia_osob[row.get("id", key)] = {"tytul": row.get("title"), "opis": row.get("description")}

    def _t_world_view_people_identity(self, _name, _key, row) -> None:
        if isinstance(row, dict):
            self.tozsamosci.append({"osoba": row.get("people_link"), "tekst": row.get("people_identity")})

    def _t_debate_guider_dialog_data(self, _name, key, row) -> None:
        data = row.get("data") if isinstance(row, dict) else None
        if isinstance(data, list):
            self.dymki[str(key)] = [
                (
                    item.get("time") if isinstance(item.get("time"), (int, float)) else 0,
                    item.get("entity_no") if isinstance(item.get("entity_no"), int) else 0,
                    item.get("text"),
                )
                for item in data
                if isinstance(item, dict)
            ]

    def _t_dialog_replace(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.zamiany.append(
                {"dialog": row.get("no", key), "na": _liczby(row.get("new_dialog")), "typ": row.get("type"), "parametr": row.get("param")}
            )

    def _t_dialog_replace_by_language(self, _name, key, row) -> None:
        if isinstance(row, dict):
            self.zamiany.append({"dialog": row.get("no", key), "na": _liczby(row.get("en")), "typ": "jezyk_en"})


class Podzial:
    """Zapis JSONL w plikach o stałej regule podziału (`nazwa_<część>.jsonl`).

    Część wiersza wynika z jego treści (znak klucza, numer modulo), a nie
    z rozmiaru pliku, więc dopisanie wiersza nie przesuwa pozostałych.
    """

    def __init__(self, katalog: Path, nazwa: str, czesci: list[str]):
        self.katalog, self.nazwa = katalog, nazwa
        self.wiersze: dict[str, list[str]] = {part: [] for part in czesci}

    def dodaj(self, czesc: str, row) -> None:
        self.wiersze[czesc].append(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    def koniec(self) -> list[dict]:
        files = []
        for part, lines in self.wiersze.items():
            path = self.katalog / f"{self.nazwa}_{part}.jsonl"
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.writelines(lines)
            size = path.stat().st_size
            if size > LIMIT_PLIKU:
                raise ValueError(f"{path.name}: {size} B przekracza limit pliku; zwiększ liczbę części")
            files.append({"plik": path.name, "wierszy": len(lines), "bajtow": size, "sha256": mapa_tekstow.sha256_pliku(path)})
        return files


def zapisz_jsonl(path: Path, rows) -> dict:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return {"plik": path.name, "wierszy": count, "bajtow": path.stat().st_size, "sha256": mapa_tekstow.sha256_pliku(path)}


def zbuduj(baza: baza_gry.Baza, zh: dict[int, str], en: dict[int, str], wyj: Path, wejscia: dict, log=print) -> dict:
    """Zbuduj wyciąg w katalogu `wyj` i zwróć manifest."""
    start = time.time()
    wyj.mkdir(parents=True, exist_ok=True)
    for old in wyj.glob("*.jsonl"):
        old.unlink()

    def czy_tekst(text_id: int) -> bool:
        return text_id in zh or text_id in en

    # 1. sceny z tabel dialog_timelines.<numer>
    numery = sceny_z_bazy.numery_dialogow(baza.tabele)
    sceny: dict[int, dict] = {}
    bledy_scen: dict[int, str] = {}
    for numer in numery:
        try:
            wiersze = dict(baza.wiersze(f"dialog_timelines.{numer}"))
            sceny[numer] = sceny_z_bazy.scena_z_tabeli(numer, wiersze, czy_tekst)
        except (baza_gry.BazaError, ValueError) as error:
            bledy_scen[numer] = str(error)[:200]
    log(f"sceny: {len(sceny)} ({time.time() - start:.0f} s)")

    # 2. jedno przejście po pozostałych tabelach
    obserwator = Obserwator(set(sceny))
    zrodla = zrodla_tekstow.zbierz(baza, czy_tekst, pomin_rodziny=("dialog_timelines",), obserwator=obserwator)
    log(f"tabele: {sum(zrodla.wiersze.values())} wierszy, {len(zrodla.wystapienia)} id z tabel ({time.time() - start:.0f} s)")

    # 3. zakres tekstów i klucze
    wskazane: set[int] = set(zrodla.wystapienia)
    for scena in sceny.values():
        for element in scena["elementy"]:
            wskazane.add(element["text_id"])
            if element["nazwa"]:
                wskazane.add(element["nazwa"])
        for osoba in scena["obsada"]:
            if osoba["nazwa"]:
                wskazane.add(osoba["nazwa"])
    w_zakresie = set(en) | wskazane
    klucz_id: dict[int, str] = {}
    teksty: dict[str, dict] = {}
    for text_id in w_zakresie:
        zrodlowy = zh.get(text_id)
        z_en = zrodlowy is None
        if z_en:
            zrodlowy = en[text_id]
        key = mapa_tekstow.klucz(zrodlowy)
        klucz_id[text_id] = key
        entry = teksty.get(key)
        if entry is None:
            entry = teksty[key] = {"zr": zrodlowy, "z_en": z_en, "n": 0, "en": Counter(), "w": []}
        entry["n"] += 1
        angielski = en.get(text_id)
        if angielski is not None and not z_en:
            entry["en"][angielski] += 1
        if not entry["w"]:
            for pochodzenie, wiersz, _etykieta in zrodla.wystapienia.get(text_id, ()):
                entry["w"] = [pochodzenie, wiersz]
                break

    def k(text_id) -> str | None:
        return klucz_id.get(text_id) if isinstance(text_id, int) and not isinstance(text_id, bool) else None

    pliki: dict[str, object] = {}
    podzial = Podzial(wyj, "teksty", list("0123456789abcdef"))
    for key in sorted(teksty):
        entry = teksty[key]
        if entry["z_en"]:
            # Brak wersji chińskiej: najnowsze teksty mają tylko warstwę języka gry.
            row = {"en": entry["zr"], "zr": "en"}
        else:
            row = {"zh": entry["zr"]}
            if entry["en"]:
                row["en"] = entry["en"].most_common(1)[0][0]
        if entry["n"] > 1:
            row["n"] = entry["n"]
        if entry["w"]:
            row["w"] = entry["w"]
        podzial.dodaj(key[0], row)
    pliki["teksty"] = podzial.koniec()
    (wyj / "zrodla.json").write_text(
        json.dumps(
            [[kind, path, zrodla.liczba[index]] for index, (kind, path) in enumerate(zrodla.pochodzenia)],
            ensure_ascii=False,
            indent=0,
        )
        + "\n",
        encoding="utf-8",
    )
    log(f"teksty: {len(teksty)} unikalnych, {len(w_zakresie)} id w zakresie ({time.time() - start:.0f} s)")

    # 4. sceny z rozwiązanymi nazwami mówców, odwołaniami i miejscami
    wiarygodne = obserwator.wiarygodne_pola()
    numer_pola = {field: number for number, field in enumerate(sorted(wiarygodne, key=lambda f: obserwator.pola[f]))}
    (wyj / "pola_dialogow.json").write_text(
        json.dumps(
            [
                [*obserwator.pola[field], obserwator.trafienia[field], obserwator.liczby[field]]
                for field in sorted(wiarygodne, key=lambda f: obserwator.pola[f])
            ],
            ensure_ascii=False,
            indent=0,
        )
        + "\n",
        encoding="utf-8",
    )
    podzial = Podzial(wyj, "sceny", [str(part) for part in range(CZESCI_SCEN)])
    mowcy = Counter()
    warianty: dict[int, tuple] = {}
    for numer in sorted(sceny):
        scena = sceny[numer]
        miejsca = set(obserwator.przestrzenie_dialogu.get(numer, ()))
        obsada = []
        for osoba in scena["obsada"]:
            nazwa, tytul, byt = osoba["nazwa"], 0, osoba["entity_no"]
            seryjny = obserwator.seryjne.get(byt)
            if seryjny is not None:
                miejsca.add(seryjny[0])
                byt = seryjny[1]
            tabliczka = obserwator.tabliczki.get(byt)
            if tabliczka is not None:
                nazwa = nazwa or tabliczka[0]
                tytul = tabliczka[1]
            obsada.append([osoba["tag"], osoba["typ"], osoba["entity_no"], k(nazwa), k(tytul)])
            if osoba["kwestii"]:
                if osoba["typ"] == sceny_z_bazy.TYP_GRACZ:
                    mowcy["gracz"] += osoba["kwestii"]
                elif k(nazwa):
                    mowcy["nazwa_z_gry"] += osoba["kwestii"]
                elif osoba["tag"]:
                    mowcy["etykieta_robocza"] += osoba["kwestii"]
                else:
                    mowcy["bez_nazwy"] += osoba["kwestii"]
        elementy = []
        for e in scena["elementy"]:
            # [rodzaj, mówca, klucz, wariant, id (tylko wariant płci), klucz podmienionej nazwy]
            element = [
                RODZAJ_KOD[e["rodzaj"]],
                e["mowca"] if e["mowca"] is not None else -1,
                k(e["text_id"]),
                e["wariant"],
                f"{e['text_id']:016x}" if e["wariant"] else None,
                k(e["nazwa"]),
            ]
            while element[-1] in (None, 0) and len(element) > 3:
                element.pop()
            elementy.append(element)
            if e["wariant"]:
                warianty[e["text_id"]] = (k(e["text_id"]), e["wariant"], en.get(e["text_id"]))
        row = {"d": numer, "o": obsada, "e": elementy}
        if scena["projekt"]:
            row["p"] = scena["projekt"]
        if scena["nazwa"]:
            row["n"] = scena["nazwa"]
        if scena["ui_type"] is not None:
            row["u"] = scena["ui_type"]
        if scena["konfiguracja"]:
            row["c"] = scena["konfiguracja"]
        if scena["banki"]:
            row["b"] = sorted({bank.rsplit("/", 1)[-1].removesuffix(".bnk") for bank in scena["banki"]})
        odwolania = []
        for field, row_key in obserwator.odwolania.get(numer, ()):
            if field in wiarygodne:
                pair = [numer_pola[field], row_key]
                if pair not in odwolania:
                    odwolania.append(pair)
        if odwolania:
            row["r"] = odwolania[:MAKS_ODWOLAN_SCENY]
            if len(odwolania) > MAKS_ODWOLAN_SCENY:
                row["rn"] = len(odwolania)
        if miejsca:
            row["m"] = sorted(miejsca)
        if numer in obserwator.nastepstwa:
            row["x"] = obserwator.nastepstwa[numer]
        podzial.dodaj(str(numer % CZESCI_SCEN), row)
    pliki["sceny"] = podzial.koniec()
    # Kwestie zależne od płci bohatera mają własne identyfikatory tekstu; zapisujemy
    # je razem z angielską wersją tego właśnie identyfikatora.
    pliki["warianty"] = zapisz_jsonl(
        wyj / "warianty.jsonl",
        (
            {"id": f"{text_id:016x}", "k": key, "w": wariant, **({"en": angielski} if angielski else {})}
            for text_id, (key, wariant, angielski) in sorted(warianty.items())
        ),
    )

    # 5. rozmowy w dymkach
    podzial = Podzial(wyj, "dymki", [str(part) for part in range(CZESCI_DYMKOW)])
    kwestii_dymkow = rozmow_dymkow = 0
    for key in sorted(obserwator.dymki, key=lambda value: (len(value), value)):
        kwestie = []
        for _czas, byt, text_id in sorted(obserwator.dymki[key], key=lambda item: item[0]):
            if k(text_id) is None:
                continue
            seryjny = obserwator.seryjne.get(byt)
            tabliczka = obserwator.tabliczki.get(seryjny[1] if seryjny else byt)
            kwestie.append([byt, k(text_id), k(tabliczka[0]) if tabliczka else None, seryjny[0] if seryjny else None])
        if kwestie:
            kwestii_dymkow += len(kwestie)
            rozmow_dymkow += 1
            podzial.dodaj(str(int(key) % CZESCI_DYMKOW) if key.isdigit() else "0", {"d": key, "e": kwestie})
    pliki["dymki"] = podzial.koniec()

    # 6. tabele powiązań
    def klucze(row: dict, pola: tuple[str, ...]) -> dict:
        """Wiersz bez pustych pól; pola tekstowe zamienione z id na klucz tekstu."""
        out = {}
        for name, value in row.items():
            if name in pola:
                key = k(value)
                if key:
                    out[name] = key
            elif isinstance(value, dict):
                inner = {item: content for item, content in value.items() if content}
                if inner:
                    out[name] = inner
            elif value not in (None, [], "", 0):
                out[name] = value
        return out

    pliki["zadania"] = zapisz_jsonl(
        wyj / "zadania.jsonl",
        ({"no": no, **klucze(row, ("nazwa", "cel", "opis"))} for no, row in sorted(obserwator.zadania.items())),
    )
    pliki["grupy_zadan"] = zapisz_jsonl(
        wyj / "grupy_zadan.jsonl",
        (
            {"id": no, **klucze(row, ("nazwa", "numer_tytulu", "tytul")), "zadania": obserwator.kolejnosc_grup.get(no, [])}
            for no, row in sorted(obserwator.grupy.items())
        ),
    )
    pliki["typy_zadan"] = zapisz_jsonl(
        wyj / "typy_zadan.jsonl",
        ({"id": no, **klucze(row, ("nazwa",))} for no, row in sorted(obserwator.typy_zadan.items())),
    )
    pliki["streszczenia"] = zapisz_jsonl(
        wyj / "streszczenia.jsonl",
        (klucze(row, ("tekst",)) for row in sorted(obserwator.streszczenia, key=lambda row: row["id"])),
    )
    pliki["wybory"] = zapisz_jsonl(
        wyj / "wybory.jsonl",
        (
            {
                "q": key,
                **klucze({name: row[name] for name in ("pytanie", "krok", "tytul", "po_dialogach")}, ("tytul",)),
                "wybory": [klucze(choice, ("tekst",)) for choice in row["wybory"] if k(choice["tekst"])],
            }
            for key, row in sorted(obserwator.wybory.items())
        ),
    )
    pliki["opcje_npc"] = zapisz_jsonl(
        wyj / "opcje_npc.jsonl",
        (
            {"no": no, "dialogi": row["dialogi"], "opcje": [klucze(item, ("tekst",)) for item in row["opcje"] if k(item["tekst"])]}
            for no, row in sorted(obserwator.opcje_npc.items())
        ),
    )
    pliki["postacie"] = zapisz_jsonl(
        wyj / "postacie.jsonl",
        (
            {"no": no, "n": k(nazwa), "t": k(tytul)}
            for no, (nazwa, tytul) in sorted(obserwator.tabliczki.items())
            if k(nazwa) or k(tytul)
        ),
    )
    tozsamosci = defaultdict(list)
    for row in obserwator.tozsamosci:
        if k(row["tekst"]):
            tozsamosci[row["osoba"]].append(k(row["tekst"]))
    pliki["encyklopedia"] = zapisz_jsonl(
        wyj / "encyklopedia.jsonl",
        (
            {
                "id": no,
                **klucze({name: row[name] for name in ("nazwa", "inna_nazwa", "urodziny", "kolejnosc")}, ("nazwa", "inna_nazwa", "urodziny")),
                "tozsamosc": tozsamosci.get(no, []),
                "historie": [
                    [k(obserwator.wydarzenia_osob[number]["tytul"]), k(obserwator.wydarzenia_osob[number]["opis"])]
                    for number in row["historie"]
                    if number in obserwator.wydarzenia_osob
                ],
            }
            for no, row in sorted(obserwator.osoby.items())
        ),
    )
    pliki["miejsca"] = zapisz_jsonl(
        wyj / "miejsca.jsonl",
        ({"no": no, **klucze(row, ("nazwa",))} for no, row in sorted(obserwator.miejsca.items(), key=lambda item: str(item[0]))),
    )
    pliki["zamiany_dialogow"] = zapisz_jsonl(
        wyj / "zamiany_dialogow.jsonl",
        sorted(obserwator.zamiany, key=lambda row: (str(row["typ"]), str(row["dialog"]))),
    )

    # 7. manifest z liczbami i pokryciem
    elementy_scen = sum(len(scena["elementy"]) for scena in sceny.values())
    kwestii = sum(1 for scena in sceny.values() for e in scena["elementy"] if e["rodzaj"] == "kwestia")
    bez_grupy = sum(1 for scena in sceny.values() for e in scena["elementy"] if e["rodzaj"] == "kwestia" and e["mowca"] is None)
    id_scen = {e["text_id"] for scena in sceny.values() for e in scena["elementy"]}
    en_ids = set(en)
    en_wskazane = len(en_ids & wskazane)
    tylko_zh = set(zh) - en_ids
    manifest = {
        "format": FORMAT,
        "wejscia": wejscia,
        "liczby": {
            "id_w_mapie_zh": len(zh),
            "id_w_mapie_en": len(en),
            "id_w_zakresie": len(w_zakresie),
            "unikalnych_tekstow_w_zakresie": len(teksty),
            "tekstow_bez_wersji_zh": sum(1 for entry in teksty.values() if entry["z_en"]),
            "id_tylko_zh_niewskazane_pominiete": len(tylko_zh - wskazane),
            "id_tylko_zh_wskazane": len(tylko_zh & wskazane),
            "scen": len(sceny),
            "scen_bez_tekstu": sum(1 for scena in sceny.values() if not scena["elementy"]),
            "elementow_scen": elementy_scen,
            "kwestii": kwestii,
            "kwestii_zaleznych_od_plci_bohatera": len(warianty),
            "rozmow_w_dymkach": rozmow_dymkow,
            "kwestii_w_dymkach": kwestii_dymkow,
            "zadan": len(obserwator.zadania),
            "grup_zadan": len(obserwator.grupy),
            "pytan_z_wyborami": len(obserwator.wybory),
            "postaci_z_tabliczka": pliki["postacie"]["wierszy"],
            "postaci_w_encyklopedii": len(obserwator.osoby),
            "miejsc": len(obserwator.miejsca),
        },
        "pokrycie": {
            "id_en_wskazane_przez_tabele_lub_sceny": en_wskazane,
            "id_en_bez_zrodla": len(en_ids) - en_wskazane,
            "procent_id_en_ze_zrodlem": round(100 * en_wskazane / len(en_ids), 2) if en_ids else 0,
            "id_w_scenach": len(id_scen),
            "kwestii_bez_grupy_mowcy": bez_grupy,
            "kwestie_wg_nazwy_mowcy": dict(mowcy),
            "scen_z_odwolaniem": sum(1 for numer in sceny if any(field in wiarygodne for field, _ in obserwator.odwolania.get(numer, ()))),
            "pol_wskazujacych_dialogi": len(wiarygodne),
        },
        "bledy": {
            "tabele": zrodla.bledy,
            "sceny": {str(numer): text for numer, text in bledy_scen.items()},
        },
        "pliki": pliki,
    }
    (wyj / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"gotowe ({time.time() - start:.0f} s)")
    return manifest


def opis_wejsc(katalogi: list[str], zh: list[str], en: list[str], baza: baza_gry.Baza) -> dict:
    """Inwentarz plików wejściowych: nazwy bez ścieżek, rozmiary i SHA-256."""

    def plik(path) -> dict:
        path = Path(path)
        return {"plik": path.name, "bajtow": path.stat().st_size, "sha256": mapa_tekstow.sha256_pliku(path)}

    return {
        "mapa_zh": [plik(path) for path in zh],
        "mapa_en": [plik(path) for path in en],
        "manifest_bazy": plik(baza.sciezka_manifestu),
        "pliki_bazy": len(baza.pliki),
        "tabel": len(baza.tabele),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wyciąg z bazy gry do katalogu index/ (wwm-indeks-v2).")
    parser.add_argument("--baza", nargs="+", required=True, help="katalogi z MANIFEST, indexN, dataN (późniejszy przykrywa)")
    parser.add_argument("--manifest", help="plik MANIFEST, jeśli nie ten z ostatniego katalogu")
    parser.add_argument("--zh", nargs="+", required=True, help="mapa zh_cn i jej warstwy _diff, w kolejności nakładania")
    parser.add_argument("--en", nargs="+", required=True, help="mapa en i jej warstwy _diff, w kolejności nakładania")
    parser.add_argument("--wyj", default="index")
    arguments = parser.parse_args(argv)

    try:
        baza = baza_gry.Baza(arguments.baza, arguments.manifest, pamiec_chunkow=2048)
        zh = mapa_tekstow.zloz(arguments.zh)
        en = mapa_tekstow.zloz(arguments.en)
    except (baza_gry.BazaError, mapa_tekstow.MapaError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    manifest = zbuduj(
        baza, zh, en, Path(arguments.wyj), opis_wejsc(arguments.baza, arguments.zh, arguments.en, baza),
        log=lambda text: print(text, file=sys.stderr),
    )
    print(json.dumps({"ok": True, "liczby": manifest["liczby"], "pokrycie": manifest["pokrycie"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
