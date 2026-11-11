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

`0x595896DC` w nagłówku to **nie magic** — to `u32` dolnej połowy `timestamp`
(2017-07-05), a nie stała formatu. `value_count` = liczba niepustych wpisów;
`entry_count` bywa większe (np. 511 slotów, 244 teksty).

Wpis, którego tekst zaczyna się od bajtu `0xFF`, jest zaślepką, nie tekstem.

## Zapisywanie (patche)

Przepakowanie tabeli: zachowujemy nagłówek i `buckets`, wpisy wypisujemy w tej
samej kolejności, teksty sklejamy od nowa zaraz za tablicą wpisów, a offsety
przeliczamy wzorem `(entry_count - index) * 16 - 8 + suma_poprzednich`. Dziury
dostają `offset = 0xFFFFFFFF`. Potem zstd i nowa tabela przesunięć kontenera.

**Sprawdzone na wszystkich chunkach:** przepakowanie bez zmiany tekstów odtwarza
zbiór `id → tekst` w 4386/4386 chunkach mapy głównej i 4163/4163 chunkach
`_diff`. Bajty nie są identyczne (wariante tekstów są współdzielone, więc
kompaktowanie skraca tabelę), ale zawartość tak.

## Co jest odczytane

| Element | Stan |
|---|---|
| kontener, chunki, zstd | odczytane, testy w `tests/test_locale_container.py` |
| tabela wpisów, offsety, teksty | odczytane, testy w `tests/test_locale_records.py` |
| zapis zwrotny (przepakowanie) | odczytany i sprawdzony na 8549 chunkach |
| 1 122 784 wpisów mapy EN | wyciągnięte, 0 błędów (4386 tabel + chunk indeksu) |
| zapis zwrotny przez patcher | `tools/apply_translation.py`, sprawdzony na całej mapie EN (200 podmian, 11 s) |
| mówcy, kolejność scen | **nieodczytane** |
| limity pól interfejsu | **nieznane** (używamy długości oryginału) |
