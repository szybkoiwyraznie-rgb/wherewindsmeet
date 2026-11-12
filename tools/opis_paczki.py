#!/usr/bin/env python3
"""Teksty opisowe pakietu dla tłumacza: `README.md`, `spis-scen.md`, `spis-misji.md`.

Wszystkie liczby pochodzą z generatora (`tools/buduj_paczke.py`) — nic nie jest
wpisane na stałe, więc README każdej wersji pakietu opisuje dokładnie tę wersję.
"""

from __future__ import annotations

from collections import Counter, defaultdict

try:
    from tools import format_paczki as fmt
    from tools import uklad_scen
except ImportError:  # uruchomienie jako skrypt
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import format_paczki as fmt
    from tools import uklad_scen


def _l(value: int) -> str:
    """Liczba z odstępem co trzy cyfry."""
    return f"{value:,}".replace(",", " ")


def _percentyl(values: list[int], share: float) -> int:
    if not values:
        return 0
    return values[min(len(values) - 1, int(len(values) * share))]


def _tabela_serii(serie: list[dict], sceny: bool = True) -> list[str]:
    scen_head = " scen |" if sceny else ""
    lines = [f"| pliki | co zawiera | plików |{scen_head} elementów | do wpisania `PL:` |", "|---|---|---:|" + ("---:|" if sceny else "") + "---:|---:|"]
    for seria in serie:
        files = seria["pliki"]
        scen = f" {_l(sum(f['scen'] for f in files))} |" if sceny else ""
        lines.append(
            f"| `{seria['baza']}_NN.md` | {seria['tytul']} | {len(files)} |{scen} "
            f"{_l(sum(f['elementow'] for f in files))} | {_l(sum(f['do_wpisania'] for f in files))} |"
        )
    return lines


def spis_scen(generator, serie: list[dict]) -> str:
    lines = [
        "# Spis scen — Where Winds Meet",
        "",
        "Scena to jeden dialog gry (jedna tabela `dialog_timelines.<numer>`); numer w nagłówku",
        "`Scena N/M — dialog D` to numer kolejny w tym pakiecie (N) i numer dialogu z danych gry (D).",
        "Pełna lista scena → plik jest w `spis-scen.tsv` (jedna linia na scenę, do wyszukiwania po numerze dialogu).",
        "",
        "## Serie plików",
        "",
        *_tabela_serii(serie),
        "",
        "## Pliki",
        "",
        "| plik | scen | elementów | do wpisania `PL:` |",
        "|---|---:|---:|---:|",
    ]
    for seria in serie:
        for entry in seria["pliki"]:
            lines.append(f"| `{entry['plik']}` | {_l(entry['scen'])} | {_l(entry['elementow'])} | {_l(entry['do_wpisania'])} |")
    by_kind = Counter()
    for _number, _dialog, _file, part, _task, moment, _elements in generator.spis_scen:
        by_kind[moment if part == "zadania" else part] += 1
    names = {
        "przyjecie": "przy przyjęciu zadania (wpis w tabeli zadań)",
        "rozmowa": "rozmowa w trakcie zadania (wpis w tabeli zadań)",
        "zakonczenie": "przy zakończeniu zadania (wpis w tabeli zadań)",
        "wybor": "pytanie z wyborem należące do zadania",
        "nastepstwo": "następstwo wyboru albo poprzedniego dialogu",
        "numeracja": "bez wpisu zadania — ułożone według numeru za sceną z wpisem",
        "projekty": "bez wpisu zadania — według projektu i numeru",
        "tlo": "rozmowy tła — według miejsca",
    }
    lines += ["", "## Skąd wynika miejsce sceny", "", "| sposób | scen |", "|---|---:|"]
    lines += [f"| {names[kind]} | {_l(by_kind[kind])} |" for kind in names if by_kind[kind]]
    return "\n".join(lines) + "\n"


def spis_misji(generator) -> str:
    ix = generator.ix
    lines = [
        "# Spis zadań — Where Winds Meet",
        "",
        "Kolejność jak w plikach scen: typ zadania (wątek główny pierwszy), grupa zadań (rozdział),",
        "a w grupie zadania według łańcucha poprzedników z danych gry. Wymienione są tylko zadania,",
        "które mają w pakiecie sceny albo przerywniki. Numer zadania jest numerem z danych gry — ten sam",
        "stoi w nagłówkach scen i przy tekstach zadań w `widoki/01_zadania_*.md`.",
        "",
    ]
    by_section: dict[tuple, list[dict]] = defaultdict(list)
    for row in generator.spis_zadan:
        by_section[(row["typ"], row["grupa"])].append(row)
    current_type = object()
    for sekcja in generator.uklad.sekcje:
        rows = by_section.get((sekcja.typ, sekcja.grupa))
        if not rows:
            continue
        if sekcja.typ != current_type:
            current_type = sekcja.typ
            lines += [f"## {generator._nazwa_typu(sekcja.typ)}", ""]
        lines += [
            f"### Grupa {sekcja.grupa} — {generator._nazwa_grupy(sekcja.grupa)}",
            "",
            "| zadanie | nazwa | cel | scen | elementów | plik |",
            "|---|---|---|---:|---:|---|",
        ]
        for row in rows:
            task = ix.zadania[row["zadanie"]]
            name = generator.para(task.get("nazwa")).replace("|", "\\|")
            target = generator.para(task.get("cel")).replace("|", "\\|")
            lines.append(f"| `{row['zadanie']}` | {name} | {target} | {row['scen']} | {row['elementow']} | `{row['plik']}` |")
        lines.append("")
    return "\n".join(lines) + "\n"


def readme(generator, manifest: dict) -> str:
    ix = generator.ix
    liczby = manifest["liczby"]
    sceny = manifest["liczby_sceny"]
    cutsceny = manifest.get("liczby_cutsceny") or {}
    widoki = manifest["liczby_widoki"]
    cut_serie = manifest.get("cutsceny") or []
    wykl = manifest.get("wykluczenia") or {}
    uklad = manifest["uklad"]
    numery = ix.manifest["liczby"]
    pokrycie = ix.manifest["pokrycie"]
    mowcy = pokrycie["kwestie_wg_nazwy_mowcy"]
    pelny = manifest["rodzaj"] == "pełny"

    lengths = sorted(
        len(fmt.zakoduj(text.en))
        for text in (ix.teksty[element[2]] for scene in ix.sceny.values() for element in scene["e"] if element[0] == "k")
        if text.en
    )
    token_counts: Counter = Counter()
    for text in ix.teksty.values():
        for token in set(fmt.rozne_tokeny(fmt.zakoduj(text.zrodlo))):
            token_counts[token] += 1
    top_tokens = ", ".join(f"`{token}`" for token, _count in token_counts.most_common(14))
    main_scenes = sum(
        1 for row in generator.spis_scen if row[3] == "zadania" and ix.zadania.get(row[4], {}).get("typ") == uklad_scen.TYP_WATKU_GLOWNEGO
    )

    out: list[str] = []
    add = out.append
    add(f"# Where Winds Meet — pakiet dla tłumacza (chiński → polski), wersja {manifest['wersja']}")
    add("")
    if pelny:
        add(
            "To jest cały tekst gry w zasięgu klienta zachodniego: wszystkie dialogi z podziałem na sceny i mówców "
            "oraz wszystkie nazwy, opisy i komunikaty z tabel gry. Tłumaczy się **tekst w plikach `.md`**, wpisując "
            "polski po znaczniku `PL:`. Nie trzeba znać formatów gry ani żadnych narzędzi."
        )
    else:
        add(
            "To jest **pakiet uzupełniający** po aktualizacji gry: zawiera tylko teksty, których nie było we "
            "wcześniejszym pakiecie. Nowe kwestie są pokazane w swoich scenach razem ze starymi (stare są oznaczone "
            "i niczego się przy nich nie wpisuje), nowe nazwy i opisy — w widokach. Zasady są te same co w pakiecie pełnym."
        )
    add("")
    add(f"Dane gry: {manifest['indeks']['opis'] or 'brak opisu wersji'}. Pakiet zbudowano {manifest['data']}.")
    add("Źródłem przekładu jest **tekst chiński**; angielska wersja gry stoi obok jako pomoc (nazwy, terminy).")
    if manifest.get("tylko_z_en"):
        add("Zakres pakietu (`--tylko-z-en`): obejmuje wyłącznie pozycje mające wersję angielską w kliencie globalnym (wpisy wyłącznie chińskie bez odpowiednika EN pominięto do czasu ich ewentualnego wydania).")
    add("")
    add("## 0. W skrócie")
    add("")
    add(
        f"1. Rozpakowujesz **`sceny.zip`** — dialogi: {_l(sceny.get('scen', 0))} scen, {_l(sceny.get('elementow', 0))} elementów "
        f"(kwestie, plansze, wybory gracza). Do wpisania: **{_l(sceny.get('do_wpisania', 0))} linii `PL:`**. "
        "Każda scena ma w nagłówku zadanie, miejsce i uczestników; `spis-misji.md` i `spis-scen.md` w tym samym zipie "
        "pokazują układ całości."
    )
    next_step = 2
    if cut_serie:
        add(
            f"{next_step}. Rozpakowujesz **`cutsceny.zip`** — wydzielone napisy cutscen (w tym PROLOG), intro, napisy filmowe oraz "
            f"plansze/powtórki przerywników: {_l(cutsceny.get('elementow', 0))} elementów, **{_l(cutsceny.get('do_wpisania', 0))} linii `PL:`**."
        )
        next_step += 1
    add(
        f"{next_step}. Rozpakowujesz **`widoki.zip`** — teksty spoza scen w grupach: postacie, zadania, przedmioty, walka, świat, "
        f"encyklopedia, komunikaty, interfejs. Do wpisania: **{_l(widoki.get('do_wpisania', 0))} linii `PL:`** "
        f"(razem w pakiecie **{_l(liczby.get('do_wpisania', 0))}**)."
    )
    add(f"{next_step + 1}. Pod każdym tekstem chińskim są linie `EN:` (angielska wersja gry jako odniesienie) i `PL:` — **polski wpisujesz po `PL:`**.")
    add(f"{next_step + 2}. Odsyłasz pliki **tak jak są** (może być zip). Nie zmieniasz nazw plików, linii `klucz:` ani tekstu chińskiego.")
    add("")
    add("## 1. Jak wygląda jeden element")
    add("")
    add("```text")
    add("14. [Kwestia — 红线 (Ruby)] 造成#Y{0}#E点伤害\\n持续三息。")
    add("   klucz: 693cf29aef2cf70a")
    add("   tokeny: zachowaj dokładnie: #Y, {0}, #E")
    add("   EN: Deals #Y{0}#E damage\\nfor three breaths.")
    add("   PL:")
    add("```")
    add("")
    add("- Pierwsza linia: numer, rodzaj elementu z mówcą albo polem gry w nawiasie i **tekst chiński**.")
    add("- `klucz:` — po tej linii narzędzia znajdują tekst w grze. Nie zmieniaj jej.")
    add("- `tokeny:` — kody gry, które muszą zostać w przekładzie dokładnie takie same (punkt 2.4).")
    add("- `limit:` (tylko w widokach) — orientacyjna długość, punkt 3.")
    add("- `dotyczy:` (tylko w widokach) — nazwa rzeczy, której dotyczy opis (np. nazwa przedmiotu przy jego opisie).")
    add("- `EN:` — angielska wersja gry. Pomaga w nazwach i terminach, ale tłumaczymy z chińskiego.")
    add("- `PL:` — tu wpisujesz polski, w tej samej linii co znacznik.")
    add("- `\\n` w tekście to **przejście do nowej linii** w grze. W polskim wstaw `\\n` tam, gdzie ma być nowa linia.")
    add("")
    add("## 2. Zasady")
    add("")
    add("1. **Piszesz tylko po `PL:`.** Linie nad `PL:` są nienaruszalne.")
    add("2. **Nie zmieniasz numerów, kolejności ani linii `klucz:`.**")
    add("3. **Cały przekład jednego elementu stoi w jednej linii po `PL:`.** Nowa linia w grze to `\\n` wpisane w tekst, nie Enter.")
    add(
        f"4. **Nie tłumaczysz kodów gry** — zostają dokładnie takie, jakie są. Najczęstsze: {top_tokens}. "
        "Linia `tokeny:` pod elementem wylicza wszystkie kody tego elementu. `#Y…#E` to kolor (początek i koniec), "
        "`{0}`, `{}`, `%s`, `%d` to miejsca, w które gra wstawia liczbę albo nazwę, `$T(…)` to wartość wyliczana przez grę. "
        "W odnośniku `<nazwa|780|#C|15>` tłumaczysz tylko `nazwa`; część od pierwszej kreski `|` do `>` zostaje bez zmian."
    )
    add("5. **Jedna nazwa — jedna pisownia** w całym pakiecie. Imiona i nazwy ustalasz w `widoki/00_postacie_*.md`, `03_przedmioty_*.md`, `05_swiat_i_miejsca_*.md` i tak samo piszesz je w dialogach.")
    add("6. Spacje na początku i końcu tekstu dopisują narzędzia — nie musisz ich odtwarzać.")
    add("")
    add("## 3. Długość tekstu")
    add("")
    add(
        "**W danych gry nie ma limitów długości pól i nie zostały one zmierzone w grze.** Dlatego pakiet podaje tylko to, "
        "co da się policzyć:"
    )
    add("")
    add(
        f"- **Kwestie w scenach** nie mają linii `limit:`. Trzymaj się długości wersji angielskiej: połowa angielskich kwestii "
        f"ma do {_percentyl(lengths, 0.5)} znaków, 95% do {_percentyl(lengths, 0.95)}, 99% do {_percentyl(lengths, 0.99)}, "
        f"najdłuższa {lengths[-1] if lengths else 0}."
    )
    add(
        "- **Widoki:** `limit: do N znaków`, gdzie `N` to długość najdłuższego tekstu angielskiego **w tym samym polu gry** "
        "(np. we wszystkich nazwach przedmiotów). To wiadomość „tyle gra na pewno wyświetla w tym polu”, a nie pomiar okna. "
        "Przy wątpliwości wybierz krótszy wariant."
    )
    add("- Jeśli w grze coś się nie zmieści, właściciel zgłosi to i dostaniesz poprawioną listę — bez zgadywania z góry.")
    add("")
    add("## 4. Polskie znaki i interpunkcja")
    add("")
    add(
        "Pisz normalną polszczyzną z `ą ć ę ł ń ó ś ź ż`. **Nie sprawdzono jeszcze w grze, czy jej czcionki mają wszystkie "
        "polskie znaki** — to zadanie dla narzędzi i pierwszego testu w grze, nie dla tłumacza. Chińskie znaki interpunkcyjne "
        "(`，。！？“”「」……`) zamieniaj na polskie odpowiedniki; wielokropek `……` to zwykłe `...`."
    )
    add("")
    add("## 5. Elementy bez `PL:`")
    add("")
    add("- `(powtórzenie elementu N — nie wpisuj tu nic)` — ten sam tekst jest wyżej w tej samej scenie.")
    add("- `(powtórzenie — tłumaczysz raz: plik, scena N, element M)` — ten sam tekst ma swoje `PL:` we wskazanym miejscu; przekład dziedziczy się sam.")
    add("- `PL (już jest): …` — tekst został już przetłumaczony; pokazany dla kontekstu.")
    if not pelny:
        add("- `(tekst z wcześniejszego pakietu — tu nic nie wpisuj)` — stary tekst pokazany dla kontekstu nowej kwestii.")
    add("- `EN: (brak wersji angielskiej w grze)` — tłumaczysz z chińskiego jak resztę.")
    add("- `EN: (to jest tekst źródłowy — chińskiej wersji nie ma w danych)` — najnowsze teksty gry mają na razie tylko wersję angielską; pierwsza linia elementu jest wtedy po angielsku i z niej tłumaczysz.")
    add("")
    add("## 6. Bohater i bohaterka")
    add("")
    add(
        f"Gracz wybiera płeć postaci. Dane gry mają dla części kwestii **osobne tory dla bohatera i bohaterki** — "
        f"takich kwestii jest {_l(numery['kwestii_zaleznych_od_plci_bohatera'])}. Mają w etykiecie `wariant: bohater` albo "
        "`wariant: bohaterka` i klucz zaczynający się od `@` (osobne miejsce w grze dla każdej wersji), więc możesz — "
        "i powinieneś — użyć właściwego rodzaju („zrobiłem” / „zrobiłam”), także gdy tekst chiński obu wersji jest jednakowy. "
        "Dotyczy to też kwestii innych postaci w takich torach: zwracają się do mężczyzny albo do kobiety. "
        "Jeśli polskie zdanie brzmi jednakowo w obu wersjach, wystarczy wpisać je przy jednym wariancie — drugi wariant "
        "tego samego tekstu chińskiego, zostawiony pusty, odziedziczy przekład."
    )
    add("")
    add(
        f"Pozostałe kwestie gracza ({_l(mowcy.get('gracz', 0))}) i kwestie skierowane do niego są **wspólne dla obu płci**. "
        "Jeśli polskie zdanie wymaga rodzaju, wybierz formę neutralną: czas teraźniejszy, bezokolicznik, konstrukcję bezosobową "
        "(„Udało się”, „Trzeba iść”). Nie zgaduj płci — błędny rodzaj jest gorszy niż zdanie neutralne."
    )
    add("")
    add("## 7. Mówcy")
    add("")
    add(
        f"Każda kwestia ({_l(numery['kwestii'])}) leży w danych gry w grupie jednego mówcy — przypisanie jest odczytane "
        f"z budowy sceny, nie zgadywane z treści (kwestii bez grupy mówcy: {pokrycie['kwestii_bez_grupy_mowcy']})."
    )
    add("")
    add(f"- `gracz` — postać gracza ({_l(mowcy.get('gracz', 0))} kwestii).")
    add(f"- `红线 (Ruby)` — nazwa z gry: z tabliczki nad postacią albo z samej sceny ({_l(mowcy.get('nazwa_z_gry', 0))} kwestii). W nawiasie wersja angielska.")
    add(
        f"- `江湖人*` — **gwiazdka**: gra nie ma dla tego mówcy nazwy na ekranie; to robocza etykieta twórców ({_l(mowcy.get('etykieta_robocza', 0))} kwestii). "
        "Jeśli taki sam chiński napis jest w grze nazwą postaci, w nawiasie stoi jej wersja angielska. Etykiety się nie tłumaczy — służy do rozpoznania, kto mówi."
    )
    add(f"- `???` — mówca bez nazwy i bez etykiety ({_l(mowcy.get('bez_nazwy', 0))} kwestii).")
    add("- W nagłówku sceny `uczestnicy:` wymienia mówców z tytułem i opisem postaci z danych gry (jeśli gra je ma), a `obecni bez kwestii:` — postacie, które w scenie są, ale nic nie mówią.")
    add("")
    add("## 8. Kolejność scen")
    add("")
    add(
        "Gra nie ma jednej listy „scena po scenie”. Kolejność w `sceny.zip` wynika z danych gry, od najmocniejszych "
        "do najsłabszych (szczegóły i liczby: `spis-scen.md`):"
    )
    add("")
    add(
        f"1. **Zadania.** Tabela zadań wskazuje dialogi wprost, a zadania tworzą łańcuch poprzedników. Pliki `NN_watek-glowny_…` "
        f"to wątek główny po rozdziałach, dalej pozostałe rodzaje zadań (każdy rodzaj w osobnej serii plików). "
        f"Scen w plikach zadań: {_l(uklad['scen_w_zadaniach'])}, w tym w wątku głównym {_l(main_scenes)}."
    )
    add(
        f"2. **Numeracja.** {_l(uklad['w_tym_wg_numeracji'])} z tych scen nie ma własnego wpisu w tabelach zadań; stoją za sceną, "
        "z którą sąsiadują numerem w tym samym projekcie. W nagłówku jest wtedy napisane `brak wpisu w tabelach zadań — scena ułożona "
        "według numeru`. To kolejność z numeracji gry, nie stwierdzone powiązanie z zadaniem."
    )
    add(f"3. **`80_dialogi-wg-projektow_NN.md`** — {_l(uklad['scen_wg_projektow'])} scen bez żadnego wpisu zadania, według projektu (pliku roboczego twórców) i numeru.")
    add(f"4. **`90_rozmowy-tla_NN.md`** — {_l(uklad['scen_tla'])} scen wskazywanych tylko przez rozmieszczenie NPC w świecie: pogawędki, powitania, reakcje. Pogrupowane według miejsca.")
    add("")
    add(
        "**Kolejności nie sprawdzono w grze.** Łańcuch zadań pochodzi z danych i w wątku głównym jest spójny "
        f"(żadne zadanie nie stoi przed swoim poprzednikiem; w całej grze {uklad['przerwanych_cykli_lancucha_zadan']} razy łańcuch zamykał się w pętlę "
        "i został przerwany), ale część scen fabularnych wywołują skrypty, których w plikach tabel nie ma — te sceny trafiły do punktu 2 albo 3."
    )
    add("")
    if cut_serie:
        add("## 8a. Sekcja cutscen (`cutsceny.zip`)")
        add("")
        add("Napisy cutscen, filmy i plansze przerywników zostały zebrane w osobnym archiwum z zachowaniem kolejności ciągów i kontekstu:")
        add("")
        out.extend(_tabela_serii(cut_serie, sceny=False))
        add("")
        add(
            "- `01_napisy_cutscen_NN.md` — napisy z zakresu `text_msg 590000–592694` pogrupowane według ciągów ID i nagrań audio (`vo_*`), "
            "z wyraźnie oznaczonym **PROLOGIEM** (`590291–590459`), podpowiedzią mówcy, identyfikatorem nagrania i parami bohater/bohaterka."
        )
        add("- `02_intro_i_filmy_*.md` — intro gry (`wds_oneday_intro_cutscene_data`) oraz napisy filmowe ze znacznikami czasu.")
        add("- `03_plansze_i_streszczenia_*.md` — powtórki cutscen w dzienniku (`task_cutscene_replay`) z powiązaniem do zadania i pozostałe plansze `cutscenes`.")
        add("")
    add("## 9. Widoki")
    add("")
    add("Każdy tekst spoza scen stoi przy tabeli i polu gry, z którego pochodzi (`[tabela · pole · wiersz]`). Podział na pliki:")
    add("")
    out.extend(_tabela_serii(manifest["widoki"], sceny=False))
    add("")
    add(
        f"`10_bez_zrodla` to teksty, które są w mapie tekstów gry, ale nie wskazuje ich żadna odczytana tabela ani scena "
        f"({pokrycie['procent_id_en_ze_zrodlem']}% identyfikatorów tekstu ma wskazane źródło). Nie wiadomo, gdzie gra ich używa — "
        "przekład jest potrzebny, kontekstu brak."
    )
    add("")
    add("## 10. Co odsyłasz")
    add("")
    add("Te same pliki `.md` z wypełnionymi liniami `PL:` — wszystkie albo tylko te, nad którymi pracowałeś. Może być zip. "
        "Puste `PL:` znaczy „jeszcze nie przetłumaczone” i niczego nie psuje; można odsyłać partiami.")
    add("")
    add("## 11. Czego w pakiecie nie ma")
    add("")
    add(
        f"- {_l(numery['id_tylko_zh_niewskazane_pominiete'])} identyfikatorów tekstu, które istnieją tylko w chińskiej mapie i których nie wskazuje "
        "żadna tabela ani scena — klient zachodni nie ma dla nich żadnej wersji językowej, więc ich nie wyświetla."
    )
    if wykl:
        opis_wykl = {
            "boty_nicki": "losowych nicków botów/graczy (`text_msg` 3220000–3269999)",
            "tabele_meta": "wpisów z tabel meta/UI/samouczków/sterowania/klawiszy/QTE/ustawień/komunikatów programisty (zostają po angielsku)",
            "stare_grey_cutsceny": "przestarzałych wariantów `__grey` z zakresu cutscen 590000–592694",
            "placeholdery_testy": "placeholderów i napisów testowych",
            "promo_beta_cn": "chińskich komunikatów beta, NDA i promocji WeChat/WeCom",
            "bledy_sieciowe": "komunikatów błędów sieciowych, serwera i logowania",
        }
        for key, count in sorted(wykl.items(), key=lambda item: -item[1]):
            add(f"- {_l(count)} {opis_wykl.get(key, key)}.")
    add(f"- {_l(numery['scen_bez_tekstu'])} dialogów bez żadnego tekstu (same animacje i dźwięk).")
    add("- Tekstów zaszytych w grafikach, filmach i w samym programie gry.")
    add("")
    add("Błędy i braki zgłaszaj z nazwą pliku i numerem sceny albo elementu — po numerze dialogu i kluczu da się dojść do danych gry.")
    return "\n".join(out) + "\n"
