# Roadmapa Czytanek — v6

Pięć braków zgłoszonych 2026-11-14 przez właściciela, rozpisanych na zadania.
Każde ma: objaw, co już wiadomo z danych w repozytorium, czego brakuje, plan
i kryterium akceptacji. Kolejność: najpierw to, co da się zrobić bez nowych
danych (A, B, C — same nazwy), potem to, co wymaga tabel z bazy gry (D, C —
powiązania) i wyjaśnienia źródła polszczyzny (E).

Zasada bez zmian: wchodzi tylko to, co udowodnione; reszta jest oznaczona jako
nieudowodniona, nigdy nie zmyślona.

## Skrót

| # | temat | dane w repo | nowe dane | kolejność |
|---|---|---|---|---|
| A | questy w 03 w kolejności łańcucha, nie alfabetycznie | są (`index/grupy_zadan.jsonl`) | nie | 1 |
| B | brakujące przedmioty i pamiątki („Stara włócznia”) | są — 1 020 kart zbiorów + 98 pamiątek z tabel `curio_*` | nie | **zrobione** |
| C | POI w czytance („Dragon Pattern Mark”) | są nazwy (`active_interact_way.button_name`); baza gry leży w `local/dane` | nie — trzeba tylko znaleźć powiązanie POI → scena | 3 |
| D | scena → następna scena (4700001 → 4700041 → 4700352) | częściowo: 5 765 scen ma pole `x`; baza gry w `local/dane` | nie — trzeba znaleźć następstwo w grafie dialogu | 4 |
| E | kwestie po angielsku w scenach, które w grze są po polsku | **tak** — przekłady są w `tlumaczenie/pl_warianty.jsonl` | nie | **zrobione** |

## A. Porządek questów w 03 — **zrobione**

Stan: `tools/kolejnosc_zadan.py` + sekcja w `tools/czytanka_czysta.py`; testy
w `tests/test_kolejnosc_zadan.py`. Kolejność: wątek główny (typ 1) w kolejności
sekcji z `tools/uklad_scen.py`, potem łańcuchy poboczne, na końcu pojedyncze
zadania pogrupowane krainą. Treść bez zmian: 75 331 jednostek, 62 838 pozycji
w reszcie — zmieniła się tylko kolejność linii w sekcji.

**Objaw.** W `03_reszta.md` sekcja „Zadania i wątki” (od linii 49539) jest
posortowana po nazwie, więc łańcuch główny czyta się alfabetycznie. Ma być po
kolejności: rozdział → kraina → quest → etap.

**Co wiadomo.** `index/grupy_zadan.jsonl` ma 1 077 grup; każda ma `kolejnosc`
(1, 2, …), `start`, `koniec` (lista id zadań zamykających) i `zadania` (lista
wszystkich id w grupie, w kolejności z gry — pierwszy wpis grupy 1 to `200246`,
`start` = `220001`). Tytuły grup i zadań są w grupach jako sloty-hashe do
`index/` (`tytul`, `numer_tytulu`), więc nazwy da się odczytać bez bazy.

**Brakuje.** Jawnego „to zadanie po tamtym”. Ale lista `zadania` w grupie jest
uporządkowana i `start`/`koniec` dają początek i koniec grupy — to wystarcza,
żeby zbudować łańcuch w obrębie grupy. Między grupami porządek daje
`kolejnosc`.

**Plan.**
1. `tools/kolejnosc_zadan.py`: grupa → lista zadań w kolejności gry (z `zadania`,
   z pilnowaniem, żeby `start` był pierwszy i `koniec` ostatni), plus nazwa grupy
   i numer tytułu z `index/`.
2. W budowniczym czytanek sekcja „Zadania” sortuje: najpierw grupy główne
   (rozpoznane po tytule/rozdziale), potem łańcuchy poboczne, na końcu
   pojedyncze zadania — pogrupowane krainą, tak jak teraz.
3. Test regresyjny: kolejność z przykładu właściciela (Rozdział pierwszy →
   „Heaven Has No Pier” → Qinghe → „Znów przyleciała jaskółka” → „Obudzone
   wspomnienia”) musi wyjść dokładnie w tej kolejności.

**Kryterium.** Żadna grupa w 03 nie jest posortowana alfabetycznie; łańcuch
z przykładu wychodzi po kolei; zadania spoza grupy zostają w sekcji pobocznej
według krainy.

## B. Brakujące przedmioty i pamiątki — **zrobione**

**Co zrobiono (2026-11-14).** Nowa sekcja 03 `# Zbiory i pamiątki — zasłyszane
historie` i `# Zbiory i pamiątki — karty przeciwników`: **1 020 kart**, para
„tytuł + pełny tekst” z jednego wiersza gry (`region_collect_jianwen_data`:
`jianwen_title` + `jianwen_text`; `card_collecting_boss`: `card_name` +
`card_content`), a bez przekładu — z gwiazdką (`\*`), tak samo jak kwestie
w 01.

**Pamiątki — rozwiązane 2026-11-14, gdy cała baza gry leży w `local/dane`.**
Pamiątki trzymają cztery tabele `curio_*` (nie `collect_*`, jak zgadywaliśmy):

| tabela | co daje |
|---|---|
| `curio_config` (120 wierszy) | `stuff_id` (przedmiot), `owner_id`, `history_id` (motyw), `history_order`, `memory` (klucz wiersza `text_msg` z opowieścią), `dialog_id` (scena, gdy jest), `location` |
| `curio_owner` (88) | `owner_name` (tekst) i `owner_icon` — `head_npc_zhuxiannpc_jiangwulang`, stąd „JiangWulang” |
| `curio_theme` (56) | `history_name` (tekst motywu) i `history_order` |
| `equip_items` | `name` + `describe_str` (nazwa i krótki opis przedmiotu) |

Wiersz `curio_config` 35 to dokładnie karta właściciela: `stuff_id` 1100010
(„Stara włócznia”), `owner_id` 1 (Jiang Wulang), `memory` **741036** — ten sam
wiersz `text_msg`, o którym pisało archiwum niżej, `history_id` 3,
`history_order` 1.

**Jak to weszło do czytanki.** `tools/pamiatki_z_bazy.py` czyta te tabele
i zapisuje **same liczby** do `index/pamiatki.jsonl` (120 wierszy). Nazwy
i opowieści dokłada `czytanka_czysta._pamiatki()` świadkami
`index/teksty_*.jsonl` (przestrzeń `equip_items.name` = 1496,
`curio_owner.owner_name` = 1167, `text_msg.content` = 4735) — ten sam
mechanizm co przy pozostałych zbiorach. Sekcja w 03 to
`# Pamiątki — przedmioty z historią`, tytuł **„właściciel — przedmiot”**
(`**jiangwulang — Stara włócznia**`), pod nim cała opowieść: przekład, a gdy go
nie ma — tekst z gry z gwiazdką. Wyszło **98 pamiątek**; 22 nie mają w wyciągu
nazwy przedmiotu, więc nie wchodzą, a licznik `pamiatki_bez_nazwy` w README
mówi, ile ich było.

**Czego nadal nie ma (i nie zmyślamy).**
- Przekładu opowieści pamiątek: **0 ze 120**. Wszystkie idą z gwiazdką.
- Nazwy „QinghePast-At Heaven's Pier 1”: takiego tekstu nie ma ani w danych gry
  (przeszukane 28 434 małych tabel i całe `local/dane`), ani w naszym
  przekładzie. „JiangWulang” występuje w grze tylko jako właściciel pamiątek
  i jako identyfikatory głosu (`vo_xsfb_jiangwulang_*` w `index/sceny_*.jsonl`).
- 6 pamiątek ma `dialog_id` (scena). To materiał dla C/D — patrz niżej.

## B. (archiwum) Objaw i dowody

**Objaw.** „JiangWulang-Stara włócznia” nie miało w czytankach pełnej karty.
Nazwa i krótki opis były w 03, opowieści nie było.

**Dlaczego wcześniej nie wyszło.** Wyciąg `index/` trzyma **teksty**, nie
referencje: `text_msg` wiersz 741036 ma `zh` + `en` („When Jiang Wulang passed
the blacksmith's shop…”), ale nic w indeksie nie mówiło, że należy do przedmiotu
1100010. Dopiero tabela `curio_config` z bazy gry daje ten klucz.

## C. POI w czytance

**Objaw.** „Dragon Pattern Mark” nie występuje w żadnym pliku czytanki.

**Co wiadomo.** Nazwa jest w indeksie: `index/teksty_b.jsonl`,
`{"zh":"龙纹标记","en":"Dragon Pattern Mark","w":[39,"200046001"]}` — tabela 39,
rekord `200046001`. Jest to rekord POI, który w grze startuje scenę 4700001.
W `out/czytanka/` ani razu.

**Brakuje.** Kolumny z tabeli 39, która mówi „ten POI startuje scenę N” —
w indeksie są tylko teksty, nie powiązania.

**Stan 2026-11-14 (baza gry jest już w `local/dane`).** Baza ma 114 925 tabel
i czyta się (`tools/baza_gry.py`), więc tabelę 39 można nazwać i przejrzeć bez
kolejnej paczki od właściciela. Do zrobienia w następnym kroku.

**Plan.**
1. Bez nowych danych: sekcja 03 „Punkty na mapie (POI)” — nazwa POI pogrupowana
   krainą, z liczbą POI.
2. Z nowych danych (jeden mały zakres zbieracza, tabela 39 i sąsiednie):
   kolumna „scena startowa” → POI trafia do 02 przy scenie, którą otwiera.
3. Oznaczenie: POI bez potwierdzonego powiązania stoi samo, bez strzałki do
   sceny — nigdy „na oko”.

**Kryterium.** Wszystkie POI z indeksu są w 03; te z potwierdzonym powiązaniem
są też w 02 przy swojej scenie.

## D. Scena → następna scena

**Objaw.** 4700001 → 4700041 → 4700352 to jedno następstwo; w czytance stoją
osobno, bez łącznika.

**Co wiadomo.** `index/kolejnosc_*.jsonl` opisują **skład** sceny (`s` =
numer sceny × 100 + numer kwestii, `d` = numer dialogu, `t` = czas), nie
następstwo. `index/chronologia.jsonl` daje tylko kolejność pozycji w pliku.
W repozytorium nie ma kolumny „następna scena”.

**Brakuje.** Tabeli z bazy gry (sceny/osi fabuły), która trzyma następstwo —
albo dowodu, że następstwo wynika z numeracji.

**Stan 2026-11-14 (baza gry w `local/dane`, 114 925 tabel).** Przeszukane
nazwy tabel z `dialog`/`scene`/`story`/`task` i kolumnami `next*`: jedyne
trafienie to `cutscenes.keep_camera_for_next_cutscene` (kamera, nie fabuła).
Czyli następstwo nie leży w kolumnie tabeli — jeśli jest, to w grafie dialogu
(`space` typu `对话-*.dialog`, skąd bierze się `index/sceny_*.jsonl`: węzły `o`,
krawędzie `e`). Do zrobienia: sprawdzić, czy krawędź grafu wskazuje numer
następnej sceny.

**Plan.**
1. Sprawdzić hipotezę „numeracja + grupa zadania wystarczą” na 20 parach scen
   z jednego zadania. Jeśli tak — bez nowych danych.
2. Jeśli nie — mały zakres zbieracza (kilka tabel `data*`, nie cała baza):
   kolumny `next`/`kolejna` z tabel scen.
3. W czytance: łańcuch jako sekcja „Ciąg dalszy” z odsyłaczem do numeru sceny;
   numeracja zostaje, żeby dało się wrócić.

**Kryterium.** Przykład właściciela (4700001 → 4700041 → 4700352) jest w
czytance jednym łańcuchem, a każdy skok ma dowód (pole z tabeli albo wpis
w grupie zadania).

## E. Angielskie kwestie w scenach, które w grze są po polsku — **zrobione**

**Przyczyna (potwierdzona na scenie 4700001).** Kwestie zależne od płci bohatera
mają w grze osobny identyfikator na każdy wariant, a wspólny klucz tekstu.
Magazyn trzyma je w `tlumaczenie/pl_warianty.jsonl` pod `id`, a indeks
(`index/warianty.jsonl`) wiąże `id` z kluczem tekstu i numerem wariantu
(1 = bohater, 2 = bohaterka). Czytanka czytała tylko `pl_X.jsonl` po kluczu,
więc **wszystkie kwestie gracza z wariantem płci wychodziły po angielsku**,
mimo gotowego przekładu. Tak było w całej scenie 4700001: 14 z 23 linii.

**Naprawa.** `tools/tlumaczenie.py`: `wczytaj(katalog, warianty=...)` dokłada
`po_kluczu_wariantow` (klucz tekstu → przekład), `przeklad()`/`ma()` sięgają do
niego, a `po_kluczu_pelny()` daje scalony słownik. Czytanka
(`tools/czytanka_czysta.py::_magazyn`) i `tools/pokrycie_tlumaczenia.py` podają
teraz ścieżkę `index/warianty.jsonl`. Czytamy **wariant bohatera** (mężczyzna,
zgodnie z decyzją właściciela); gdy rodzina go nie ma (21 z 180 przetłumaczonych
rodzin), bierzemy drugi dostępny wariant — lepszy polski z żeńską końcówką niż
angielski.

**Efekt.** Scena 4700001 jest w całości po polsku („Ten znak to…”, „Ostrożnie.”,
„Ciężka i ostra. Nie baw się nią.”). Kwestie bez przekładu: 160 912 → **160 751**;
linii w 01/02: 29 395 → **29 556**. Znika też fałszywy komunikat narzędzia
„BRAK przekładu → w grze po angielsku” dla tych kwestii.

**Co zostaje otwarte.** Ten sam błąd może siedzieć w innych miejscach, które
czytają magazyn bez `warianty=`: `tools/buduj_paczke.py`, `tools/buduj_czytanki.py`
(wydanie „pełne”), `tools/zbuduj_latke.py`. Trzeba przejść po kolei i sprawdzić,
czy nie gubią wariantów — to osobne zadanie, nie blokuje czytanki.

## E. (archiwum) Objaw i dowody

**Objaw.** W scenie 4700001 kwestie `\*This symbol...`, `\*Careful!` itd. są po
angielsku, a kwestie Ruby'ego po polsku. W grze — zdaniem właściciela — cała
scena jest po polsku.

**Co wiadomo.** Gwiazdka w czytance znaczy dokładnie „nie ma polskiego
przekładu w `tlumaczenie/`”. Sprawdzone dla tej sceny:
- tekst jest w indeksie jako `zh` + `en`, klucz `5eb6a0036634f83f`, dwa warianty
  (`index/warianty.jsonl`);
- w zwrotce tłumacza (`tlumaczenie/pl_*.jsonl`) tego klucza **nie ma**;
  sąsiednie kwestie Ruby'ego są (`693cf29aef2cf70a` → „O rety, to jakiś tajny
  znak?”).
Więc polszczyzna widziana w grze nie pochodzi ze zwrotki — musi być w plikach
gry (np. `translate_words_map_pl`) albo w innej łatce.

**Brakuje.** Faktu, skąd gra bierze polski tekst dla tych kwestii, oraz pliku
z tymi tekstami.

**Plan.**
1. Właściciel sprawdza (30 s): czy w czystej instalacji, bez naszej łatki, ta
   scena jest po polsku, i co leży w `Package/HD/oversea/locale/` oraz
   `LocalData/Patch/HD/oversea/locale/` (nazwy `translate_words_map_*`).
2. Jeśli jest mapa PL: dodać ją do wyciągu (`tools/mapa_tekstow.py`,
   `tools/wyciag.py`) i czytać polski jako pierwsze źródło — to może zamknąć
   większość z 160 912 kwestii z gwiazdką.
3. Jeśli mapa PL nie istnieje: mały zakres zbieracza na samo `locale/`
   (kilka MB) i ta sama droga.

**Kryterium.** Scena 4700001 jest w czytance w całości po polsku albo — jeśli
polskiego tekstu w danych gry nie ma — czytanka mówi to wprost w README,
a gwiazdki zostają tylko przy kwestiach realnie nieprzetłumaczonych.

## Wydania

- **v6**: A + B + C (same nazwy POI). Wchodzi bez nowych danych z gry.
- **v7**: D + C (powiązania) + E — po dostarczeniu tabel albo plików `locale`.
- Numeracja rośnie, jak dotąd; stare wydania z Dysku Google idą do kosza.
