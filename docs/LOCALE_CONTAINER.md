# Kontener tekstów gry (mapa locale)

Opis odczytany z własnych danych i **potwierdzony** przez narzędzia społeczności
([`dest1yo/wwm_utils`](https://github.com/dest1yo/wwm_utils),
[`lehieugch68/WWM-Locale-Editor`](https://github.com/lehieugch68/WWM-Locale-Editor)).
Nie kopiujemy ich kodu; opis służy do własnej, niezależnej implementacji
(`tools/locale_container.py`, `tools/locale_records.py`).

## Warstwa 1 — plik mapy

```text
u32 magic   = 0xDEADBEEF
u32 version = 1
u32 count   = liczba chunków
u32[count+1] tabela przesunięć (bajty od początku tabeli przesunięć)
chunki...
```

`base = 12 + 4 * (count + 1)`. Ostatni wpis tabeli jest wartownikiem równym
rozmiarowi reszty pliku, więc tabela domyka się do rozmiaru pliku.

**Chunk 0 nie jest tabelą tekstów** — to indeks mapy: `u64 suma wpisów |
u64 liczba chunków | u32[liczba chunków - 1]` (na mapie EN: 1 122 784 wpisów,
4386 chunków danych, 17560 B). Trzeba go przepisywać bez zmian. Mapa EN ma
więc **4387 chunków, z czego 4386 to tabele tekstów**.

## Warstwa 2 — chunk

```text
u8  compression_type   (4 = zstd)
u32 compressed_size
u32 decompressed_size
compressed_size bajtów danych
```

Prefiks ma 9 bajtów (struktura `packed`). Wszystkie chunki w mapie EN są typu 4.

## Warstwa 3 — tabela (po dekompresji)

```text
TableHeader 24 B : u64 entry_count, u64 value_count, u64 timestamp
buckets          : max(entry_count + 17, 24) B, nieprzejrzyste — kopiujemy bez zmian
entries          : entry_count * 16 B: u64 id, u32 offset, u32 length
values           : teksty
```

Położenie tekstu: `entries_pos + 16 * index + 8 + offset`, czyli `offset` jest
liczone od pola `offset` własnego wpisu. Zwykle teksty leżą sklejone zaraz za
tablicą wpisów (`offset = (entry_count - index) * 16 - 8 + suma_poprzednich`),
ale w danych gry zdarzają się wpisy wskazujące **wcześniejszy** region tekstów
(współdzielone teksty) oraz „dziury” (`id = 0`, `length = 0`) z nieaktualnymi
offsetami. Dlatego parser czyta teksty przez `offset`, a nie przez sumowanie
długości.

`entry_count` to **rozmiar tablicy slotów** (capacity), nie liczba tekstów;
`value_count` to liczba zajętych slotów. `buckets` to pole `ctrl` tablicy
hashowej (`0x80` = pusty slot, `0xFE` = usunięty, `< 0x80` = zajęty) plus
bajt `0xFF`, 15-bajtowa kopia początku `ctrl` i dopełnienie do 8 bajtów —
razem `entry_count + 17` (dla 511 slotów: 528 B).

`0x595896DC` w nagłówku to `seed` tablicy hashowej (wspólny dla całego pliku) —
wygląda jak magic, ale nią nie jest. Klucze są hashami tekstu źródłowego;
samego źródła plik nie przechowuje, dlatego mapy są per-język.

Wpis, którego tekst zaczyna się od bajtu `0xFF`, jest zaślepką, nie tekstem.

## Warstwa `_diff`

Warstwy poprawek (`*_diff`) używają tego samego kontenera i układu tabel:

- **Chunk 0** ma strukturę `u64 suma_wpisów_po_zmianie, u64 liczba_kubełków_bazy,
  u32[liczba_kubełków_bazy]`. Każdy wpis tablicy daje numer chunku w pliku
  `_diff`, który modyfikuje dany kubełek bazy, albo `0xFFFFFFFF`, jeśli ten
  kubełek nie ma zmian. Uwaga: w chunku 0 `liczba_kubełków_bazy` to rozmiar
  indeksu pliku **bazowego**, nie liczba chunków samego pliku `_diff` — dlatego
  `apply_translation.is_metadata_chunk` rozpoznaje chunk 0 warunkiem
  `len(payload) == 16 + 4 * count`.
- **Pozostałe chunki** to tabele tekstów o tym samym układzie co warstwa 3
  powyżej; zawierają wpisy dopisane, zmienione i usunięte (tekst o wartości
  zaczynającej się od `0xFF`).
- Klient nakłada warstwę różnicową dla danego języka względem pliku bazowego:
  najpierw mapa bazowa z `Package/HD/oversea/locale/`, potem aktualniejsza
  warstwa `_diff`. W danych z Patcha 2.4 (`build 26592996`, `2026-11-13`) plik
  `LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff` jest wyliczony
  od zera względem bazy w `Package/` i **zastępuje** starszy plik `_diff`
  z `Package/` (złożenie `Package` + `LocalData/Patch` daje dokładnie deklarowaną
  w nagłówku sumę `1 136 704` wpisów i m.in. cofa 34 wcześniejsze różnicowe klucze).
  Czytnik warstwowy `tools/mapa_tekstow.py` (`wybierz_warstwy_gry` /
  `filtruj_zastapione_diffy`) automatycznie wybiera aktywną warstwę `_diff`,
  natomiast patcher (`tools/patcher_wwm.py`) nadpisuje na dysku oba pliki
  niezależnie, utrzymując ich spójność.

## Zapisywanie (patche)

Przepakowanie tabeli: zachowujemy nagłówek i `buckets`, wpisy wypisujemy w tej
samej kolejności, teksty sklejamy od nowa zaraz za tablicą wpisów, a offsety
przeliczamy wzorem `(entry_count - index) * 16 - 8 + suma_poprzednich`. Dziury
dostają `offset = 0xFFFFFFFF`. Potem zstd i nowa tabela przesunięć kontenera.
W pliku `_diff` wpisy usunięte (`0xFF`) pozostają usunięte (nie są przekładane).

**Sprawdzone na wszystkich chunkach:** przepakowanie bez zmiany tekstów odtwarza
zbiór `id → tekst` w 4386/4386 chunkach mapy głównej i 4163/4163 chunkach
`_diff`. Bajty nie są identyczne (warianty tekstów są współdzielone, więc
kompaktowanie skraca tabelę), ale zawartość tak.

## Co jest odczytane

| Element | Stan |
|---|---|
| kontener, chunki, zstd | odczytane, testy w `tests/test_locale_container.py` |
| tabela wpisów, offsety, teksty i warstwy `_diff` | odczytane, testy w `tests/test_locale_records.py` i `test_mapa_tekstow.py` |
| zapis zwrotny (przepakowanie) | odczytany i sprawdzony na 8549 chunkach |
| 1 136 704 wpisów mapy EN (baza + `LocalData/Patch/_diff` w Patchu 2.4) | wyciągnięte, 0 błędów (poprzednio 1 124 787 w buildzie 25906190) |
| zapis zwrotny całej mapy i `_diff` przez łatkę | `tools/zbuduj_latke.py`, `tools/patcher_wwm.py` i `tools/apply_translation.py`; mała łatka testowa (`latka_testowa.py` na mapie EN) zweryfikowana w realnej grze Steam (UI + prolog + polskie znaki działają); symulacja obu patcherów sprawdzona na kopiach binarek Patcha 2.4 (`26592996`) |
| mówcy, powiązania tabel, kolejność scen | odczytane z bazy gry ([BAZA_GRY.md](BAZA_GRY.md), [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md)) |
| limity pól interfejsu i pełna fabuła w grze | **limity szerokości i pełne tłumaczenie nie sprawdzone jeszcze w grze** (widoki podają długość EN; pełna łatka czeka na zwrotkę) |
