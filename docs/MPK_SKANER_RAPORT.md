# Raport z sondy `.mpk` — `WWM_MPK_Skaner` (uruchomienie właściciela, 2026-11-17)

Wejście: `WWM_MPK_Skaner_WYNIK.zip` (`17 180 B`, SHA-256
`0f80a219aef87ae0ff7e82ad4378f7e42fe786bc7a1112cc0915b31d0012f225`),
zmaszynowy raport `RAPORT.json`. Środowisko: Windows, Steam, folder gry
`...\steamapps\common\Where Winds Meet`. Dokument powstał z samego raportu —
prawdziwych paczek ani tekstów gry tu nie ma; offsety/liczby są metadanymi.

## 1. Inwentarz paczek

- **489 paczek `*.mpk`, razem `211 334 119 524 B` (~211 GB)**.
- Największe: `Resources35.mpk` (3,25 GB), `Resources34.mpk` (2,41 GB),
  `Resources40.mpk` (2,19 GB), `Resources69/70/37/39/66/72.mpk` (po ~2,17 GB).
- Reszta to m.in. `LT1.mpk` (2 568 577 B), `Patch3109.mpk` (27 822 546 B),
  `Patch3110.mpk` (26 552 643 B) w `LocalData\Patch\`.

## 2. Indeksy

### `Resources.mpkinfo` — główny spis zasobów

- **2 604 099 wpisów** (+46 063 placeholdery pomijane), **158 kontenerów**
  `Resources<N>.mpk` (+ `Resources.mpk` jako pack 0).
- **Wszystkie kontenery istnieją; offsety fizyczne wszędzie** (0 niefizycznych).
- Suma rozmiarów wpisów: `200 513 882 817 B`; pokrycie na plik zwykle
  ~85–100 %, ale **24 kontenery > 100 %** (max `Resources80.mpk` 144,3 %,
  `Resources90.mpk` 132,9 %, `Resources133.mpk` 121,4 %, `Resources138.mpk`
  117,1 %) — wpisy współdzielą bloki albo indeks zawiera duplikaty; do audytu,
  nie blokuje wycinania.
- Część paczek podejrzanie pusta: `Resources145.mpk` 55,1 %, `Resources146.mpk`
  44,7 %, `Resources149.mpk` 62,6 %, `Resources115.mpk` 70,3 % — być może
  częściowy pobór Steam; warto sprawdzić „Zweryfikuj integralność plików".

### `LocalData\Patch\LT1.mpkinfo` — paczka skryptowa

- **240 wpisów** → `LT1.mpk` (`2 568 577 B`), pokrycie 100,0 %, offsety
  fizyczne. To nasza główna nadzieja na Lua z odwołaniami do `.cine`/`.etsb`.

### `Patch3109.mpkinfo` / `Patch3110.mpkinfo` — paczki łatki 2.4

- 22 i 24 wpisy → `Patch3109.mpk` (27 822 546 B) / `Patch3110.mpk`
  (26 552 643 B), pokrycie 100,0 %. Średni blok ~1,2 MB → to nie są skrypty,
  tylko duże zasoby (wideo/tekstury). **Nie wycinamy.**

### `Patch.mpkdb` — baza łatki (SQLite)

- `info0`: **854 wierszy**, kolumny `v0..v6` (`v0` signed i64 = file_id,
  `v6` = offset), `info1`: 0 wierszy, `meta`: 1 wiersz, `pak`: 2 wiersze.
- Odpowiada na pytanie „co łatka 2.4 dołożyła/podmieniła" — pełny spis 854
  wpisów trafia do JSON w kit v2 (`mpkdb_dump.json`).

## 3. Trafienia kandydatów (14)

Wszystkie z wzorca `Char/e_01_cutscene/qhrw/<film>/<film>.cine`; **wszystkie
w `Resources34.mpk`**; rozmiary 4 177–23 174 B.

| plik (końcówka) | pack | offset | size |
|---|---|---|---|
| `sq001_zlxl/sq001_zlxl.cine` | 34 | 239 585 133 | 7 238 |
| `sq001_zlxl_mobile/sq001_zlxl_mobile.cine` | 34 | 560 249 733 | 6 239 |
| `sq002_hxtq/sq002_hxtq.cine` | 34 | 68 918 600 | 4 939 |
| `sq003_qhyt/sq003_qhyt.cine` | 34 | 467 747 302 | 6 387 |
| `sq004_hwsl/sq004_hwsl.cine` | 34 | 469 161 063 | 4 582 |
| `sq005_bnjx/sq005_bnjx.cine` | 34 | 239 657 456 | 7 204 |
| `sq006_hykz/sq006_hykz.cine` | 34 | 241 650 511 | 4 177 |
| `sq007_xfkr/sq007_xfkr.cine` | 34 | 1 693 759 467 | 10 219 |
| `sq009_xcsz/sq009_xcsz.cine` | 34 | 876 974 319 | 4 552 |
| `sq010_ydgz/sq010_ydgz.cine` | 34 | 761 011 270 | 6 190 |
| `sq011_jhzl/sq011_jhzl.cine` | 34 | 941 245 505 | 11 630 |
| `sq013_bfcs/sq013_bfcs.cine` | 34 | 241 376 941 | 4 234 |
| `sq017_lxhy/sq017_lxhy.cine` | 34 | 872 554 791 | 6 035 |
| `sq018_gtnl/sq018_gtnl.cine` | 34 | 973 289 295 | 23 174 |

Wzorce z `qhrw` działają, ale **tylko dla rodziny `e_01_cutscene`** — reszta
z 974 filmów ma zapewne inne prefiksy (`e_02_cutscene`, inne regiony), których
nie zgadliśmy.

**0 trafień dla `.etsb`/`.ets`** — wszystkie 174 ścieżki POI (`storyline`)
plus warianty rozszerzeń nie występują jako pliki VFS pod tymi ścieżkami.
Najbardziej prawdopodobne: `storyline` z POI to **cel skoku logicznego, nie
plik**; `.etsb` leżą gdzie indziej (prefiks nieznany). Do ustalenia po
zrzuceniu Lua (`LT1.mpk`).

**0 trafień** dla wzorców innych niż `e_01_cutscene/qhrw`.

## 4. Co z tego wynika

1. `file_id` i `.mpkinfo` poprawnie wskazują **istniejące** `.cine` — format
   indeksu i haszowania potwierdzone na realnej instalacji.
2. `.cine` leżą w zasobach **pod indeksem** → wycinanie po trafień = gotowe
   (kit v2).
3. `LT1.mpk` do analizy — to paczka Lua; harvest ścieżek z niej da resztę
   prefiksów `.cine`/`.etsb` (jeśli są w ogóle w zasobach).
4. Paczki łatki 2.4 (`Patch3109/3110`) nie przyniosą Lua — nie wycinamy.
5. `Patch.mpkdb` dostarczy pełny spis tego, co 2.4 podmieniła/dołożyła (854
   wpisy).

## 5. Dalej (bramka 2 w [ROADMAP_MPK_INDEKSY.md](ROADMAP_MPK_INDEKSY.md))

- Kit **`WWM_MPK_Skaner_v2.zip`**: ta sama sonda +
  a) wycinanie SUROWYCH bloków trafionych kandydatów (14 `.cine`),
  b) wycinanie wszystkich 240 bloków `LT1.mpkinfo` (~2,5 MB),
  c) `mpkdb_dump.json` — schema i wszystkie wiersze `Patch.mpkdb`.
  Bez dekodowania EZST/ZSTD — dekodujemy po swojej stronie.
- Właściciel uruchamia `SKANUJ.bat`, odsyła `WWM_MPK_Skaner_WYNIK.zip`
  (~3 MB) na Dysk.
- Po naszej stronie: odkodowanie EZST, analiza `.cine` (podział bloków,
  zdarzenia), harvest ścieżek z Lua → kandydaci v2 → kolejne uruchomienie
  skanera.
