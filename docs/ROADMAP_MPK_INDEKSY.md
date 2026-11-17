# Roadmapa: trzy brakujące indeksy WWM (sceny → sceny, POI → sceny, osie `.cine`)

Stan: 2026-11-17. Plan na kolejne sesje, wykonywany **po kolei, bramka po
bramce**. Fakty o formacie i źródłach: [MPK_FORMAT_RESEARCH.md](MPK_FORMAT_RESEARCH.md).
Dotychczasowe ustalenia o kolejności i `.cine`: [CINE_KOLEJNOSC.md](CINE_KOLEJNOSC.md).

Cel: znaleźć w instalacji gry indeksy, które wiążą

1. **scenę → następną scenę** (`## Scena 4700001` → `## Scena 4700041` →
   `## Scena 4700352`),
2. **aktywację POI → start sceny** (np. „Dragon Pattern Mark" → `## Scena 4700001`),
3. **osie czasu `.cine`** — chronologię kwestii wewnątrz cutscen.

Pliki `Package/HD/oversea` i `LocalData/Patch/HD/oversea` ich **nie zawierają**
(sprawdzone: 75 007 tabel `dialog_timelines.*` bez znajomości scen `4700001`;
żadna tabela nie kluczuje numerem przerywnika; `cine_path` leży w `cutscenes`,
ale sama oś nie). Podejrzenie (a według właściciela również doświadczenie
z innych maszyn): indeksy są w **~200 `Resources*.mpk`** (+ ewentualnie
`LT*.mpk` / `Patch*.mpk`), których indeks leży w `./Resources.mpkinfo` i
`LocalData/Patch/*.mpkinfo` / `Patch.mpkdb`.

## Zasady stałe

- Skaner i wszelkie narzędzia **tylko czytają**; gra nie jest uruchamiana,
  proces nie jest dotykany; nic nie jest wysyłane do sieci.
- Duże dane (`*.mpk`, `*.mpkinfo`, `Patch.mpkdb`, wydobyte `.cine`/`.etsb`)
  **nie trafiają do Git** ([DATA_POLICY.md](DATA_POLICY.md)); do repo trafia
  kod, dokumentacja, wnioski i — jak dotąd — teksty/ścieżki.
- Każdą bramkę kończymy z dowodami: raport liczbowy + SHA-256 paczki +
  wpis w [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) i aktualizacja
  [STATUS.md](STATUS.md).
- Nie zgadujemy numerów ani powiązań; to, czego dane nie powiedzą, zostaje
  jawnie opisane jako niewiadoma.

## Bramka 0 — badania i przygotowanie kitu (wykonane 2026-11-17)

**Wejście:** publiczne źródła (GitHub/ResHax), `index/`, `docs/`.
**Wynik:**

- [x] [MPK_FORMAT_RESEARCH.md](MPK_FORMAT_RESEARCH.md) — co już wie świat
  (Zhincore/wwm-messiah-tools MIT, zamknięte narzędzie mohebbiaina, zakazany
  dest1yo/wwm_utils), format `.mpkinfo` v3, `Patch.mpkdb`, `file_id`,
  struktura bloków EZST/ZSTD/LuaText.
- [x] Pierwszy raport z sondy (`docs/MPK_SKANER_RAPORT.md`), uruchomienie
  właściciela na instalacji Steam — patrz bramka 1.

- [x] [MPK_FORMAT_RESEARCH.md](MPK_FORMAT_RESEARCH.md) — co już wie świat
  (Zhincore/wwm-messiah-tools MIT, zamknięte narzędzie mohebbiaina, zakazany
  dest1yo/wwm_utils), format `.mpkinfo` v3, `Patch.mpkdb`, `file_id`,
  struktura bloków EZST/ZSTD/LuaText.
- [x] `tools/mpk_skaner.py` — skaner (stdlib, bez sieci): inwentarz paczek,
  odczyt indeksów, statystyki offsetów, magia/entropia próbkowanych bloków,
  haszowanie kandydatów ścieżek (POI storyline z `index/poi.jsonl` + wzorce
  `.cine` z `cine_name`), `Patch.mpkdb` w trybie `mode=ro`.
- [x] `tools/build_mpk_skaner.py` + `collector`-analogiczny one-click
  `SKANUJ.bat` → `dist/WWM_MPK_Skaner_v1.zip`.
- [x] Testy jednostkowe/integracyjne na danych syntetycznych.

**Bramka jakości:** `python3 tools/run_tests.py` zielony,
`python3 tools/check_repository.py` OK, `git diff --check` czysty.

**Krok właściciela:** rozpakować `WWM_MPK_Skaner_v1.zip` poza grą, kliknąć
`SKANUJ.bat`, wybrać folder gry (albo przeciągnąć go na `.bat`); wynik
(`MPK_SKANER_WYNIK/…` + `WWM_MPK_Skaner_WYNIK.zip`, zwykle kilka MB) wysłać na
Dysk Google do folderu „Where Winds Meet". **Paczki `.mpk` nie wysyłamy.**

## Bramka 1 — raport z pierwszego uruchomienia (wykonane 2026-11-17)

**Wejście:** `WWM_MPK_Skaner_WYNIK.zip` od właściciela (`17 180 B`,
SHA-256 `0f80a219…`).
**Zadania (wykonane):**

1. Odczytano `RAPORT.json`: **489 `*.mpk` (211 GB, 158 kontenerów z
   `Resources.mpkinfo`, wszystkie istnieją, offsety fizyczne wszędzie)**.
   Brak „lite" paków; 24 kontenery z pokryciem > 100 % — do audytu.
2. Magia/entropia: raport próbkowania — do wykorzystania przy analizie EZST
   (klucz publiczny AES-ECB; dekodujemy po swojej stronie).
3. Trafienia: **14 × `.cine` z wzorca `e_01_cutscene/qhrw/...` — wszystkie
   w `Resources34.mpk`**; **0 trafień `.etsb`** (POI `storyline` to najpewniej
   cel skoku, nie plik VFS); LT1.mpk to paczka skryptowa (240 bloków),
   Patch3109/3110 = duże zasoby łatki, pomijany.
4. Decyzja: **bramka 2 — kit v2 wycina surowe bloki** (14 trafień + wszystkie
   240 bloków LT1.mpkinfo + zrzut `Patch.mpkdb` do JSON, bez dekodowania).

**Wynik:** `docs/MPK_SKANER_RAPORT.md` + wpisy w
[EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

## Bramka 2 — wycinarka `.cine` i `.etsb` (wykonana 2026-11-17, kit v4)

**Wejście:** ustalenia z bramki 1 (14 trafień `.cine` w `Resources34.mpk`,
240 bloków skryptowych `LT1.mpk`).
**Zadania (wykonane):**

1. [x] Kit: sonda + wycinanie SUROWYCH bloków (limity 64 MB/blok,
   512 MB łącznie) + `mpkdb_dump.json` (BLOB→hex w v3) + okno wyboru
   folderu gry tkinter w v4 (zamiast wpisywania ścieżki z palca).
2. [x] Przebieg właściciela na v3 → `WWM_MPK_Skaner_WYNIK (1).zip`
   (14/14 `.cine`, 240/240 Lua LT1, dump mpkdb OK).
3. [x] Dekodowanie EZST/LuaText (nasz `tools/mpk_artefakty.py`, publiczny
   algorytm MIT): 14/14 `.cine` OK; 240/240 Lua OK; format `.cine`
   opisany (magic `c1 59 41 0d`, u64le len, tabela identyfikatorów, oś
   czasu binarnie).
4. [x] Reguła VFS: **ścieżka = `LuaText/` + debug_source** — 240/240;
   zwalidowany nasz `file_id` (5/5 + 240/240).
5. [x] Artefakty pochodne commitowane: `index/mpk/` (+`README.md`),
   generator `tools/mpk_artefakty.py`.
6. [x] Kit **v4** na Dysku; właścicielski wynik: 8 066 kandydatów, 14
   trafień — wszystkie `.cine` pack-34, **0 trafień ścieżek POI/storyline**.
   Patch3109/3110 mają 22/24 wpisy w lokalnych indeksach, ale te bloki nie
   zostały wycięte w v4.
**Wynik:** pierwsze prawdziwe `.cine` na stole + raport dekodowania +
zwalidowany hashing indeksu.

## Bramka 2.5 — strukturalne bloki `hex_world` i grafy Storyline (2026-11-17)

**Wynik dotychczasowy:**

- 8 bloków `hex_world` z packów 7/8; w czterech z nich 14 200 wystąpień
  rekordów `Resource` (13 151 unikalnych 16-bajtowych GUID-ów). ID są binarne,
  nie tekstowe; 2 wystąpienia `POI` są przypadkowymi bajtami w identyfikatorach.
  Brak wspólnego klucza z tekstowymi GUID-ami `index/`.
- Dodany indeks pochodny `index/mpk/storyline_graphs.jsonl` (14 grafów) i
  generator `tools/index_storyline_graphs.py`. Znaleziony potwierdzony most
  Storyline → cutscene: `5_a31638d0356c7433` ma sekwencję `2560507` (dialog)
  → `32474` (cutscene `sq001_qzpk_male`, 10,5 s). Inny graf wiąże zadania
  380493/380494 z łańcuchem `pre/post` w `index/zadania.jsonl`.
- To **nie** identyfikuje POI uruchamiającego graf ani uniwersalnego
  klucza scena→scena. Pełna para repozytorium nazw/plików bazowych i parser
  `.cine` pozostają poza tym checkpointem. Szczegóły i ujemne wyniki:
  [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md), wpis 2026-11-17 (9).

**Następny krok:** wyjaśnić, skąd pobrać/odczytać pełne resource repository
(names + data) dla bieżącej instalacji; nie zgadywać mapowania GUID→POI.

## Bramka 3 — analiza `.cine`: osie cutscen (sesja 4+)

**Wejście:** wydobyte `.cine` (co najmniej `sq001_zlxl.cine` dla 30161 — 39
kwestii znanych z ekranu).
**Zadania:** struktura blokowa (nagłówek, tablica zdarzeń, stride), mapowanie
zdarzeń na kwestie (`hx_01…pma_06` z `sound_data`), weryfikacja na 30161
(dokładnie 39 linii w kolejności właściciela), potem uogólnienie na pozostałe
przerywniki z `cutscenes.cine_path`.
**Wynik:** `tools/cine_kolejnosc.py` + wnioski w
[CINE_KOLEJNOSC.md](CINE_KOLEJNOSC.md); czytanka bierze kolejność z osi
(decyzja właściciela po weryfikacji).

## Bramka 4 — analiza `.etsb`: następstwo scen i POI → sceny (sesja 5+)

**Wejście:** wydobyte `.etsb` z trafień POI (bramka 1/2) i ewentualne skrypty
z `LT*.mpk` (gdyby istniały i były czytelne).
**Zadania:** format tabel klienta (ETSB — przypuszczalnie skompilowana tablica
z `client/…`), szukanie pól odwołujących się do numerów scen (`4700001` itd.)
i do POI; sprawdzenie, czy wpis „Dragon Pattern Mark" istnieje w `poi.jsonl`
z `dialog: 4700001`-podobnym powiązaniem (najpierw przejrzeć to, co już
mamy w `index/` — może odpowiedź leży częściowo w POI, którego `dialog` jest
pusty, ale `storyline` wskazuje plik uruchamiający scenę).
**Wynik:** opis formatu + narzędzie deczytujące; powiązania scen włączone
do `index/` (nowe pliki lub pola), czytanka/chronologia korzystają z nich.

## Bramka 5 — domknięcie i dokumentacja (sesja 6+)

- Pełny przebieg: skaner → wycinarka → `cine_kolejnosc` → powiązania scen →
  czytanka w kolejności z gry.
- Uzupełnienie `docs/STATUS.md`, `docs/WERSJE_CZYTANKI.md` (nowa wersja po
  ułożeniu kolejności z osi), ewentualny wpis do `index/` (format v3).
- Decyzja właściciela: czy i co z tych plików trafia do repo (domyślnie:
  nie, tylko pochodne tekstowe).

## Ryzyka i awaryjne wyjścia

- **Paczki skompaktowane („lite")** — offsety indeksu nie fizyczne; skaner to
  wykryje (bramka 1) i wtedy potrzebna jest ścieżka `_walk_blocks` (bloki EZST
  back-to-back) albo dogadanie z właścicielem pełnej instalacji.
- **Brak trafień dla `.cine`** — wzorce ścieżek nietrafione; wtedy szukamy
  ścieżek w skryptach Lua z `LT*.mpk` (`wwm-lua`-owe podejście) albo w ciągach
  w `.csb`/UI; do tego czasu kolejność z danych HD zostaje jak jest.
- **Brakuje `Resources.mpkinfo`** — instalacja „lite"; wtedy zostają
  `Patch.mpkdb` (łatka) i sondowanie; uczciwie raportujemy pokrycie.
- **Zaszyfrowane w całości** — wtedy wracamy do rozmowy o planie B
  (memory-read) wyłącznie za świadomą zgodą właściciela; domyślnie NIE.
- **`.cine` nie ma tekstu, tylko odwołania** — nadal wystarcza do kolejności
  (o to prosimy); pełne tłumaczenie napisów i tak robi czytanka z `index/`.
