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

## Skala i co siedzi w pozostałych plikach

Suma pola `B` z nagłówków wszystkich 4386 chunków mapy EN to **1 122 784
wpisów** (średnio 256 na chunk), a łączny rozpakowany payload to
**94 581 912 B** (średnio ok. 84 B na wpis). To pierwsza liczba wpisów oparta
na strukturze, nie na heurystyce tekstowej.

Ten sam kontener (`0xDEADBEEF`, ta sama tabela) mają też `data3` (3949 chunków),
`data205` (2606) i `_diff`. Po dekompresji pierwszego chunku `data3` widać
identyfikatory typu `bp_399_pref_building_…`, a w `data205` nazwy ustawień typu
`disable_change_time_speed`, `enable_avatar_filter` — czyli indeksy danych gry,
**nie proza do tłumaczenia**. `MANIFEST` ma `count = 1` i jeden chunk bez ramki
zstd, więc jego układu nie sprawdzono.

## Rekord wpisu (zweryfikowane na 686 chunkach `_diff`)

W pliku `translate_words_map_en_diff` jest 686 chunków z jednym wpisem
(`A = B = 1`) — tam indeks jest mikroskopijny i układ dał się odczytać:

| offset w payloadzie | zawartość |
|---|---|
| 0 | `u64` A (liczba wpisów w „grupie”) |
| 8 | `u64` B (liczba wpisów w chunku) |
| 16 | `u32` `0x595896DC` |
| 20 | `u32` 0 |
| 24 | region indeksu (dla `B = 1` dokładnie **24 B**, dla `B = 2` — 56 B) |
| po indeksie | `u64` hash wpisu, `u32` typ (`8` = tekst UTF-8), `u32` długość |
| dalej | tekst o dokładnie tej długości, bez terminatora |

Sprawdzenie: dla chunku z tekstem `Northmount West` rekord ma długość `0x0F`
(15) i tyle dokładnie bajtów zajmuje tekst; dla `Unlocked at 5:00 on Jul 3` —
`0x19` (25) i 25 B; dla opisu muszli — `0x15E` (350) i 350 B. Zgodność
wystąpiła we wszystkich 686 przypadkach jednowpisowych.

Region indeksu rośnie z liczbą wpisów, ale nie liniowo od `B` (dla `B = 2`
i `B = 3` ma po 56 B), a wypełniają go bajty `0x80` — wygląda na strukturę
pochodną od hashy (trie/prefix), a **nie** na tabelę przesunięć tekstu. Jeśli to
się potwierdzi, indeks nie wymaga przeliczania przy zmianie długości tekstu,
a podmiana sprowadza się do rekordu (długość) i tekstu. To **hipoteza** — wymaga
sprawdzenia przez przebudowę chunku i odczyt zwrotny, zanim cokolwiek zapiszemy
w instalacji gry.

## Układ chunku `_diff` (odczytany w całości)

W plikach `_diff` chunk ma układ, który domyka się co do bajtu:

```text
[0..24)          nagłówek: u64 grupa, u64 liczba wpisów, u32 0x595896DC, u32 0
[24..24+I)       indeks — nieprzejrzysty, rozmiar I zmienia się per chunk
                 (obserwowane: 8, 20, 24, 36, 40, 56, 72 B)
[24+I ..)        N × 16 B rekordów: u64 hash, u32 typ, u32 długość
[dalej)          wszystkie teksty sklejone w kolejności rekordów, bez terminatora
```

`I` wyznacza warunek: suma zadeklarowanych długości musi równać się dokładnie
liczbie bajtów pozostałych po rekordach. Gdy indeks zawiera zera, kilka wartości
`I` spełnia sumę przypadkiem — rozstrzyga walidacja UTF-8 tekstów typu 8.

Narzędzie: `tools/locale_records.py` (tylko odczyt, walidacja, bez zapisu).
Na `translate_words_map_en_diff`: **598 z 4164** chunków przechodzi tę walidację
(suma 630 wpisów, 621 unikalnych hashy). Reszta jest odrzucana, nie zgadywana —
prawdopodobnie mają wspólne teksty albo inny wariant indeksu.

Mapa główna `translate_words_map_en` ma **inny** układ: po nagłówku widać ok.
8,7 kB nieprzejrzystego indeksu, a rekordów `[hash][typ][długość]` nie udaje się
tam odnaleźć jako tablicy stałej długości (sprawdzone 8/12/16/20/24/32 B z
kontrolą sumy). Jej 1 122 784 wpisów pozostają nieodczytane.

## Czego nie wiemy

- Znaczenia pól `A`, `B`, `C`; `C` jest stałe w plikach EN, `_diff` i `zh_cn_diff`,
  więc **nie** jest identyfikatorem języka.
- Znaczenia regionu indeksu (pochodna hashy?) i tego, czy zawiera on
  przesunięcia tekstu; jak odróżnić wpisy puste, usunięte i przeniesione.
- Czy układ `rekord + tekst` obowiązuje w chunkach wielowpisowych: dla
  `B = 1` potwierdzony, dla większych `B` jeszcze nie prześledzony.
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
