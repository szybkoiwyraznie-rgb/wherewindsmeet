# Patcher — jak działa i jak go używać

Patcher podmienia teksty w mapie locale gry. Uruchamiasz go **lokalnie**, na
kopii pliku z gry; narzędzie nigdy nie modyfikuje pliku wejściowego.

## Użycie

```bash
python3 tools/apply_translation.py \
  --map "pliki/000001_translate_words_map_en" \
  --tlumaczenia tlumaczenia.jsonl \
  --wyjscie "pliki/000001_translate_words_map_en.new"
```

- `--map` — oryginalna mapa z gry (nie jest zmieniana),
- `--tlumaczenia` — JSONL, po jednym `{"id": "…", "text": "…"}` na linię
  (`id` to identyfikator z paczki dla Tłumacza, 16 znaków hex),
- `--wyjscie` — nowy plik mapy; musi być inny niż `--map`,
- `--poziom` — poziom zstd (domyślnie 9),
- `--bez-weryfikacji` — pomija kontrolę po zapisie (nie zalecane).

Wymaga pakietu `zstandard` (`python3 -m venv .venv && .venv/bin/pip install zstandard`).

## Co robi

1. Czyta kontener, chunki i tabele (format w [LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)).
2. Chunek 0 (indeks mapy) przepisuje bez zmian.
3. W każdej tabeli podmienia teksty wpisów, których `id` występuje w pliku
   tłumaczeń; pozostałe wpisy zostają nietknięte.
4. Przepakowuje tabelę: te same id, nowe offsety i długości, teksty sklejone od
   nowa. Dzięki temu tłumaczenie może być dłuższe lub krótsze od oryginału.
5. Kompresuje chunki, składa nowy kontener z nową tabelą przesunięć.
6. **Weryfikuje wynik przed zapisem:** czyta własne wyjście i porównuje każdy
   wpis — jeśli cokolwiek się nie zgadza, plik nie powstaje.

## Co wypisuje

```json
{"chunks": 4387, "entries": 1122784, "applied": 200, "ids_not_in_map": 0,
 "bytes_before": 50550179, "bytes_after": 51904280,
 "verified": {"ids": 1122784, "changed": 200}, "ok": true, "output": "…"}
```

- `applied` — ile wpisów podmieniono,
- `ids_not_in_map` — ile id z pliku tłumaczeń nie istnieje w mapie (np. teksty
  z innej wersji gry); takie pozycje są pomijane, nie zgadywane,
- `verified.changed` — ile wpisów różni się od oryginału w zapisanym pliku.

## Czego patcher jeszcze nie robi

- nie kopiuje pliku do instalacji gry ani nie robi backupu — to robi skrypt
  uruchamiany przez użytkownika,
- nie obsługuje map `_diff` (nakładka LDP) — tylko mapę główną EN,
- nie sprawdza, czy gra przyjmie plik (test u użytkownika).

## Wynik na realnej mapie

Mapa EN 50 550 179 B, 4386 tabel tekstów, 1 122 784 wpisy: 200 podmian,
11 s, wynik 51 904 280 B, weryfikacja 1 122 784 id / 200 zmian. Struktura
wyniku przechodzi `tools/locale_container.py`.
