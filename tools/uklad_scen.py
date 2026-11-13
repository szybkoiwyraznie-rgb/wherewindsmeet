#!/usr/bin/env python3
"""Kolejność scen w pakiecie dla tłumacza — wyłącznie z danych gry (`index/`).

Gra nie ma jednej listy „scena po scenie”. Kolejność składa się z trzech
rodzajów danych, od najmocniejszego:

1. **Zadania.** Tabela zadań wskazuje dialogi wprost (przyjęcie, rozmowa,
   zakończenie zadania, pytania z wyborami), a zadania tworzą łańcuch
   `pre_task`/`post_task`. Typ zadania (wątek główny, przygody, …) i grupa
   (rozdział) dają podział na pliki; wewnątrz grupy zadania idą w porządku
   topologicznym łańcucha.
2. **Następstwa.** Dialog, do którego prowadzi wybór gracza albo tabela
   następstw, stoi zaraz za dialogiem, z którego wynika.
3. **Numeracja.** Dialog bez wpisu w tabelach zadań, którego numer sąsiaduje
   (odstęp do `ODSTEP`) w tym samym projekcie z dialogiem już ułożonym, stoi
   zaraz za nim. To kolejność z numeracji gry, nie stwierdzone powiązanie —
   w pakiecie jest to napisane przy każdej takiej scenie.

Reszta trafia do dwóch części bez chronologii: rozmowy tła (dialogi wskazywane
tylko przez rozmieszczenie NPC w świecie — grupowane według miejsca) oraz
pozostałe dialogi według projektu i numeru.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

try:
    from tools import indeks as indeks_mod
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import indeks as indeks_mod
    from tools import wypisz

ODSTEP = 5
TYP_WATKU_GLOWNEGO = 1
MOMENTY = ("przyjecie", "rozmowa", "zakonczenie")
# Tabele, które wskazują dialog jako rozmowę tła: rozmieszczenie i reakcje NPC.
RODZAJE_TLA = ("spaces.", "npc_dialog_select", "utility_behaviors", "entity_blackboard")
BEZ_LICZBY = 10**12


@dataclass
class Miejsce:
    """Położenie jednej sceny w pakiecie."""

    dialog: int
    czesc: str  # "zadania" | "projekty" | "tlo"
    zadanie: int | None = None
    moment: str = ""  # przyjecie | rozmowa | zakonczenie | wybor | nastepstwo | numeracja
    za: int | None = None  # dialog, za którym scena stoi (następstwo, numeracja)


@dataclass
class SekcjaZadan:
    typ: int | None
    grupa: int | None
    zadania: list[int] = field(default_factory=list)  # w kolejności łańcucha


@dataclass
class Uklad:
    sekcje: list[SekcjaZadan]
    sceny_zadania: dict[int, list[Miejsce]]  # zadanie -> sceny w kolejności
    projekty: list[tuple[str, list[int]]]  # (projekt, dialogi wg numeru)
    tlo: list[tuple[tuple, list[int]]]  # (("miejsce", numer) | ("pole", nazwa), dialogi)
    miejsca: dict[int, Miejsce]
    cykle: int  # ile razy łańcuch pre/post zamykał się w cykl (przerwany)


def kolejnosc_typow(ix) -> list:
    """Typy zadań: wątek główny pierwszy, dalej według kolejności z gry i numeru."""
    types = {task.get("typ") for task in ix.zadania.values()}

    def key(typ):
        if typ == TYP_WATKU_GLOWNEGO:
            return (0, 0, 0)
        if typ is None:
            return (3, 0, 0)
        row = ix.typy_zadan.get(typ)
        return (1, row.get("kolejnosc", 99), typ) if row else (2, 0, typ)

    return sorted(types, key=key)


def porzadek_topologiczny(ix, tasks: list[int], start: int | None = None) -> tuple[list[int], int]:
    """Zadania jednej grupy w kolejności łańcucha `pre_task`/`post_task`.

    Zasady, w tej kolejności:
    - części rozdziału (`pian`) idą rosnąco, zadania bez `pian` na końcu;
    - w części zaczynamy od zadania startowego grupy, potem od najniższego numeru,
      i idziemy łańcuchem w głąb: po zadaniu jego następniki z tej samej części;
    - zadanie nie stoi przed swoimi poprzednikami — brakujące poprzedniki są
      dociągane tuż przed zadanie, które ich wymaga (zadania pomocnicze bez
      własnego poprzednika lądują więc przy zadaniu, do którego prowadzą).

    Zwraca (kolejność, liczba przerwanych cykli w łańcuchu).
    """
    inside = set(tasks)
    before: dict[int, set[int]] = {task: set() for task in tasks}
    after: dict[int, set[int]] = {task: set() for task in tasks}
    for task in tasks:
        row = ix.zadania[task]
        for other in row.get("pre", ()):
            if other in inside and other != task:
                before[task].add(other)
                after[other].add(task)
        for other in row.get("post", ()):
            if other in inside and other != task:
                before[other].add(task)
                after[task].add(other)

    def pian(task: int) -> int:
        return ix.zadania[task].get("pian") or BEZ_LICZBY

    def key(task: int):
        return (0 if task == start else 1, task)

    done: set[int] = set()
    opened: set[int] = set()
    order: list[int] = []
    cycles = 0
    for root in sorted(tasks, key=lambda task: (pian(task), key(task))):
        if root in done:
            continue
        part = pian(root)
        # wpis stosu: (zadanie, etap); etap 0 = następnik, 1 = wymagany poprzednik, 2 = gotowe do wpisania
        stack = [(root, 0)]
        while stack:
            task, stage = stack.pop()
            if task in done:
                continue
            if stage < 2:
                if task in opened:
                    # Zadanie już czeka na swoje poprzedniki. Jeśli wróciliśmy do niego
                    # jako do poprzednika, łańcuch zamyka się w cykl — przerywamy go tutaj.
                    cycles += stage
                    continue
                opened.add(task)
                stack.append((task, 2))
                stack.extend((other, 1) for other in sorted(before[task] - done, key=key, reverse=True))
            else:
                done.add(task)
                order.append(task)
                following = [other for other in after[task] if other not in done and pian(other) == part]
                stack.extend((other, 0) for other in sorted(following, key=key, reverse=True))
    return order, cycles


def _tlo(ix, scena: dict) -> bool:
    """Scena wskazywana wyłącznie przez tabele rozmieszczenia i reakcji NPC."""
    refs = scena.get("r")
    if not refs:
        return False
    return all(ix.pola_dialogow[number][0].startswith(RODZAJE_TLA) for number, _row in refs)


def uloz(ix) -> Uklad:
    """Ułóż wszystkie sceny z tekstem; każda trafia dokładnie w jedno miejsce."""
    sceny = {number: scene for number, scene in ix.sceny.items() if scene["e"]}

    # następstwa dialogu: tabela następstw, wybory gracza, opcje rozmowy z NPC
    nastepstwa: dict[int, list[int]] = defaultdict(list)

    def nastepuje(source: int, target: int) -> None:
        if target in sceny and target != source and target not in nastepstwa[source]:
            nastepstwa[source].append(target)

    for number, scene in ix.sceny.items():
        for target in scene.get("x", ()):
            nastepuje(number, target)
    pytania: dict[int, list[dict]] = defaultdict(list)
    for key in sorted(ix.wybory, key=lambda value: (ix.wybory[value].get("pytanie") or 0, ix.wybory[value].get("krok") or 0, value)):
        row = ix.wybory[key]
        pytania[row.get("pytanie")].append(row)
        targets = [target for choice in row["wybory"] for target in choice.get("dialogi", ())]
        for source in row.get("po_dialogach", ()):
            for target in targets:
                nastepuje(source, target)
    for number in sorted(ix.opcje_npc):
        row = ix.opcje_npc[number]
        targets = [
            int(option["parametr"])
            for option in row["opcje"]
            if isinstance(option.get("parametr"), str) and option["parametr"].isdigit()
        ]
        for source in row["dialogi"]:
            for target in targets:
                nastepuje(source, target)

    # zadania w kolejności: typ -> grupa -> łańcuch
    by_section: dict[tuple, list[int]] = defaultdict(list)
    for number, task in ix.zadania.items():
        by_section[(task.get("typ"), task.get("grupa"))].append(number)
    sekcje: list[SekcjaZadan] = []
    cykle = 0
    for typ in kolejnosc_typow(ix):
        groups = [group for (kind, group) in by_section if kind == typ]

        def group_key(group):
            row = ix.grupy.get(group) if group is not None else None
            return (
                0 if group is not None else 1,
                (row or {}).get("kolejnosc", BEZ_LICZBY),
                group if group is not None else 0,
            )

        for group in sorted(groups, key=group_key):
            start = (ix.grupy.get(group) or {}).get("start") if group is not None else None
            order, cycle = porzadek_topologiczny(ix, by_section[(typ, group)], start)
            cykle += cycle
            sekcje.append(SekcjaZadan(typ, group, order))

    def dialogi_zadania(task: dict) -> list[tuple[int, str]]:
        found = [(dialog, moment) for moment in MOMENTY for dialog in (task.get("dialogi") or {}).get(moment, ())]
        for question in task.get("wybory", ()):
            for row in pytania.get(question, ()):
                found += [(dialog, "wybor") for dialog in row.get("po_dialogach", ())]
                found += [(dialog, "wybor") for choice in row["wybory"] for dialog in choice.get("dialogi", ())]
        return found

    # pierwszy (w kolejności pakietu) wpis zadania, który wskazuje dialog wprost
    bezposrednie: dict[int, int] = {}
    for sekcja in sekcje:
        for number in sekcja.zadania:
            for dialog, _moment in dialogi_zadania(ix.zadania[number]):
                if dialog in sceny:
                    bezposrednie.setdefault(dialog, number)

    miejsca: dict[int, Miejsce] = {}
    sceny_zadania: dict[int, list[Miejsce]] = {}
    for sekcja in sekcje:
        for number in sekcja.zadania:
            placed: list[Miejsce] = []
            for dialog, moment in dialogi_zadania(ix.zadania[number]):
                if dialog in miejsca or bezposrednie.get(dialog) != number:
                    continue
                miejsce = miejsca[dialog] = Miejsce(dialog, "zadania", number, moment)
                placed.append(miejsce)
                # następstwa bez własnego wpisu zadania stoją zaraz za dialogiem
                stack = [(target, dialog) for target in reversed(nastepstwa.get(dialog, ()))]
                while stack:
                    target, source = stack.pop()
                    if target in miejsca or target in bezposrednie:
                        continue
                    miejsce = miejsca[target] = Miejsce(target, "zadania", number, "nastepstwo", source)
                    placed.append(miejsce)
                    stack.extend((following, target) for following in reversed(nastepstwa.get(target, ())))
            if placed:
                sceny_zadania[number] = placed

    # numeracja: dialog sąsiadujący numerem z ułożonym, w tym samym projekcie
    by_project: dict[str, list[int]] = defaultdict(list)
    for number, scene in sceny.items():
        by_project[scene.get("p") or ""].append(number)
    przylaczone: dict[int, list[Miejsce]] = defaultdict(list)
    for project in sorted(by_project):
        previous = None
        anchor: int | None = None
        for number in sorted(by_project[project]):
            if number in miejsca:
                anchor = number
            elif _tlo(ix, sceny[number]):
                pass  # rozmowa tła: nie przerywa ciągu numerów, ale sama do niego nie należy
            elif anchor is not None and previous is not None and number - previous <= ODSTEP:
                root = miejsca[anchor]
                miejsce = Miejsce(number, "zadania", root.zadanie, "numeracja", anchor)
                przylaczone[anchor].append(miejsce)
            else:
                anchor = None
            previous = number
    for task, placed in sceny_zadania.items():
        extended: list[Miejsce] = []
        for miejsce in placed:
            extended.append(miejsce)
            extended.extend(przylaczone.get(miejsce.dialog, ()))
        sceny_zadania[task] = extended
    for attached in przylaczone.values():
        for miejsce in attached:
            miejsca[miejsce.dialog] = miejsce

    # reszta: rozmowy tła według miejsca, pozostałe według projektu
    tlo: dict[tuple, list[int]] = defaultdict(list)
    projekty: dict[str, list[int]] = defaultdict(list)
    for number in sorted(sceny):
        if number in miejsca:
            continue
        scene = sceny[number]
        if _tlo(ix, scene):
            if scene.get("m"):
                key = ("miejsce", min(scene["m"]))
            else:
                kind, path = ix.pola_dialogow[scene["r"][0][0]][:2]
                key = ("pole", f"{kind} :: {path}")
            tlo[key].append(number)
            miejsca[number] = Miejsce(number, "tlo")
        else:
            projekty[scene.get("p") or ""].append(number)
            miejsca[number] = Miejsce(number, "projekty")

    return Uklad(
        sekcje=sekcje,
        sceny_zadania=sceny_zadania,
        projekty=sorted(projekty.items()),
        tlo=sorted(tlo.items(), key=lambda item: (item[0][0], str(item[0][1]).zfill(12) if item[0][0] == "miejsce" else item[0][1])),
        miejsca=miejsca,
        cykle=cykle,
    )


def main(argv=None) -> int:
    wypisz.utf8()
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Podsumowanie układu scen wyliczonego z index/.")
    parser.add_argument("indeks", nargs="?", default="index")
    arguments = parser.parse_args(argv)
    ix = indeks_mod.wczytaj(arguments.indeks)
    uklad = uloz(ix)
    counts = defaultdict(lambda: [0, 0])
    for miejsce in uklad.miejsca.values():
        name = miejsce.czesc if miejsce.czesc != "zadania" else f"zadania/{miejsce.moment}"
        counts[name][0] += 1
        counts[name][1] += len(ix.sceny[miejsce.dialog]["e"])
    print(json.dumps({"sceny_i_elementy": dict(sorted(counts.items())), "przerwanych_cykli_lancucha": uklad.cykle}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
