# Baza danych gry: `MANIFEST` → `indexN` → `dataN`

Ustalone **2026-11-11** na plikach z `Package/HD/oversea` (dostawy z Dysku:
`oversea*.zip`, `index*.zip`, `patch.zip`). Narzędzie: `tools/baza_gry.py`.
To zastępuje wcześniejsze skanowanie plików `data*` „po wzorcach”: każdy rekord
gry da się teraz odczytać dokładnie, po nazwie tabeli i kluczu.

## Obraz całości

Pliki `MANIFEST`, `indexN` i `dataN` to jedna baza klucz → wartość:

```text
MANIFEST   lista tabel: nazwa → liczba wierszy + położenie indeksu
indexN     dla każdej tabeli tablica haszująca: klucz wiersza → położenie wartości
dataN      wartości (zserializowane obiekty)
```

Wszystkie trzy rodzaje plików używają tego samego kontenera co mapa tekstów
(`0xDEADBEEF`, wersja 1, tabela przesunięć, chunki zstd —
[LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)).

## `MANIFEST` (jeden chunk, po dekompresji ok. 15 MB)

```text
nagłówek 24 B : u16 1, u16 1, u32 8, u32 n_tabel, u32 n_części, u32 n_c, u32 n_d
nazwy         : (n_tabel + n_c + n_d) × [u16 długość, ASCII, dopełnienie do 8 B]
rekordy       : n_tabel × 32 B
części        : n_części × 8 B  (u16 plik indeksu, u16 chunk,
                                 u16 plik poprawek, u16 chunk poprawek; 0xFFFF = brak)
ogon          : u32 liczba + nazwy plików indeksu, u32 liczba + nazwy plików danych
```

Rekord tabeli (32 B): `u32 wiersze, u32 liczba_części, u16 plik_schematu,
u16 chunk_schematu, u16 plik_kolumn_dopisanych, u16 chunk_kolumn_dopisanych,
u32 hash, u32 0, u32 pierwsza_część, u32 flagi`.

- `plik_schematu = 0xFFFF` oznacza tabelę bez schematu kolumn.
- Części `pierwsza_część … +liczba_części` wskazują chunki indeksu z wierszami.
- `wiersze` to liczba wierszy **po nałożeniu poprawek** (patrz niżej).
- Flagi: bit `0x400` — klucze wierszy są liczbami (`u64`), bit `0x800` — klucze
  są napisami; bit `0x1` — tabela bez chunku schematu.
- Manifest z patcha (`LocalData/Patch`): 114 171 tabel z rekordem, 149 050
  części, oraz 284 + 163 767 nazw bez rekordu (głównie `spaces.*` i `maps.*`;
  ich znaczenie jest **niewyjaśnione** — nie mają położenia w tych plikach).
- Największe rodziny nazw z rekordem: `dialog_timelines.<numer>` 74 950,
  `spaces.*` 23 302, `new_graph_cues.*` 2 443, `maps.*` 1 582; razem 7 595
  różnych prefiksów.

## Warstwa aktualizacji (`index1001`, `index1200`, `data1001`, `data1200`)

Gra nie przepisuje dużych plików przy aktualizacji. Zmiany leżą w osobnych
plikach `1001` (tabele) i `1200` (dialogi, przestrzenie), a `MANIFEST` wiąże je
z plikami bazowymi na dwa sposoby:

1. **Poprawki wierszy.** Każda część tabeli może wskazać drugi chunk indeksu
   („chunk poprawek”) o tej samej budowie. Wiersz z chunku poprawek:
   - zastępuje wiersz bazowy o tym samym kluczu,
   - dopisuje nowy wiersz, jeśli klucza nie było,
   - **kasuje** wiersz bazowy, jeśli jego położenie to `plik 0, długość 0`.
2. **Kolumny dopisane.** Rekord tabeli może wskazać drugi chunk schematu.
   Pełna lista kolumn = kolumny bazowe + kolumny dopisane (numeracja ciągła).
   Przykład: `sound_data` dostała w ten sposób kolumnę `sea_text`.

Stan w dostawie z 2026-11-11: manifest bazowy ma 2 574 części z poprawkami
i 8 tabel z dopisanymi kolumnami; manifest z `LocalData/Patch` — 3 862 części
i 10 tabel. Wszystkie wskazują pliki `1001` albo `1200`.

To jest podstawa audytu aktualizacji: porównanie wierszy po nałożeniu poprawek
(a nie porównanie bajtów plików) mówi dokładnie, które rekordy gra zmieniła.

## Chunk indeksu

Dwa rodzaje:

1. **schemat**: `u16 liczba`, potem `liczba` × `[u16 długość, nazwa kolumny]`;
2. **wiersze**: ta sama tablica haszująca co w mapie tekstów — nagłówek 24 B
   (`u64 pojemność, u64 zajęte, u64 seed 0x608DDB2C`), bajty `ctrl`
   (`max(pojemność + 17, 24)`; `< 0x80` = zajęty slot), potem `pojemność` × 16 B.

Slot wiersza (16 B):

```text
klucz napisowy : u32 offset (od własnego pola), u32 długość   → napis w ogonie chunku
klucz liczbowy : u64 wartość
położenie      : u16 numer pliku danych, u16 chunk, u16 offset, u16 długość
```

**`offset` i `długość` są w słowach 8-bajtowych.** Wartości w chunku danych są
dopełniane zerami do 8 bajtów.

## Wartości w `dataN`

Wartość bez schematu to jedna zserializowana wartość z etykietą typu:

| tag | znaczenie |
|---|---|
| `0x01` `0x02` `0x03` `0x04` | u8, u16, u32, u64 |
| `0x06` | f64 |
| `0x08` | napis: `u16` długość w bajtach + UTF-8 |
| `0x09` | lista: `u16` liczba elementów |
| `0x0a` | obiekt lub słownik: `u16` **liczba elementów = 2 × liczba par**, potem pary klucz/wartość (klucz bywa napisem albo liczbą) |
| `0x0b` `0x0c` `0x0d` | None, False, True |

Wiersz tabeli **ze schematem** ma inną budowę: `u16 liczba_pól`, potem pola
`u16 (numer_kolumny | typ << 10)` + dane. Numer kolumny ma 10 bitów (tabele
mają ponad 256 kolumn), `typ` to ten sam tag co wyżej, a dane są kodowane jak
wartość z etykietą, tylko bez bajtu etykiety. Kolumn, których wiersz nie
wypełnia, po prostu w nim nie ma.

Bajt `0x28`, wzięty początkowo za osobny tag słownika, to po prostu starszy
bajt nagłówka pola (`0x0a << 2`). W strumieniu wartości nie występuje ani razu
(policzone na 3 670 355 wierszach: wszystkie tabele poza `spaces.*`, `maps.*`
i `new_graph_cues.*` oraz 3 000 losowych dialogów).

## Sprawdzenie na całej bazie (2026-11-11)

`python3 tools/baza_gry.py KATALOGI --sprawdz` czyta każdy wiersz każdej tabeli
i wymaga, żeby wartość skończyła się w swoim przedziale, a dopełnienie było
zerowe. Wynik na dostawach z Dysku (pliki bazowe + `LocalData/Patch`):

| miara | wynik |
|---|---|
| tabel w `MANIFEST` | 114 171 (28 261 ze schematem), 10 077 485 wierszy |
| tabel odczytanych bez błędu | **114 169**, 10 077 465 wierszy |
| nieznane tagi | 0 |
| tabel z inną liczbą wierszy niż w `MANIFEST` | **0** |
| tabel z błędem wartości | 2 (`0x00` w miejscu tagu) |

Dwie tabele z błędem to `spaces.s66027.spawn.spawn_sw_default_0`
i `spaces.s66027.spawn.spawn_sw_hg_usual_0` (rozmieszczenie obiektów w jednej
przestrzeni, bez tekstów). Przyczyna **niewyjaśniona**; dla pakietu tłumacza
bez znaczenia.

Pierwszy odczyt (bez warstwy aktualizacji) dawał 377 tabel z inną liczbą
wierszy i 113 792 tabele czyste. Po uwzględnieniu chunków poprawek i kolumn
dopisanych liczba wierszy zgadza się z `MANIFEST` w każdej tabeli — to jest
dowód, że opis warstwy aktualizacji powyżej jest poprawny.

### Aktualizacja po Patchu 2.4 (`2026-11-13`, build `26592996`)

Na pełnej paczce z Collector `1.3.0` (60 plików `Package/HD/oversea/` + `LocalData/Patch/HD/oversea/`):
- **114 925** tabel ma niepuste rekordy (w tym 3 nowe tabele mapy `maps.world_zizouqi_01_m.*` w patchu, a 1 stara `wuxue_fx_collect_reward` obecna tylko w pakiecie bazowym);
- **114 904** tabel czyta się bez błędu (0 nieznanych tagów);
- **21** pustych/wyzerowanych tabel rozmieszczeń `spaces.*` (8-bajtowe ładunki zerowe) zgłasza `nieznany typ 0x00` i jest odnotowanych wyłącznie w `manifest.json -> bledy` bez wpływu na teksty ani sceny;
- pojawiło się także 7 binarnych plików formuł RPG w `LocalData/Patch/HD/oversea/formula/*.ft` (brak napisów do tłumaczenia).

## Dialog = cztery pola jednej tabeli

Każdy dialog to tabela `dialog_timelines.<numer>` z czterema wierszami:

| klucz | treść |
|---|---|
| `dialog_config` | m.in. `dialog_no`, `id`, `is_skip`, `for_oversea`, `oversea_src_dialog_no` |
| `project_info` | `project_name` |
| `timeline` | `TimelinePObject` z torami, mówcami i kwestiami |
| `used_sound_bnk` | lista banków dźwięku |

W chunku danych leżą w tej kolejności: `dialog_config`, `project_info`,
`timeline`, `used_sound_bnk`.

### Wyjaśnienie „5 859 brakujących dialogów”

Pierwszy parser (`tools/timeline.py`, usunięty) wycinał scenę od znacznika
`TimelinePObject` do następnego i brał pierwsze `dialog_no` z tego wycinka.
Ponieważ `dialog_config` leży **przed** własnym `timeline`, wycinek zawierał
`dialog_config` **następnego** dialogu. Skutek: w pierwszym indeksie
(`wwm-indeks-v1`) numer i projekt każdej sceny należały do sceny następnej
w pliku. Potwierdzenie na tamtym indeksie:

| pomiar | wynik |
|---|---|
| zapisany `dialog_no` = `source_id // 100` **następnej** sceny | 62 726 z 62 746 par |
| zapisany `dialog_no` = `source_id // 100` własnej sceny | 0 z 62 602 |
| `source_id // 100` jest kluczem rejestru | 68 268 z 68 274 scen z tekstem |
| „brakujące” numery, które są numerem sceny już obecnej w indeksie | 5 506 z 5 859 |
| plik poprawki (numery skaczą o miliony): zgodność z następną sceną | 14 z 14 |

Wnioski oparte na tym numerze („5 871 scen bez `dialog_no`”, „`dialog_no` to
grupa”, przypisanie scen do projektów, 5 859 braków) były **artefaktem
parsera**, nie cechą danych. Dokumenty, które je opisywały (`SCENY_WWM.md`,
`ANALIZA_KORPUSU.md`), parser `tools/timeline.py` i zbudowany nim indeks zostały
usunięte 2026-11-12. Poprawne odczytanie: numer dialogu = nazwa tabeli
`dialog_timelines.<numer>`; czyta go `tools/sceny_z_bazy.py`.

## Tabele wiążące i warianty w grze

Wyciąg (`tools/wyciag.py`) łączy dialogi z resztą bazy przez następujące
tabele (szczegóły w kodzie oraz [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md)):

| tabela / pole | rola |
|---|---|
| `tasks` (`pre_task`, `post_task`, `pian_id`, `group_id`, `fetch_play_dialogs`, `finish_play_dialogs`, `finish_dialogs`, `fetch_dialogs_id`, `process_interact_param`, `finish_choice`, `get_task_choice`) | zadania, ich kolejność łańcuchowa oraz powiązania z dialogami |
| `task_group_info`, `task_types` | rozdziały (typ `1` = wątek główny, grupy `1`, `4`, `6`, `7` = rozdziały 1–4) i kolejność typów zadań; uwaga: `group_tasks` sortuje po numerze, nie po fabule (59 naruszeń kolejności w rozdz. 1) |
| `branch_data` (`ques_argue_no`), `npc_talk_options` | pytania z wyborami gracza, opcje rozmowy z NPC i następstwa dialogów |
| `spaces.*.entity` → `entity_init_data.billboard_data` → `entity_attr` | tłumaczenie `entity_no` mówcy na `npc_no`, imię/tytuł z tabliczki oraz opis postaci (`introduction` przez `attr_id`) |
| `world_view_person_info` (i powiązane `world_view_*`) | postacie w encyklopedii gry i ich historie |
| `space_info` / `spaces.*`, `cutscenes`, `plot_recap_data`, `dialog_replace*` | nazwy miejsc, plansze przerywników, streszczenia i podmiany dialogów |
| `EntityTextTrack`: `valid_for_specific_type` + `entity_type` (`1` / `2`) | kwestie zależne od płci bohatera (bohater / bohaterka) o osobnych identyfikatorach tekstu nawet przy wspólnym źródle chińskim |
| `debate_guider_dialog_data` | powtarza niemal wyłącznie kwestie scen (66 357 z 66 372 linii) — w pakiecie nie dubluje scen |

Skrypty wywołujące dialogi poza tabelami (`*.ets`, nazwy `storyline.*` bez
rekordu w bazie) nie leżą w tych tabelach; dlatego część scen fabularnych nie ma
bezpośredniego wskazania w `tasks`, a `oversea_src_dialog_no` (22 348 wpisów,
tylko 186 istniejących celów) nie nadaje się do wiązania kolejności.
