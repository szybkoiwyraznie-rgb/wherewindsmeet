# Kontener map lokalizacyjnych WWM — rozpoznanie z 2026-11-11

Dokument opisuje **jedno prywatne archiwum wynikowe** zbieracza
(`WWM_DANE_20261111_181913_13ff7ac1.zip`, 72 995 594 B) i pliki w nim zawarte:
`translate_words_map_en`, `translate_words_map_en_diff` (×2), `MANIFEST` (×2),
`translate_words_map_zh_cn_diff`, `data3`, `data205`. Nie jest to opis
potwierdzony na innej wersji gry ani gwarancja, że każdy plik ma ten sam układ.

Archiwum i rozpakowane dane pozostają poza Git (ignorowany `local/`). Poniżej
są tylko struktury i liczby, bez treści gry.

## Co jest zmierzone

Magiczna liczba każdego z ośmiu plików to `EF BE AD DE` (`0xDEADBEEF`)
zapisane little-endian. Dalej dla `translate_words_map_en` (50 550 179 B):

| offset | zawartość | wartość w pliku EN |
|---|---|---|
| 0 | magic `0xDEADBEEF` | — |
| 4 | wersja `uint32` | `1` |
| 8 | liczba chunków `uint64` | `4387` |
| 16 | `uint32[count]` — offsety względem końca tablicy | rośnie monotonicznie |
| 16+4·count | dane chunków | koniec ostatniego offsetu = rozmiar pliku (różnica 0 B) |

Sprawdzenie domknięcia: `16 + 4·4387 + 0x3031107 = 0x30355A3` = rozmiar
pliku. Ostatni wpis tabeli (indeks 4386) ma długość **0 B** — to wartownik,
więc realnych chunków jest **4386**. Wszystkie 4386 rozpakowują się bez błędu.

Każdy chunk to 8-bajtowy prefiks i co najmniej jedna ramka **zstd**
(magic `28 B5 2F FD`); w zbadanych chunkach ramka zaczyna się na przesunięciu 9
względem początku chunku. Po dekompresji payload ma nagłówek:

```
uint64 A   # 511 w EN, 1–7 w plikach _diff
uint64 B   # liczba wpisów w chunku (np. 244, 236, 260; w _diff A == B)
uint32 C   # 0x595896DC w każdym zbadanym pliku
uint32 0
```

Za nagłówkiem jest region indeksu z gęstymi bajtami `0x80`, a dalej tekst
w postaci łańcuchów rozdzielonych bajtem `NUL`. Tekst jest jawny, z markupem
GRY: `#Y…#E`, `#G…#`, `#Z…#E`, `$T(5001)`, `{}` jako placeholder.

Zgrubny pomiar z całego pliku EN (heurystyka „łańcuch NUL + głównie ASCII”):
**1 922 733** fragmenty i **64 097 425** znaków, przy czym liczba ta zawiera
także fragmenty indeksu, więc **nie jest** liczbą wpisów do tłumaczenia.
Liczba wpisów z nagłówków chunków (suma `B`) jest osobnym, jeszcze nie
zmierzonym parametrem.

## Czego nie wiemy

- Znaczenia pól `A`, `B`, `C`; `C` jest stałe w plikach EN, `_diff` i `zh_cn_diff`,
  więc **nie** jest identyfikatorem języka.
- Jak indeks wiąże łańcuchy z kluczami/hashami i jak odróżnić wpisy puste,
  usunięte i przeniesione.
- Czy `data3`/`data205`/`MANIFEST` mają ten sam układ rekordów — mają tę samą
  magiczną liczbę i ten sam nagłówek, ale ich payload nie był rozpakowany.
- Jak zapisać plik z powrotem: kolejność, kompresja, sumy i ewentualne
  ograniczenia klienta. **Nie wolno** zakładać, że wystarczy podmienić tekst.
- Relacja `_diff` do mapy głównej: `_diff` ma mniej chunków (EN diff 4164,
  zh_cn diff 2201) i chunki o 1–7 wpisach, więc wygląda na przyrost, ale
  kierunku zastosowania nie sprawdzono.

## Jak to odtworzyć

Dane: prywatne archiwum w ignorowanym `local/`. Dekompresja wymaga biblioteki
zstd (Python 3.11 nie ma jej w bibliotece standardowej; użyto `zstandard`
w lokalnym, ignorowanym `.venv`). Skrypt analizy leżał w `local/` i **nie jest**
częścią repozytorium — zawiera ścieżki do danych gry.

```sh
.venv/bin/pip install zstandard
.venv/bin/python local/analiza_mapy.py
```

Kolejny krok to ekstraktor zapisujący pary (klucz, tekst) do formatu pakietu
tłumacza, z jawnym raportem wpisów nierozpoznanych — patrz
[STATUS.md](STATUS.md) i [TRANSLATION_BUNDLE.md](TRANSLATION_BUNDLE.md).
