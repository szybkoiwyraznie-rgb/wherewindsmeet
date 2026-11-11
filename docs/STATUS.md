# Stan projektu

Aktualizacja: **2026-11-10**. Jest to punkt wejścia dla kolejnej sesji; historię
szczegółowych prób zapisuj w [dzienniku](EXPERIMENT_LOG.md), nie w nieskończenie
rosnącym `AGENTS.md`.

## Co wiadomo

- Właściciel rozpoczyna nieoficjalną polską wersję *Where Winds Meet*. Chce
  procesu analogicznego do SRW Y: ekstrakcja → tłumacz → import i instalacja,
  później czytanka i obsługa aktualizacji. Zgłosił instalację Steam na Windows:
  App ID `3564740`, Build ID `25906190`, `1.1.0.63833` na ekranie logowania i
  `1.0.332.63833` po załadowaniu. Są to [odrębne oznaczenia](STEAM_REFERENCE.md),
  nie dowód autentyczności plików ani ich zgodności z narzędziami.
- Preferuje własne tłumaczenie z dobrym modelem oraz tekst natywnie w grze;
  nakładka to plan awaryjny. Nie wykorzystujemy gotowego polskiego tłumaczenia
  Arimy ani innych niezweryfikowanych gotowych zwrotek.
- Właściciel poinformował, że według jego sprawdzenia zmiany czystego tekstu
  są dozwolone, i wybrał wyłącznie zmiany wartości tekstowych przy wyłączonej
  grze. Nie potwierdziliśmy niezależnie wyjątku w warunkach wydawcy; brak
  gwarancji bezpieczeństwa konta. Bez wstrzykiwania, zmian pamięci/kodu,
  podmiany podczas startu/gry ani obchodzenia zabezpieczeń.
- Jest [prototyp pakietu tłumacza](TRANSLATION_BUNDLE.md): szablon i walidacja
  fikcyjnych rekordów w wymyślonym JSON. Nie obsługuje formatu plików gry ani
  nie wykonuje importu; wykrywa wyłącznie jawnie zadeklarowane literały.
- Właściciel określił [dwie aplikacje Windows](TWO_APPLICATIONS.md): audytor
  wszystkich plików z kolejką nowych/zmienionych linii i patcher z jedną
  aktualną kopią na plik. Jest ogólny odczytowy skaner plików, testowany na
  sztucznych katalogach, oraz syntetyczne modele linii, cofania i rotacji kopii.
  Żaden nie został uruchomiony na grze ani nie potwierdza buildu, założeń o ID
  i zakresie czy autentyczności referencji. Brak gotowych ZIP-ów.
- Punktem odniesienia jest `mtgcrawler` w wersji opisanej w
  [PRIOR_ART.md](PRIOR_ART.md). Jego ustalenia dotyczące plików SRW nie są
  ustaleniami o Where Winds Meet.
- Przygotowano dokumentację, ochronę danych, kontrole i konfigurację CI.
  Publiczny [przegląd wykonalności](FEASIBILITY.md) wskazuje istniejące
  narzędzia oraz ograniczenia oficjalnych warunków gry. Nie badano jeszcze
  wydania właściciela; w repozytorium nie ma danych gry ani tłumaczenia.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | 165 testów lokalnych na Linux/Python 3.11; dla kodu `3ea3b36` oba przebiegi CI przeszły 4/4 konfiguracje Windows/Linux × Python 3.11/3.12. Wyniki bieżącego commita sprawdzać osobno. |
| Rozpoznanie wersji, formatów, zasad gry i ryzyka | Zgłoszono Steam na Windows oraz oznaczenia wersji. Faktycznych plików, formatu, warstw, zakresu warunków i zgodności narzędzi nie sprawdzono; są [proste oględziny](STEAM_REFERENCE.md). |
| Ekstrakcja i zakres tekstów | Nie rozpoczęto; brak wiarygodnych liczników. |
| Pakiet tłumacza i import | Prototyp szablonu/walidacji wymyślonego JSON; brak ekstrakcji, importu i integracji z grą. |
| Patcher, instalacja i przywracanie | Nie powstały; są jedynie syntetyczne modele cofania i rotacji kopii, bez zapisu. `runtime_tested: false`. |
| Aktualizacje gry | Skaner ogólnych plików oraz syntetyczny audyt i wybór linii; brak pamięci tłumaczeń, ekstrakcji i obsługi aktualizacji WWM. |
| Aplikacje Windows i czytanka | Planowane; ZIP-ów i czytanki nie ma. |

## Otwarte ustalenia

1. Region, ustawiony język, istnienie kandydackich katalogów i plików oraz
   zakres planowanych testów dla zgłoszonej instalacji Steam. Build ID i numery
   ekranów są zapisane jako zgłoszone, nie jako weryfikacja plików.
2. Język źródłowy/referencyjny, wybór modelu, koszty, prawo i warunki
   przetwarzania oraz publikacji tekstu gry. Nie używamy cudzej gotowej
   polonizacji jako źródła tłumaczenia.
3. Wpływ warunków gry i zabezpieczeń na wybraną edycję oraz techniczna
   wykonalność zmian wyłącznie tekstowych; ustalenie właściciela nie zostało
   przez nas niezależnie potwierdzone. Patrz [FEASIBILITY.md](FEASIBILITY.md).
4. Formaty w wydaniu właściciela, aktywne warstwy, powierzchnie tekstowe,
   polskie glify i ograniczenia interfejsu — raporty społeczności wymagają
   weryfikacji.
5. Licencja własnego kodu, dokumentacji i tłumaczeń. Nie wybrano jej i nie
   dodano pliku `LICENSE`.

## Następny krok

Poprosić o [oględziny nazw i rozmiarów w Eksploratorze](STEAM_REFERENCE.md):
dwa kandydackie katalogi, bez instalowania Pythona i bez przesyłania plików
lub pełnej ścieżki. Brak katalogu nie oznacza braku tekstów w grze. Zapytać
również o ustawiony język; nie zgadywać formatu ani aktywnej warstwy.

Równolegle można kontynuować prace syntetyczne: rozwinąć skaner do
strumieniowego indeksu, zaprojektować zatwierdzanie przekładów i odzyskiwanie
po przerwaniu wieloplikowej zmiany. Przed otwieraniem treści lub
modyfikowaniem rzeczywistych plików uzgodnić zakres, prawa, konkretny plan,
kopię i przywracanie. Nie żądać całej gry ani poświadczeń. [Kontakt z wydawcą](PUBLISHER_PERMISSION.md)
jest opcjonalny; wybranego kierunku nie trzeba ponownie potwierdzać. Szczegóły
w [planie](ROADMAP.md) i [rozpoznaniu](FEASIBILITY.md).
