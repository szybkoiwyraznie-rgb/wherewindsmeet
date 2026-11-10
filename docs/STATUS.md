# Stan projektu

Aktualizacja: **2026-11-10**. Jest to punkt wejścia dla kolejnej sesji; historię
szczegółowych prób zapisuj w [dzienniku](EXPERIMENT_LOG.md), nie w nieskończenie
rosnącym `AGENTS.md`.

## Co wiadomo

- Właściciel rozpoczyna nieoficjalną polską wersję *Where Winds Meet*. Chce
  procesu analogicznego do SRW Y: ekstrakcja → tłumacz → import i instalacja,
  później czytanka i obsługa aktualizacji. Celem jest Windows; gra nie jest
  jeszcze zainstalowana, a [rekomendowaną wersją startową jest Steam](WINDOWS_OPTIONS.md).
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
- Jest także [syntetyczny audyt aktualizacji i model cofania](UPDATES_AND_RESTORE.md).
  Audyt wymaga jawnego, niesprawdzonego założenia o porównywalności ID i zakresu;
  model nie sprawdza plików gry ani nie pozwala na zapis. Ani jeden, ani drugi
  nie stanowi gotowego narzędzia do aktualizacji czy odinstalowania WWM.
- Punktem odniesienia jest `mtgcrawler` w wersji opisanej w
  [PRIOR_ART.md](PRIOR_ART.md). Jego ustalenia dotyczące plików SRW nie są
  ustaleniami o Where Winds Meet.
- Przygotowano dokumentację, ochronę danych, kontrole i konfigurację CI.
  Publiczny [przegląd wykonalności](FEASIBILITY.md) wskazuje istniejące
  narzędzia oraz ograniczenia oficjalnych warunków gry. Nie badano jeszcze
  wydania właściciela; w repozytorium nie ma danych gry ani tłumaczenia.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | 97 testów lokalnych; 4/4 konfiguracje CI przeszły dla `08fa340`. Wyniki bieżącego commita sprawdzać osobno. |
| Rozpoznanie wersji, formatów, zasad gry i ryzyka | Windows wybrano; Steam rekomendowano. Instalacja, build, zakres warunków i zgodność narzędzi pozostają niepotwierdzone; jest [narzędzie metadanych](INVENTORY.md). |
| Ekstrakcja i zakres tekstów | Nie rozpoczęto; brak wiarygodnych liczników. |
| Pakiet tłumacza i import | Prototyp szablonu/walidacji wymyślonego JSON; brak ekstrakcji, importu, atomowego zapisu i integracji z grą. |
| Patcher, instalacja i przywracanie | Nie powstały; jest tylko fikcyjny model decyzji bez zapisu. `runtime_tested: false`. |
| Aktualizacje gry | Syntetyczny audyt małych źródeł; brak pamięci tłumaczeń, ekstrakcji i obsługi aktualizacji WWM. |
| Czytanka | Planowana; brak implementacji. |

## Otwarte ustalenia

1. Potwierdzenie instalacji Steam, regionu oraz wersji gry i Build ID; zakres
   planowanych testów dla tego klienta.
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

Kontynuować na próbkach syntetycznych: projekt strumieniowego indeksu, jawne
zatwierdzanie przekładów oraz odzyskiwanie po przerwaniu wieloplikowej zmiany.
Później potrzebne będą format i stabilność ID, dokładniejsze reguły tokenów oraz
bezpieczny import. Właściciel może zainstalować niemodyfikowaną grę ze Steam;
po instalacji przydadzą się wersja i Build ID. Przed rzeczywistymi plikami
uzgodnić konkretny plan, kopię oraz przywracanie, a dopiero jeśli to potrzebne —
minimalny raport metadanych.
Nie żądać całej gry ani poświadczeń. [Kontakt z wydawcą](PUBLISHER_PERMISSION.md)
jest opcjonalny; wybranego kierunku nie trzeba ponownie potwierdzać. Szczegóły
w [planie](ROADMAP.md) i [rozpoznaniu](FEASIBILITY.md).
