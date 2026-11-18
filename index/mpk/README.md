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
| `storyline_graphs.jsonl` | 14 grafów `Storyline` z dekodowanych bloków: liczby typów węzłów oraz wybrane identyfikatory zadań, transferów, przestrzeni, cutscen/QTE i ścieżki zagnieżdżonych storyline; bez tekstu, pozycji, payloadów ani krawędzi grafu |
| `sciezki_vfs.jsonl` | 11 278 unikalnych ścieżek/nazw plików VFS z bazy gry (974 `.cine`, 3 011 `.graph`, 926 `.etsb`, 6 367 `.ets`; 10 559 z katalogiem): kolumny `cutscenes.cine_path`, `fenbao_cutscene_info.resources`/`.cutscene_graph` (z numerami cutscen w polu `cutsceny`) + surowy skan chunków `dataN`; generator `tools/sciezki_vfs.py` — to są kandydaci file_id dla skanera v7 |
| `cine_ujecia.jsonl` | **978 masterów `.cine`** z przebiegu v7: ścieżka, numery cutscen, **uporządkowana lista pod-ujęć** (5 022 dzieci, 5 021 potwierdzone w paczkach po `file_id`) — kolejność ujęć przerywnika wprost z osi czasu gry; generator `tools/wynik7_indeksy.py` |
| `etsb_storyline.jsonl` | **6 961 rozwiązanych skryptów `Storyline/<ścieżka>.etsb`** (reguła VFS: prefiks `Storyline/`): file_id, kontener + fakty z grafu (sceny `dialogs_no`, cutsceny, zadania, zagnieżdżone skrypty); zawiera benchmark POI `Storyline/client/dialogs/hjt/sxd_longwenbiaoji.etsb → scena 4700001` |
| `storyline_sceny.jsonl` | **8 948 grafów Storyline** z przebiegu v7 (bloki EZST + kandydaci + skan goły, dedup): sceny/cutsceny/zadania/skrypty w grafie + `nastepstwa` — krawędzie przez węzły pośrednie: 3 909 scena→scena (1 508 unikalnych), 235 cutscena→scena, 182 scena→cutscena, 192 cutscena→cutscena |
| `poi_storyline_sceny.jsonl` | **191 POI z `interact_storyline`** (`index/poi.jsonl`) skrzyżowane z `etsb_storyline.jsonl`: 61 ze sceną (w tym benchmark POI 200046001 → `sxd_longwenbiaoji.etsb` → scena 4700001), 55 bez scen w grafie, 75 nierozwiązanych (głowa sondy nie trafiła — kandydaci do kitu v8); generator `tools/poi_storyline_sceny.py` |

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
4. **Storyline — przykład referencji do cutsceny (2026-11-17):**
   blok `5_a31638d0356c7433` ma `DialogCutsceneSequenceNode` z ID `2560507`
   (znalezione jako `d` w `index/sceny_3.jsonl`) i `32474` typu 2
   (w `index/cutsceny_meta.jsonl`: `sq001_qzpk_male`, 10,5 s).
   To potwierdza ścieżkę **graf Storyline → dialog/cutscene ID**, ale nie
   wskazuje POI, które uruchamia ten graf. W `5_2a40efe1316c7433` występują
   `TrackTaskNode` 380493/380494, a łańcuch `pre/post` zadań istnieje w
   `index/zadania.jsonl`; są to kotwice do dalszego mapowania, nie dowód
   ogólnej kolejności scen.
5. **`Patch.mpkdb`** = spis łatki: `info0` (v0 `file_id` signed i64 **albo
   ścieżka** dla 6 plików bootstrapu paczki, v1 rozmiar, v2 `pack_id`,
   v3 hash treści, v4/v5 flagi, v6 offset), `info1` (puste),
   `pak` (repozytorium łatki podzielone na 2 klocki 2 MB + 471 425 B —
   to jest `LT1.mpk`), `meta` (zaciemnione).

## Czego tu nadal NIE WIEMY

- Następstwa scen (`4700001 → 4700041 → …`) ani wiarygodnego klucza
  POI → start sceny. `storyline_graphs.jsonl` ujawnia przykłady powiązań
  grafów z łańcuchem zadań i cutsceną, ale nie wiąże grafu z wierszem POI;
  hashowanie 174 unikalnych storyline-ścieżek (warianty prefiksu i `.ets/.etsb`)
  dało 0 trafień w 848 Patch `info0` i 240 LT1. Wynik v4 właściciela miał
  14/8 066 trafień kandydujących, wszystkie `.cine` z pack-34, bez POI.
- Pełnego formatu `.cine` (oś czasu i mapowanie rekordów na kwestie) —
  Bramka 3.

## Regeneracja

```bash
python3 -m venv /tmp/ezst && /tmp/ezst/bin/pip install zstandard pycryptodome lz4
/tmp/ezst/bin/python tools/mpk_artefakty.py \
    --wynik-zip "google_drive/WWM_MPK_Skaner_WYNIK (1).zip"
```

Surowe bloki wypada potem trzymać poza repo (`local/mpk_dekodowane/`).
Indeks grafów wymaga już zdekodowanych bloków JSON (np. z
`local/patch_karwedane/`):

```bash
python3 tools/index_storyline_graphs.py local/patch_karwedane \
    --output index/mpk/storyline_graphs.jsonl
```

## Zasady dla przyszłych agentów

1. Nie commituj `RAPORT.json` / `PODSUMOWANIE.txt` z pełnymi ścieżkami
   bezwzględnymi — zapisuj wnioski w docs, metadane w JSONL tutaj.
2. Nie commituj bajtów `.cine`/Lua — tylko hashe i tabele identyfikatorów.
3. `lt1_stringi.jsonl` sortuje malejąco po `wystapien` — dobre do
   grepowania nazw scen/ID pod Bramką 3.
4. Każda zmiana indeksów musi przejść `python3 tools/run_tests.py`
   i `python3 tools/check_repository.py`.
