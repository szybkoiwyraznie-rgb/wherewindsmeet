# Patcher — jak działa i jak go używać

## Jedno polecenie z dowolnej zwrotki (`tools/one_click_patch.py`)

Gdy spłynie od tłumacza częściowa albo pełna zwrotka (kilka plików `.md`,
katalog albo archiwum `.zip` z częściowo wypełnionymi polami `PL:`) oraz zrzut
z gry (`WWM_DANE_*.zip` ze zbieracza `collector/` lub rozpakowany katalog
map), jedno polecenie buduje gotowy one-clickowy instalator `WWM_LATKA_PL.zip`
dla Windows:

```bash
python3 tools/one_click_patch.py \
  --zwrotka zwrotka_czesc1.zip [plik2.md ...] \
  --dane-gry WWM_DANE_20261111_181913_13ff7ac1.zip \
  --wyj-zip dist/WWM_LATKA_PL.zip
```

Skrypt w jednym przebiegu:
1. importuje wyłącznie wypełnione linie `PL:` (puste `PL:` pomija bezpiecznie — obsługuje częściowe zwrotki),
2. łączy zwrotkę z bazowym magazynem `--magazyn tlumaczenie` (o ile istnieje i nie podano `--tylko-zwrotka`; opcjonalnie utrwala go przez `--zapisz-magazyn`),
3. odczytuje `RAPORT.json` i automatycznie wykrywa mapy `zh_cn`, docelowe mapy języka (`Package/...` i `LocalData/Patch/...`) oraz `steam_build_id`,
4. przepisuje binarne mapy gry z obsługą wariantów płci i kolizji fabularnych oraz weryfikuje każdy wpis,
5. pakuje wynik razem z `instalator/` (`ZAINSTALUJ.bat`, `PRZYWROC.bat`, `SPRAWDZ_STAN.bat`) do jednego gotowego `WWM_LATKA_PL.zip`.

W przypadku błędów w zwrotce (np. zgubione tokeny lub złamana linia) domyślnie
przerywa z listą błędów w JSON (`exit code 2`); flaga `--pomin-bledne` pozwala
zbudować łatkę wyłącznie z poprawnych wpisów. Zamiast `--dane-gry` można też
podać jawnie `--zh`, `--mapa` i `--build-gry`.

## Budowa łatki krok po kroku (`tools/zbuduj_latke.py`)

Głównym narzędziem niskopoziomowym budującym zmienione mapy tekstów z magazynu tłumaczeń
(`tlumaczenie/`) jest `tools/zbuduj_latke.py`. Wykorzystuje ono niższy poziom
(`tools/apply_translation.py`), przepisując osobno mapę główną **oraz** jej
warstwy `_diff`. Narzędzie działa lokalnie na kopii plików z gry i nigdy nie
modyfikuje oryginałów.

Pełny opis obiegu, ról plików i procedury przy aktualizacjach jest w
[PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md).

## Zbudowanie łatki z magazynu (`tools/zbuduj_latke.py`)

```bash
python3 tools/zbuduj_latke.py \
  --indeks index \
  --magazyn tlumaczenie \
  --zh "pliki/translate_words_map_zh_cn" "pliki/translate_words_map_zh_cn_diff" \
  --mapa Package/HD/oversea/locale/translate_words_map_en "pliki/Package/HD/oversea/locale/translate_words_map_en" \
  --mapa Package/HD/oversea/locale/translate_words_map_en_diff "pliki/Package/HD/oversea/locale/translate_words_map_en_diff" \
  --mapa LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff "pliki/LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff" \
  --build-gry 25906190 \
  --wyj dist/latka
```

- `--indeks` — wyciąg `index/` (do mapowania kwestii zależnych od płci i wariantów),
- `--magazyn` — katalog `tlumaczenie/` (`pl_*.jsonl`, `pl_warianty.jsonl`),
- `--zh` — chińska mapa źródłowa i jej warstwy `_diff` (służy do wyliczenia klucza SHA-256 każdego identyfikatora),
- `--mapa SCIEZKA_W_GRZE PLIK` — jawna para docelowej ścieżki w instalacji gry i lokalnego pliku wejściowego (rozróżnia identyczne nazwy między `Package/...` i `LocalData/Patch/...` i zapisuje `sciezka_w_grze` oraz `plik_latki` w `latka.json`),
- `--cel` — alternatywny zapis dla pojedynczych plików o unikalnych nazwach (lub ze ścieżką zawierającą `Package/` albo `LocalData/Patch/`),
- `--build-gry` — opcjonalny `buildid` ze Steam zapisywany w `latka.json` (sprawdzany przy instalacji),
- `--wyj` — osobny katalog wyjściowy (nie może być katalogiem plików wejściowych).

Gotową łatkę z `--wyj` można spakować razem ze skryptami Windows (`instalator/`:
`ZAINSTALUJ.bat`, `PRZYWROC.bat`, `SPRAWDZ_STAN.bat`, `instaluj_latke.ps1`,
`CZYTAJ_TO.txt`) do jednego archiwum:

```bash
python3 tools/build_installer_kit.py --latka dist/latka --output dist/WWM_LATKA_PL.zip
```

Do pierwszego bezpiecznego sprawdzenia czcionek i przyjmowania map w grze służy
osobny generator małej łatki UI (`tools/latka_testowa.py` oraz plan w [TEST_W_GRZE.md](TEST_W_GRZE.md)).

Kolejność dobierania przekładu dla identyfikatora:
1. wprost po identyfikatorze (`pl_warianty.jsonl` — kwestie zależne od płci bohatera; nieprzetłumaczony wariant dziedziczy po drugim wariancie tego samego tekstu),
2. po kluczu SHA-256 tekstu chińskiego z `--zh`, a jeśli nie ma wersji chińskiej — tekstu z pliku celu.

Po zapisie każdego pliku łatka czyta własne wyjście z powrotem i porównuje
każdy wpis: zmienić się mogą wyłącznie wpisy z przekładem i tylko na ten przekład;
wpisy usunięte (`0xFF` w `_diff`) pozostają usunięte.

## Narzędzie niskopoziomowe (`tools/apply_translation.py`)

Do pojedynczego pliku mapy i jawnego JSONL `{"id": "…", "text": "…"}`:

```bash
python3 tools/apply_translation.py \
  --map "pliki/000001_translate_words_map_en" \
  --tlumaczenia tlumaczenia.jsonl \
  --wyjscie "pliki/000001_translate_words_map_en.new"
```

Wymaga `zstandard` (`pip install -r requirements-dev.txt`). Czyta kontener
([LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)), przepisuje chunk 0 bez zmian,
przepakowuje tabele z nowymi offsetami i weryfikuje wynik przed zapisem.

## Czego jeszcze nie ma i co nie zostało sprawdzone

- **Nie przetestowano łatki w rzeczywistej grze** (klient może sprawdzać sumy kontrolne plików przy starcie lub aktualizacji, czcionki mogą nie mieć wszystkich polskich znaków, a pola interfejsu mają nieznane limity szerokości).
- **Nie wybrano docelowo zastępowanego języka klienta** (dotychczasowe próby na mapie EN w piaskownicy).
- **Skrypty instalatora i przywracania (`instalator/`)** przeszły automatyczne testy Windows CI na fikcyjnej instalacji (kopia oryginałów poza grą, sprawdzanie SHA-256 i buildu Steam, transakcyjny zapis z cofnięciem błędu, bezpieczne przywracanie), ale **nie były jeszcze uruchamiane na rzeczywistej instalacji gry właściciela** ([TEST_W_GRZE.md](TEST_W_GRZE.md)).

## Wynik na realnych mapach w piaskownicy

Próba na 3 prawdziwych mapach EN z buildu `25906190` i sztucznym magazynie
19 630 przekładów (23 s): przepisano 95 471 wpisów mapy bazowej oraz 847 i 1 060
w dwóch warstwach `_diff`; po złożeniu warstw zmienionych 96 019 z 1 124 787
wpisów, zbiór identyfikatorów niezmieniony, read-back przeszedł bez rozjazdów.
Wcześniejsza próba jednostkowa `apply_translation.py` (200 tekstów → 41 962
podmiany przez dziedziczenie, 11–13 s) również przeszła read-back i
`tools/locale_container.py`.
