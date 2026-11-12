# Patcher — jak działa i jak go używać

Głównym narzędziem budującym zmienione mapy tekstów z magazynu tłumaczeń
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
  --zh "pliki/translate_words_map_zh_cn" "pliki/000007_translate_words_map_zh_cn_diff" \
  --cel "pliki/000001_translate_words_map_en" \
  --cel "pliki/000003_translate_words_map_en_diff" \
  --cel "pliki/000002_translate_words_map_en_diff" \
  --wyj dist/latka
```

- `--indeks` — wyciąg `index/` (do mapowania kwestii zależnych od płci i wariantów),
- `--magazyn` — katalog `tlumaczenie/` (`pl_*.jsonl`, `pl_warianty.jsonl`),
- `--zh` — chińska mapa źródłowa i jej warstwy `_diff` (służy do wyliczenia klucza SHA-256 każdego identyfikatora),
- `--cel` — docelowe pliki wybranego języka klienta (baza + warstwy `_diff`, np. angielskie); każdy jest przepisywany osobno pod swoją nazwą do `--wyj`,
- `--wyj` — osobny katalog wyjściowy (nie może być katalogiem plików wejściowych).

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
- **Brak jeszcze skryptu instalującego łatkę u właściciela** (kopia bezpieczeństwa oryginałów, podmiana, sprawdzone przywracanie) — nie wolno podmieniać plików instalacji gry bez osobnego planu i działającego cofania.

## Wynik na realnych mapach w piaskownicy

Próba na 3 prawdziwych mapach EN z buildu `25906190` i sztucznym magazynie
19 630 przekładów (23 s): przepisano 95 471 wpisów mapy bazowej oraz 847 i 1 060
w dwóch warstwach `_diff`; po złożeniu warstw zmienionych 96 019 z 1 124 787
wpisów, zbiór identyfikatorów niezmieniony, read-back przeszedł bez rozjazdów.
Wcześniejsza próba jednostkowa `apply_translation.py` (200 tekstów → 41 962
podmiany przez dziedziczenie, 11–13 s) również przeszła read-back i
`tools/locale_container.py`.
