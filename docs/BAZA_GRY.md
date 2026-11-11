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
części        : n_części × 8 B  (u16 plik indeksu, u16 chunk, u32 0xFFFFFFFF)
ogon          : u32 liczba + nazwy plików indeksu, u32 liczba + nazwy plików danych
```

Rekord tabeli (32 B): `u32 wiersze, u32 liczba_części, u16 plik_schematu,
u16 chunk_schematu, u32 d, u32 hash, u32 0, u32 pierwsza_część, u32 flagi`.

- `plik_schematu = 0xFFFF` oznacza tabelę bez schematu kolumn.
- Części `pierwsza_część … +liczba_części` wskazują chunki indeksu z wierszami.
- Flagi: bit `0x400` — klucze wierszy są liczbami (`u64`), bit `0x800` — klucze
  są napisami; bit `0x1` — tabela bez chunku schematu.
- Manifest z patcha (`LocalData/Patch`): 114 171 tabel z rekordem, 149 050
  części, oraz 284 + 163 767 nazw bez rekordu (głównie `spaces.*` i `maps.*`;
  ich znaczenie jest **niewyjaśnione** — nie mają położenia w tych plikach).
- Największe rodziny nazw z rekordem: `dialog_timelines.<numer>` 74 950,
  `spaces.*` 23 302, `new_graph_cues.*` 2 443, `maps.*` 1 582; razem 7 595
  różnych prefiksów.

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
| `0x0a` | obiekt: `u16` **liczba elementów = 2 × liczba pól**, potem pary nazwa/wartość |
| `0x28` | słownik z dowolnymi kluczami (ta sama budowa co `0x0a`) |
| `0x0b` `0x0c` `0x0d` | None, False, True |

Wiersz tabeli **ze schematem** ma inną budowę: `u16 liczba_pól`, potem pola
`u16 (numer_kolumny | typ << 10)` + dane. Numer kolumny ma 10 bitów (tabele
mają ponad 256 kolumn), `typ` to ten sam tag co wyżej, a dane są kodowane jak
wartość z etykietą, tylko bez bajtu etykiety. Kolumn, których wiersz nie
wypełnia, po prostu w nim nie ma.

## Sprawdzenie na całej bazie (2026-11-11)

`python3 tools/baza_gry.py KATALOGI --sprawdz` czyta każdy wiersz każdej tabeli
i wymaga, żeby wartość skończyła się w swoim przedziale, a dopełnienie było
zerowe. Wynik na dostawach z Dysku (pliki bazowe + `LocalData/Patch`):

| miara | wynik |
|---|---|
| tabel w `MANIFEST` | 114 171 (28 261 ze schematem), 10 077 485 wierszy |
| tabel odczytanych bez błędu | **113 792**, 10 069 118 wierszy |
| nieznane tagi | 0 |
| tabel z inną liczbą wierszy niż w `MANIFEST` | 377 (różnica zwykle 1–3 wiersze) |
| tabel z błędem wartości | 2 (`0x00` w miejscu tagu) |

Rozbieżności liczby wierszy **nie są jeszcze wyjaśnione**: w 171 z 377 tabel
indeks ma tyle wierszy, ile podaje `MANIFEST` bazowy (z `Package`), a nie ten
z `LocalData/Patch`, więc patch najpewniej nakłada wiersze inną drogą niż
lista części tabeli. Do ustalenia, zanim audyt aktualizacji będzie na tym
polegał.

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

`tools/timeline.py` wycina scenę od znacznika `TimelinePObject` do następnego
i bierze pierwsze `dialog_no` z tego wycinka. Ponieważ `dialog_config` leży
**przed** własnym `timeline`, wycinek zawiera `dialog_config` **następnego**
dialogu. Skutek: w `index/` numer i projekt każdej sceny należą do sceny
następnej w pliku. Potwierdzenie na samym indeksie:

| pomiar | wynik |
|---|---|
| zapisany `dialog_no` = `source_id // 100` **następnej** sceny | 62 726 z 62 746 par |
| zapisany `dialog_no` = `source_id // 100` własnej sceny | 0 z 62 602 |
| `source_id // 100` jest kluczem rejestru | 68 268 z 68 274 scen z tekstem |
| „brakujące” numery, które są numerem sceny już obecnej w indeksie | 5 506 z 5 859 |
| plik poprawki (numery skaczą o miliony): zgodność z następną sceną | 14 z 14 |

Wnioski z `docs/SCENY_WWM.md` i `docs/ANALIZA_KORPUSU.md` oparte na tym numerze
(„5 871 scen bez `dialog_no`”, „`dialog_no` to grupa”, przypisanie scen do
projektów, 5 859 braków) są **artefaktem parsera**, nie cechą danych. Poprawne
odczytanie: numer dialogu = nazwa tabeli `dialog_timelines.<numer>`.
