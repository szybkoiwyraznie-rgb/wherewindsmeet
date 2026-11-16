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
| B | brakujące przedmioty i pamiątki („Stara włócznia”, „QinghePast-At Heaven's Pier 1”) | są (`index/teksty_*.jsonl`, tabela 4735) | nie | 2 |
| C | POI w czytance („Dragon Pattern Mark”) | są nazwy (`index/teksty_b.jsonl`, tabela 39) | tak — powiązanie POI → scena | 3 |
| D | scena → następna scena (4700001 → 4700041 → 4700352) | częściowo (`index/kolejnosc_*.jsonl`) | prawdopodobnie tak | 4 |
| E | kwestie po angielsku w scenach, które w grze są po polsku | nie (tekst jest tylko zh+en) | tak — pliki `locale` z gry | 1 (blokada: 1 odpowiedź) |

## A. Porządek questów w 03

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

## B. Brakujące przedmioty i pamiątki

**Objaw.** „JiangWulang-Stara włócznia / QinghePast-At Heaven's Pier 1” nie ma
w czytankach pełnej karty. Nazwa „Stara włócznia” w 03 jest, ale opis z jej
karty — nie.

**Co wiadomo.** Tekst jest w indeksie: `index/teksty_9.jsonl`, wpis
`[4735, "741036"]`, `zh` + `en` („When Jiang Wulang passed the blacksmith's
shop, he pretended to buy the spear on a whim…”). W `out/czytanka/*.md` tego
tekstu nie ma. Tabela 4735 to największa tabela tekstowa w indeksie
(103 975 wpisów) — leżą w niej opisy pamiątek, przedmiotów i zbiorów.

**Brakuje.** Rozpoznania, które kolumny tabeli 4735 (i sąsiednich) trzymają
nazwę, a które opis, oraz klucza łączącego parę nazwa–opis.

**Plan.**
1. Rozpoznanie z indeksu: dla tabeli 4735 zebrać pary „krótki tekst = nazwa”
   / „długi tekst = opis” po wspólnym rekordzie; sprawdzić, ile par da się
   złożyć („Stara włócznia” musi wyjść jako pierwsza).
2. Nowa sekcja 03 „Przedmioty i pamiątki”: `**Nazwa:** opis`, bez punktora,
   sortowanie krainą, potem nazwą.
3. Jeśli rekord ma witness w scenie albo cutscenie — karta idzie do 02 przy tej
   jednostce, a w 03 zostaje tylko odsyłacz (bez duplikatu tekstu).

**Kryterium.** Karta „Stara włócznia” (JiangWulang) jest w czytance z pełnym
opisem; żaden opis nie występuje dwa razy; liczba par policzona i podana
w README czytanki.

## C. POI w czytance

**Objaw.** „Dragon Pattern Mark” nie występuje w żadnym pliku czytanki.

**Co wiadomo.** Nazwa jest w indeksie: `index/teksty_b.jsonl`,
`{"zh":"龙纹标记","en":"Dragon Pattern Mark","w":[39,"200046001"]}` — tabela 39,
rekord `200046001`. Jest to rekord POI, który w grze startuje scenę 4700001.
W `out/czytanka/` ani razu.

**Brakuje.** Kolumny z tabeli 39, która mówi „ten POI startuje scenę N” —
w indeksie są tylko teksty, nie powiązania.

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
albo dowodu, że następstwo wynika z numeracji (do sprawdzenia: czy 4700041 i
4700352 sąsiadują w tej samej grupie zadania i czy łańcuch da się odtworzyć
z `grupy_zadan` + numerów scen).

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

## E. Angielskie kwestie w scenach, które w grze są po polsku

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
