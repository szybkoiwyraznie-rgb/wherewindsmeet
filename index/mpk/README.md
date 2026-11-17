# `index/mpk/` — artefakty pochodne z paczek `.mpk` (bramki 2–3)

Wszystko tutaj jest **metadaną wyprowadzoną z danych gry** (hashy, offsety,
rozmiary, identyfikatory pól, liczniki). Surowe bloki gry i zdekodowane
źródła Lua/cine NIE są w repo — patrz [../../DATA_POLICY.md](../../DATA_POLICY.md).
Zdekodowane bloki trzyma `local/mpk_dekodowane/` (gitignore).

## Skąd to się wzięło

- 2026-11-17: właściciel uruchomił `WWM_MPK_Skaner_v3.zip` na instalacji
  Steam (Patch 2.4, folder `...\Where Winds Meet`). Wynik
  `WWM_MPK_Skaner_WYNIK (1).zip` (2 207 306 B, SHA-256
  `ca1837849990344e97e0014b75c087ce864c7fceeaa1fcc25c2008515dec9936`)
  zawiera: `RAPORT.json`, `PODSUMOWANIE.txt`, `mpkdb_dump.json`,
  `wyciete/` — 14 bloków `.cine` z `Resources34.mpk` (`106 800 B`)
  i 240 bloków `LT1.mpk` (`2 568 577 B`).
- Dekodowanie wg publicznego algorytmu z MIT repo
  `Zhincore/wwm-messiah-tools` (EZST = AES-256-ECB na prefiksie ≤256 B +
  zstd; `ZSTD` = goły zstd; LuaText = u32le + LZ4 → Lua 5.4 chunk).
  Narzędzie: [`../../tools/mpk_artefakty.py`](../../tools/mpk_artefakty.py)
  (wymaga `zstandard`, `pycryptodome`, `lz4` w osobnym venv).

## Co tu jest

| plik | zawartość |
|---|---|
| `cine_dekodowane.jsonl` | 14 plików: ścieżka VFS, pack/offset/rozmiar, sha256 surowego i dekodowanego, nagłówek `.cine`, tabela identyfikatorów pól (np. `StartTime`, `Entity`, `Camera`, `Montage`…) |
| `lt1_dekodowane.jsonl` | 240 wpisów: sha256, rozmiar, `debug_source` i wynikająca ścieżka VFS |
| `lt1_stringi.jsonl` | 41 727 identyfikatorów z bytecode'u Lua + licznik wystąpień (tylko `[A-Za-z0-9_/.@-]{4,}`; bez tekstu fabularnego) |
| `patch_mpkdb_info0.jsonl` | 854 wierszy `info0` (848 z `file_id_hex` + 6 wierszy-ścieżek `LuaText/patch/...`) |
| `patch_mpkdb_pak.jsonl` | 2 wiersze `pak` (pak = `LT1.mpk`: `2 097 152 + 471 425 = 2 568 577 B`) |
| `patch_mpkdb_meta.json` | 1 wiersz `meta` — tylko rozmiary i sha256 (bajty to zaciemniona konfiguracja; NIE zapisujemy) |

## Reguły VFS — potwierdzone na danych gry (2026-11-17)

1. **`file_id = MurmurHash3_x86_32(path /* utf-8, '/' */, seed=0) << 32 | lo32`**
   — nasza implementacja (`tools/mpk_skaner.py`) **walidowana na 240/240**
   bloków LT1: `file_id("LuaText/" + debug_source)` zgadza się z nazwą
   bloku z `.mpkinfo`. To samo daje 6 wierszy-ścieżek z `info0`
   (`LuaText/patch/patch_context.lua` itd.) i 5 potwierdzonych ścieżek.
2. **`LuaText/` to prefiks VFS plików Lua.** Debug name z bytecode'u
   (`@hexm/client/...`) + `LuaText/` = prawdziwa ścieżka VFS. POI
   `storyline` podany **bez** tego prefiksu nie dawał trafienia — kit v4
   dodaje warianty `LuaText/…`, `LuaText/hexm/…`,
   `LuaText/hexm/client/storyline_data/…`.
3. **`.cine` leżą w `Resources34.mpk`** pod ścieżkami `Char/<e_xx_cutscene>/<region>/<nazwa>/<nazwa>.cine`
   (trafień 14/14 wzorca; 974 filmów w `index/cutsceny_meta.jsonl`).
   Format dekodowanego `.cine`: magic `c1 59 41 0d` + **u64le długość
   pliku** + u8 `n` + `n` identyfikatorów pól null-terminated + binarna
   oś czasu (rekordy ze wskaźnikami do tabeli identyfikatorów; pole `"25"`/
   `"27"` przy `1e 02` powtarzają się — analiza w Bramce 3).
4. **`Patch.mpkdb`** = spis łatki: `info0` (v0 `file_id` signed i64 **albo
   ścieżka** dla 6 plików bootstrapu paczki, v1 rozmiar, v2 `pack_id`,
   v3 hash treści, v4/v5 flagi, v6 offset), `info1` (puste),
   `pak` (repozytorium łatki podzielone na 2 klocki 2 MB + 471 425 B —
   to jest `LT1.mpk`), `meta` (zaciemnione).

## Czego tu nadal NIE WIEMY

- nastepstw scen (`4700001 → 4700041 → …`) i podpięcia POI → `.etsb`:
  POI `storyline` NIE jest ścieżką VFS bez prefiksu; czekamy na wyniki
  kitu **v4** (kandydaci z prefiksami `LuaText/…`).
- pełnego formatu `.cine` (oś czasu, powiązanie z `cutsceny_meta.cine_name`) —
  Bramka 3.

## Regeneracja

```bash
python3 -m venv /tmp/ezst && /tmp/ezst/bin/pip install zstandard pycryptodome lz4
/tmp/ezst/bin/python tools/mpk_artefakty.py \
    --wynik-zip "google_drive/WWM_MPK_Skaner_WYNIK (1).zip"
```

Surowe bloki wypada potem trzymać poza repo (`local/mpk_dekodowane/`).

## Zasady dla przyszłych agentów

1. Nie commituj `RAPORT.json` / `PODSUMOWANIE.txt` z pełnymi ścieżkami
   bezwzględnymi — zapisuj wnioski w docs, metadane w JSONL tutaj.
2. Nie commituj bajtów `.cine`/Lua — tylko hashe i tabele identyfikatorów.
3. `lt1_stringi.jsonl` sortuje malejąco po `wystapien` — dobre do
   grepowania nazw scen/ID pod Bramką 3.
4. Każda zmiana indeksów musi przejść `python3 tools/run_tests.py`
   i `python3 tools/check_repository.py`.
