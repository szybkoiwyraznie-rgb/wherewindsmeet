# Raport metadanych kandydatów lokalizacji

`tools/inspect_localization.py` jest małym narzędziem rozpoznawczym, nie
ekstraktorem ani patchem. Powstało na podstawie publicznie opisanych nazw plików
z [FEASIBILITY.md](FEASIBILITY.md); zgodność z instalacją właściciela **nie
została sprawdzona**. Właściciel wybrał zamiast ręcznych oględzin
[automatyczny zbieracz Windows](COLLECTOR.md), który nie wymaga Pythona i
kopiuje wybrane kandydaty. W [STEAM_REFERENCE.md](STEAM_REFERENCE.md) opisano
starszy skrypt dwóch lokalizacji, przetestowany tylko na sztucznych katalogach.
Ustalenie właściciela i zakres warunków: [FEASIBILITY.md](FEASIBILITY.md).

## Co robi, a czego nie robi

- Sprawdza wyłącznie dziewięć znanych nazw `translate_words_map_*` w **jednym
  wskazanym katalogu**. Nie przeszukuje dysku ani podkatalogów.
- Dla zwykłego pliku podaje nazwę kandydata oraz jego rozmiar. Nie otwiera
  zawartości plików, nie liczy hashy, nie czyta tekstu, nie uruchamia gry i
  nie modyfikuje danych. Skrypt nie wykonuje bezpośrednich wywołań sieciowych,
  ale system może użyć sieci, gdy wskazany katalog leży na zdalnym dysku.
- Nie umieszcza podanej ścieżki w raporcie ani obsłużonych błędach. Ścieżkę
  może jednak zapisać historia powłoki lub ujawnić lista procesów. Sprawdza
  tylko końcowy element ścieżki katalogu i kandydatów: pomija dowiązania i
  punkty reparse w tych miejscach, lecz system może przejść przez dowiązanie
  w katalogu nadrzędnym. To nie jest zabezpieczenie przed podmianą ścieżek.
- Brak dostępu lub nietypowy typ pliku daje wynik `incomplete`. Jeśli katalog
  jest niedostępny na końcu lub jego identyfikator różni się od początkowego,
  wyniki kandydatów są odrzucane jako `unknown`. Sprawdzenia nie są atomowe:
  mogą nie wykryć wszystkich zmian i nie stanowią migawki systemu plików.
- Nie ustala wersji, autentyczności, aktywnej warstwy, formatu, języka
  źródłowego, zakresu tekstu ani prawa do modyfikacji. `no_candidates` nie
  dowodzi, że w grze nie ma lokalizacji: mogła zmienić się nazwa lub katalog.

## Użycie po uzgodnieniu

Z katalogu repozytorium, po wskazaniu **katalogu lokalizacji**, a nie całego
folderu gry:

```sh
python tools/inspect_localization.py --locale-dir "ŚCIEŻKA_DO_KATALOGU_LOKALIZACJI"
```

Wynikiem jest JSON na standardowym wyjściu; skrypt nie zapisuje raportu ani nie
zmienia wskazanych plików gry. Python może utworzyć pliki cache modułów;
przekierowanie stdout może zapisać raport we wskazanym miejscu. Przed
ewentualnym przekazaniem raportu należy go obejrzeć. Publiczne źródła
opisują dla niektórych wydań PC podkatalogi `Package/HD/oversea/locale` i
`LocalData/Patch/HD/oversea/locale`, ale są to tylko tropy — nie wiemy, czy
istnieją w Twoim wydaniu, ani która warstwa jest aktualna.

Kody wyjścia: `0` — katalog sprawdzony (także gdy nie ma kandydatów), `1` —
wynik niepełny, `2` — błędne argumenty, niedostępny katalog, zwykły plik albo
link/reparse jako katalog wejściowy. `directory_state: matched_start_end`
znaczy tylko, że identyfikatory katalogu przy dwóch sprawdzeniach się zgadzały,
nie że stan pomiędzy nimi się nie zmienił. Narzędzie nie przyjmuje żadnych haseł,
tokenów ani danych konta. Raport nie zastępuje późniejszego, uzgodnionego
potwierdzenia wersji i pochodzenia plików.

## Testy

```sh
python tools/run_tests.py
```

Testy tworzą wyłącznie sztuczne katalogi i dane, m.in. blokują typowe funkcje
odczytu, listowania i tworzenia gniazd, sprawdzają ukrycie ścieżki, pomijanie
linków oraz niepełny wynik przy błędach i zmianie katalogu. Nie dowodzą
atomowości ani zachowania zdalnych systemów plików.
