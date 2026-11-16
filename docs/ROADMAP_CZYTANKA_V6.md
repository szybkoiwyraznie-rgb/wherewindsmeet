## Wspólne dla B i C: mapa identyfikatorów tekstów — **zrobione**

W danych gry nazwy to **liczby**, nie tekst: `equip_items.name`,
`active_interact_way.button_name`, `curio_owner.owner_name`. Treść leży
w mapach języka (`locale/translate_words_map_zh_cn` + `_diff`, `_en`), a klucz
przekładu to SHA-256 z **tekstu źródłowego** (`tools/mapa_tekstow.klucz`).
Droga jest więc taka:

    identyfikator -> tekst chiński -> klucz -> polski przekład z `tlumaczenie/`

`tools/nazwy_z_map.py` robi z tego mały plik `index/nazwy.jsonl` (10 557
wpisów, 956 KB) — **tylko** identyfikatory, których naprawdę używa czytanka
(`index/poi.jsonl`, `index/pamiatki.jsonl`), a nie 1,8 mln wpisów mapy.
Czytanka czyta go w `_tekst_nazwy()`: najpierw mapa (zna każdy identyfikator),
potem świadkowie `index/teksty_*.jsonl` (znają tylko to, co trafiło do wyciągu).
Bez tej mapy 7 294 POI i 22 pamiątki zostawały bez nazwy.

## B. Brakujące przedmioty i pamiątki — **zrobione**

**Zbiory (2026-11-14).** Sekcje 03 `# Zbiory i pamiątki — zasłyszane historie`
i `# Zbiory i pamiątki — karty przeciwników`: **1 020 kart**, para „tytuł +
pełny tekst” z jednego wiersza gry (`region_collect_jianwen_data`,
`card_collecting_boss`), a bez przekładu — z gwiazdką (\\*).

**Pamiątki.** Trzymają je cztery tabele `curio_*` (nie `collect_*`, jak
zgadywaliśmy wcześniej):

| tabela | co daje |
|---|---|
| `curio_config` (120 wierszy) | `stuff_id`, `owner_id`, `history_id` (motyw), `history_order`, `memory` (klucz wiersza `text_msg` z opowieścią), `dialog_id`, `location` |
| `curio_owner` (88) | `owner_name` (identyfikator tekstu) i `owner_icon` — `head_npc_zhuxiannpc_jiangwulang`, stąd „JiangWulang” |
| `curio_theme` (56) | `history_name`, `history_order` |
| `equip_items` | `name` + `describe_str` |

Wiersz `curio_config` 35 to dokładnie karta właściciela: `stuff_id` 1100010
(„Stara włócznia”), `owner_id` 1 (Jiang Wulang), `memory` **741036** — ten sam
`text_msg`, o którym pisało archiwum.

`tools/pamiatki_z_bazy.py` zapisuje z tych tabel **same liczby**
(`index/pamiatki.jsonl`: `przedmiot`, `nazwa_id`, `wlasciciel_id`, `pamiec`),
`index/nazwy.jsonl` daje treść nazw, a `czytanka_czysta._pamiatki()` stawia
w 03 sekcję `# Pamiątki — przedmioty z historią`: tytuł **„właściciel —
przedmiot”** i cała opowieść. Wychodzi **120 pamiątek, 0 bez nazwy**. Przykład
z pliku:

    **Jiang Wulang — Stara włócznia**

    \\*When Jiang Wulang passed the blacksmith's shop, he pretended to buy…

**Czego nie ma i nie zmyślamy.**
- Przekładu opowieści pamiątek: **0 ze 120** — wszystkie idą z gwiazdką.
- Nazwy „QinghePast-At Heaven's Pier 1”: takiego tekstu nie ma w danych gry
  (przeszukane `local/dane` i 28 727 tabel ze schematem) ani w przekładzie.

## C. POI w czytance — **zrobione (2 948 w 03, 368 z numerem sceny)**

POI to wiersze `active_interact_way`: nazwa w `button_name` (identyfikator
tekstu), a numer sceny **tylko tam, gdzie gra go zapisuje** (`play_dialog_no` /
`result_play_dialog`). `tools/poi_z_bazy.py` → `index/poi.jsonl` (10 368
wierszy, 1 368 z numerem sceny), `index/nazwy.jsonl` → treść nazwy.
`czytanka_czysta._poi()` daje w 03 sekcję `# Punkty na mapie (POI)`:
`**Nazwa** — scena N`, a bez dowodu samo `**Nazwa**`.

- **2 948** haseł (tyle jest różnych nazw; powtórzone nazwy nie dublują tekstu),
- **368** z potwierdzonym numerem sceny,
- **11** POI zostało bez nazwy — ich identyfikatora nie ma w mapach języka
  (licznik `poi_bez_nazwy` w README).

**„Dragon Pattern Mark” jest w 03** (i „Dragon Pattern Contraption” też), ale
z gwiazdką: klucz `b86a976ba200e189` (龙纹标记) **nie ma polskiego przekładu**.
Numeru sceny ten POI nie ma: w wierszu jest tylko
`interact_storyline: client/dialogs/hjt/sxd_longwenbiaoji.etsb`. Nazwa pliku
pasuje do „longwenbiaoji” = 龙纹标记, ale to nie dowód liczbowy — POI stoi bez
numeru, dopóki nie będzie pliku klienta `.etsb` (tabeli „ścieżka → numer
dialogu” nie ma: przeszukane wszystkie 28 727 tabel ze schematem, jedyne
trafienie to sam wiersz tego POI).

## D. Scena → następna scena — **nie da się udowodnić z zebranych danych (zamknięte)**

Właściciel podał następstwo **4700001 → 4700041 → 4700352**. Sprawdzone
wszystko, co mamy, i następstwa w tym nie ma:

1. **Kolumny.** W 28 727 tabelach ze schematem nazwy `dialog`/`scene`/`story`/
   `task`/`quest` mają **jedną** kolumnę z „next”: `cutscenes.
   keep_camera_for_next_cutscene` (kamera, nie fabuła).
2. **Drzewo sceny.** `dialog_timelines.4700001` (wiersze `timeline`,
   `dialog_config`, `project_info`, `used_sound_bnk`) nie zawiera **ani razu**
   liczb 4700041 ani 4700352. `dialog_config` ma tylko `dialog_no`.
3. **Cała baza.** Przeszukane wszystkie tabele: **żaden wiersz** nie zawiera
   dwóch z tych trzech numerów, a 4700041 i 4700352 występują w bazie wyłącznie
   jako identyfikatory **encji / kitów / npc** (`entity_marker.npc_no`,
   `spawn_kit.kit_serial_id`, `strongpoint_info.enemy_entity_id`) — nie jako
   sceny.
4. **Zadania.** 4700001 jest w bazie tylko jako `finish_dialogs` zadań
   220003 i 10000220003 (grupa 1). 4700041 i 4700352 w żadnym zadaniu nie
   występują.

Wniosek: następstwo leży w **plikach klienta** (`.etsb`, `client/dialogs/…`),
których nie zbieramy, i nie da się go odtworzyć z tabel gry. Zgodnie z zasadą
„co nieudowodnione, mówimy wprost” **nie łańcuchujemy scen na oko**: trzy sceny
stoją tam, gdzie je stawia porządek gry (sekcja 燕南), a w `01` są osobnymi
jednostkami. Jeśli właściciel dostarczy pliki `.etsb` (albo zgodzi się
potraktować nazwę pliku scenariusza jako dowód), D wróci do pracy.

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
