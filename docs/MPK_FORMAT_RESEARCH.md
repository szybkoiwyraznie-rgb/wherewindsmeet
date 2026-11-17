# Badanie formatu `.mpk` / `.mpkinfo` / `Patch.mpkdb` — co już wie świat o WWM

Stan: 2026-11-17. Zapis **źródeł i wniosków** z publicznych repozytoriów, żeby
nie robić reverse engineeringu od zera i żeby następne sesje miały punkt startu.
To nie jest plan pracy — plan mieszka w [ROADMAP_MPK_INDEKSY.md](ROADMAP_MPK_INDEKSY.md).

Zasada nadrzędna: obcy kod i cudze paczki **nie trafiają do repozytorium**;
do naszego kitu przenosimy wyłącznie *wnioski o formacie* i krótkie, własne
implementacje, z podaniem źródła. Jeden z znalezionych projektów oznaczyliśmy
jako **zakazany** (patrz §5).

## 1. `Zhincore/wwm-messiah-tools` — główne źródło (MIT)

https://github.com/Zhincore/wwm-messiah-tools — aktywna (ostatni commit
2026-11-17), Python + Rust, MIT (fork `fangfang1984/netease-messiah-tools`,
2022, MIT, oryginalnie Diablo Immortal / Messiah v1). To, co zweryfikowali na
Steam global build, odpowiada naszemu Patch 2.4.

### 1.1 Mapa źródeł indeksu (`tools/wwm/vfs.py`, `docs/file-id.md`)

| Gdzie | Plik indeksu | Jakie `.mpk` |
|---|---|---|
| katalog gry (root) | `Resources.mpkinfo` | `Resources.mpk`, `Resources<N>.mpk` (N z pola `packed`) |
| `LocalData/Patch/` | `LT<n>.mpkinfo` | `LT<n>.mpk` |
| `LocalData/Patch/` | `*.mpkinfo` (`MpkCached_*`, `TinyFiles_*`, `Patch<n>`) | `Patch<pack_id>.mpk` |
| `LocalData/Patch/` | `Patch.mpkdb` (SQLite) | `Patch<v2>.mpk` |

To dokładnie ten brakujący trop: **~200 plików `Resources*.mpk`**, o których
pisał właściciel, to części `Resources<N>.mpk` rozdzielone z jednej logicznej
paczki; o tym, który wpis indeksu siedzi w którym `Resources<N>.mpk`, mówi
pole `packed` w `.mpkinfo` — więc **nie trzeba przeszukiwać 200 paczek
na ślepo**: indeks i tak zna odpowiedź.

`Resources.mpkinfo` i `Patch.mpkdb` bywają opakowane jako `HEX_`/`HEXB_`
(metadane integralności) — wtedy to nie indeks, tylko zaszyfrowany JSON/msgpack.

### 1.2 `.mpkinfo` v3 (binarne; `mpk/src/v3_parser.rs`, `tools/wwm/vfs.py: read_mpkinfo`)

```
u32 version = 3
u32 count
count × 20 B wpisy: u32 id_lo, u32 id_hi, u32 offset, u32 size, u32 packed
16 B koniec (trailer, nieanalizowany)
```

- `file_id = (id_hi << 32) | id_lo`, gdzie `id_hi` = MurmurHash3-x86-32 ścieżki
  (seed 0), `id_lo` = sygnatura ogona bez rozszerzenia (patrz 1.4).
- `size` = rozmiar **zapisany** (zwykle blok EZST), liczba **bajtów**, nie wierszy.
- `packed`: bit 0 = placeholder/folder (`offset`/`size` zerowe — pomijamy),
  bity 1..31 = `pack_id` → nazwa kontenera `Resources{N}.mpk` / `Patch{N}.mpk`.
- Sanity: `len(data) == 8 + 20*count + 16` — inaczej to nie v3.
- Hybrid lite install: gdy `max(offset+size) > rozmiar kontenera`, wpisy nie
  adresują pliku fizycznie (skompaktowana „lite" paczka) — offsety nie
  zadziałają i trzeba iść blokami od początku (`Pack._walk_blocks`).

### 1.3 `Patch.mpkdb` (SQLite; `tools/wwm/vfs.py: read_mpkdb`)

Tabele `info0` (baza) i `info1` (dociągnięte aktualizacje), kolumny
`v0..v6+`; z perspektywy czytanki ważne:

- `v0` = file_id jako **signed i64** (odjąć 2^64 dla wartości ≥ 2^63),
- `v1` = rozmiar, `v2` = pack_id (`Patch<v2>.mpk`), `v3` = content hash
  (MurmurHash3-128 XOR połowy, po 2 MiB blokach dla plików ≥ 4 MiB),
- `v6` = offset fizyczny w kontenerze.

To jednocześnie **spis treści łatki** i dowód, że gra dociąga paczki
z `easebar.com` (wątek ResHax, patrz §4). Do czytania: wyłącznie
`sqlite3.connect("file:…?mode=ro", uri=True)`.

### 1.4 `file_id` — ścieżka → klucz (`docs/file-id.md`, `tools/wwm/ids.py`)

```
id = (MurmurHash3_x86_32(path /* utf-8, '/' */, seed=0) << 32) | lo32
```

- `path`: pełna ścieżka VFS, case-sensitive, z rozszerzeniem.
- Bez rozszerzenia dla `lo32`: ostatnia kropka **po ostatnim slashem** jest obcinana.
- `lo32` dla typowej ścieżki: ostatnie 3 znaki (last on top) + długość w najniższym
  bajcie (`n==0..2` — reguły specjalne w tabeli z doc).
- Ścieżka GUID-owa (`xx/<guid>[.6|.1]`, długość stripped 39/41): `lo32` =
  big-endian u32 z bajtów 3..6 (pierwsze 4 znaki GUID).

Krytyczne zastosowanie u nas: **mamy ~174 prawdziwych ścieżek klienta** spisanych
w `index/poi.jsonl` (pole `storyline`, np. `client/dialogs/hjt/sxd_lingwei.etsb`)
oraz `cine_path` znany z tabeli `cutscenes` (przykład `Char/e_01_cutscene/qhrw/
sq001_zlxl/sq001_zlxl.cine`). Dla każdego kandydata liczymy `file_id` i szukamy
go **w indeksie** — to natychmiast odpowiada: czy `.etsb`/`.cine` są
w `Resources*.mpk`, w `Patch*.mpk`, czy nigdzie (np. dociągane strumieniowo).

### 1.5 Bloki w `.mpk` (`tools/wwm/codecs.py`)

| Blok | Sygnatura | Zawartość |
|---|---|---|
| EZST | `EZST` + u32 `raw_size` | pierwsze `floor16(len)` B (max 256) AES-256-ECB, reszta zwykły zstd frame |
| ZSTD | `ZSTD` + u32 `raw_size` | zwykły zstd frame (bez szyfrowania) |
| LuaText | u32le `decoded_size` + surowy blok LZ4 | skompilowany Lua 5.4 (bez magii) |

Klucz AES jest opublikowany w repo (skrajnie słabe „drzwi frontowe", nie kryptografia).
`.mpk` z „lite" instalacji to szereg bloków EZST back-to-back.

### 1.6 Inne ustalenia z repo (na później)

- `wwm-lua` (`tools/wwm/lua.py`): wypisuje źródła Lua z debug info — tą drogą
  Zhincore ponazywał ~53 tys. wpisów skryptowych; kandydaci na dalsze ścieżki
  (`harvest.py`).
- `wwm-repository` (`tools/wwm/repository.py`, `docs/resource-names.md`): repo
  GUID→nazwa (dwa nieznane pliki VFS: ~1,2 MB imiona + ~89 MB dane, LZ4) —
  daje prawdziwe ścieżki zasobów; przydatne, gdybyście chcieli `.cine`/GUIDy
  mapować na nazwy zamiast zgadywać wzorce.
- `wwm-tables` (`tools/wwm/tables.py`, `docs/hd-store.md`): to **nasz** format
  `Package/HD/oversea` (`MANIFEST`/`indexN`/`dataN`) — u nich zweryfikowany na
  114 171 tabelach (10,08 M wierszy) steam global build. Nasze ekstrakty są
  na tej samej drodze i to potwierdza, że pełna baza = komplet tabel.
- Wniosek: czego NIE ma w żadnej z tych rodzin — **następstwa scen i .cine** —
  i tak nie ma w HD store; musi być w VFS (`Resources*` / `LT*` / `Patch*`).

## 2. `mohebbiamin/WWM-MPK-Tool` — zamknięty exe, tylko do oględzin (nie do repo)

https://github.com/mohebbiamin/WWM-MPK-Tool — Windows exe (~9 MB), GUI + CLI
(`info/list/extract/rebuild/probe/carve/db`), indeks `.mpkinfo` + `Patch.mpkdb`,
rekonstrukcja ścieżek heurystyką, brak źródeł w repozytorium (tylko release).
`Patch##.mpk` **nie mają** indeksu — robią to tryby `probe`/`carve`.

- Plus: dowód, że `.cine`/`.etsb` praktycznie dają się wydobyć z paczek,
  a `LT*.mpk` to paczki skryptowe z indeksem.
- Minusy: brak kodu do przeglądu (nie stawiamy cudzego, niewidzianego exe
  w naszym łańcuchu dostaw), unsigned → SmartScreen, licencja niejasna.
- Decyzja: **nie rekomendujemy używania**; nasz skaner robi `probe` po swojemu.
  Gdyby właściciel mimo wszystko chciał spróbować — na własne ryzyko, tylko do
  odczytu, kopia paczki.

## 3. `dest1yo/wwm_utils` — ZAKAZANY

https://github.com/dest1yo/wwm_utils — narzędzie do map lokalizacji.
Wątek ResHax wskazuje, że VirusTotal oznaczył je jako trojana
(https://github.com/dest1yo/wwm_utils/issues/1). **Nie pobieramy, nie uruchamiamy,
nie linkujemy właścicielowi jako opcji.**

## 4. ResHax — wątek „Where Winds Meet [ZZZ4/Messiah]" i inne

https://reshax.com/topic/18528-where-winds-meet-zzz4messiah/ — Deep dive
`translate_words_map` (to i tak znamy z własnego `locale/translate_words_map_*`),
wzmianka o `easebar.com` (dociąganie `.pak` → `.mpk`). Źródło
potwierdzające, że ~200 `Resources*.mpk` i `Patch*.mpk` to właśnie dociągnięte
delta-paczki; **nie** rozpakowujemy ich w naszym potoku budowania.

## 5. Czego w tych źródłach NIE MA (i co z tego wynika)

- Nikt publiczny nie opisał jeszcze **następstwa scen** (`4700001` → `4700041`
  → `4700352`) ani **uruchamiania scen przez POI** jako gotowego indeksu.
- Nikt publiczny nie opisał formatu **`.cine`** (osi platformy chronologii) —
  tylko `cine_path`/`cine_duration` w tabeli `cutscenes` i `cine_name`.
- Czyli nawet po powodzeniu skanera zostaje realna praca analityczna;
  skaner ma tylko odpowiedzieć: **które paczki / offsety / rozmiary** dotyczą
  naszych kandydatów, zanim zaczniemy carve'ować.

## 6. Bezpieczeństwo i granice

- Skaner **tylko czyta**: nagłówek i wybrane okienka paczek, indeksy,
  `Patch.mpkdb` w trybie `mode=ro`. Nie zapisuje w folderze gry, nie dotyka
  procesu gry, niczego nie wysyła do sieci.
- Wynik (hashy, offsety, nazwy paczek, ewentualne fragmenty ścieżek z danych)
  zostaje lokalny; do repo trafiają tylko wnioski/format/kod/dokumentacja.
- Duże dane gry (`*.mpk`, `*.mpkinfo`, `Patch.mpkdb`, wydobyte `.cine`) nie
  trafiają do Git — patrz [DATA_POLICY.md](DATA_POLICY.md).
