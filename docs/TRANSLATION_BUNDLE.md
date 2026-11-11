# Prototyp pakietu tłumacza — wyłącznie dane syntetyczne

To mały, niezależny od formatu gry prototyp: tworzy szablon zwrotki i sprawdza
ją względem osobnego źródła. Przykładowe zdania i identyfikatory są wymyślone;
nie pochodzą z *Where Winds Meet*. **Nie ma tu ekstrakcji, importu, instalacji
ani zapisu do gry.** Format JSON v1 jest formatem roboczym tego prototypu, nie
rozpoznanym formatem WWM ani obietnicą zgodności z przyszłym ekstraktorem.
Na tej samej podstawie powstały [syntetyczny audyt aktualizacji](UPDATES_AND_RESTORE.md)
i [wybór nowych/zmienionych linii](TWO_APPLICATIONS.md); nie importują zwrotek
ani nie przenoszą przekładów automatycznie.

## Uruchomienie przykładu

Python 3.11 lub 3.12; tylko biblioteka standardowa. Z katalogu repozytorium:

```sh
python tools/translation_bundle.py prepare --source tests/fixtures/synthetic_translation_source.json
python tools/translation_bundle.py validate --source tests/fixtures/synthetic_translation_source.json --bundle tests/fixtures/synthetic_translation_return.json
```

Pierwsze polecenie wypisuje cały szablon JSON, łącznie z tekstem i kontekstem.
Drugie wypisuje raport: w źródle są 3 fikcyjne rekordy, w zwrotce 2, z czego
1 ma tłumaczenie, 1 ma `null`, a 1 pominięto. `valid: true` oznacza tylko
pozytywną walidację tego formatu; `complete: false` i
`game_compatibility_verified: false` pozostają jawne.

Oba polecenia **czytają** pliki `.json`, ale nie zapisują ani nie zmieniają
plików: wynik trafia na standardowe wyjście. `prepare` ujawnia treść źródła;
nie stosuj go obecnie do tekstów gry ani w publicznych logach. W razie
samodzielnego zapisywania wyjścia nie nadpisuj źródła ani instalacji gry;
przekierowanie jest wykonywane przez powłokę, nie przez skrypt. Na Windows
PowerShell 5.1 może zapisywać przekierowanie jako UTF-16, natomiast prototyp
czyta tylko UTF-8 (z opcjonalnym BOM). Błędy nie zawierają przekazanych ścieżek
ani tekstów. Raport również ich nie zawiera, lecz jego skróty mogą identyfikować
dane — przed udostępnieniem oceń ich wrażliwość.

## Format źródła i szablonu

Pełny, testowy przykład znajduje się w
[`tests/fixtures/synthetic_translation_source.json`](../tests/fixtures/synthetic_translation_source.json).
Plik źródłowy jest obiektem zawierającym dokładnie:

- `schema`: liczba całkowita `1`;
- `source_id`: etykieta źródła, **nie** automatycznie sprawdzony numer buildu;
- `records`: niepusta lista rekordów. Każdy ma dokładnie `id`, `source`,
  `context` i `protected_tokens`.

`id` jest unikalny w źródle. Zarówno `id`, jak i `source_id` mają 1–256 znaków:
pierwszy to litera ASCII lub cyfra, pozostałe mogą zawierać litery ASCII,
cyfry oraz `._:/-`. `source` i `context` są napisami UTF-8. `protected_tokens`
to lista różnych, niepustych **dosłownych** ciągów obecnych w `source`; może
być pusta. Nie wnioskujemy, które ciągi w rzeczywistej grze są znacznikami.

`prepare` porządkuje listę tokenów, dodaje do każdego rekordu `source_sha256`
(SHA-256 bajtów UTF-8 napisu źródłowego) i `translation: null`, a do całego
pakietu `source_digest`. Wszelkie pola poza tłumaczeniem mają pozostać bez
zmian. Akceptowana jest część rekordów w dowolnej kolejności; duplikaty i
nieznane identyfikatory są błędem. `null` oznacza brak tłumaczenia, a brak
rekordu oznacza pominięcie **w zwrotce**, nie usunięcie go z gry. Puste lub
złożone wyłącznie z białych znaków tłumaczenie jest odrzucane.

Walidator przyjmuje osobno oryginalne źródło oraz zwrotkę i porównuje pełny
`source_digest`, identyfikatory, źródłowe teksty, konteksty, listy tokenów i
hashe rekordów. Dla każdego tłumaczenia porównuje liczbę wystąpień każdego
zadeklarowanego literału, również nakładających się wystąpień. Przy błędzie
zwraca kod niezerowy i nie wypisuje częściowego raportu; niczego nie importuje.

## Skróty i ograniczenia

- `source_digest` to SHA-256 kanonicznego JSON znormalizowanego źródła: klucze
  obiektów są sortowane, tokeny w rekordzie sortowane, kolejność rekordów jest
  istotna, a tekst kodowany jako UTF-8 bez normalizacji Unicode. Białe znaki
  formatowania i kolejność kluczy wejściowego JSON nie mają znaczenia.
- `bundle_digest` w raporcie wiąże raport z kanoniczną treścią zwrotki, w tym
  tłumaczeniami i kolejnością jej listy. To nie jest hash surowego pliku JSON.
  Oba skróty wykrywają zmiany względem **niezależnie zachowanego, zaufanego**
  źródła i ponownej walidacji. Nie są podpisami, nie dowodzą pochodzenia ani
  uprawnień, nie weryfikują buildu gry i nie chronią przed świadomą podmianą
  zarówno źródła, jak i zwrotki.
- Sprawdzane są **tylko zadeklarowane literały i ich liczba**. Brak lub błędna
  lista deklaracji, nowe niezadeklarowane znaczniki, struktura zagnieżdżeń,
  kolejność wymaganych elementów, semantyka, jakość przekładu, długość pola,
  czcionki i kodowanie wymagane przez grę nie są weryfikowane. Wynik pozytywny
  nie oznacza, że tekst da się bezpiecznie zapisać lub wyświetlić w grze.
- Wejściowy JSON źródła jest ograniczony do 8 MiB, zwrotka do 32 MiB, źródło
  do 10 000 rekordów, każdy tekst do 100 000 znaków, a lista do 256 literałów
  po maksymalnie 256 znaków. Istnieje również limit 16 777 216 jednostek pracy
  sprawdzania tokenów: suma długości tekstów pomnożonych przez liczbę ich
  tokenów, osobno dla źródła i dla par źródło/tłumaczenie. Większe dane trzeba
  dzielić; limity nie są limitami gry. Powtórzone klucze JSON, niepoprawny
  Unicode i niestandardowe liczby JSON są odrzucane.
- Nie istnieje jeszcze bezpieczny importer, zapis atomowy, powiązanie z
  potwierdzonym buildem ani przetestowane przywracanie. Właściciel wybrał
  [odczytowy zbieracz](COLLECTOR.md); modyfikowanie rzeczywistych plików nadal
  wymaga planu, kopii i przywracania. Zasady i stan projektu: [STATUS.md](STATUS.md),
  [DATA_POLICY.md](DATA_POLICY.md) i [FEASIBILITY.md](FEASIBILITY.md).
