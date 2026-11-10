# Stan projektu

Aktualizacja: **2026-11-10**. Jest to punkt wejścia dla kolejnej sesji; historię
szczegółowych prób zapisuj w [dzienniku](EXPERIMENT_LOG.md), nie w nieskończenie
rosnącym `AGENTS.md`.

## Co wiadomo

- Właściciel rozpoczyna nieoficjalną polską wersję *Where Winds Meet*. Chce
  procesu analogicznego do SRW Y: ekstrakcja → tłumacz → import i instalacja,
  później czytanka i obsługa aktualizacji.
- Punktem odniesienia jest `mtgcrawler` w wersji opisanej w
  [PRIOR_ART.md](PRIOR_ART.md). Jego ustalenia dotyczące plików SRW nie są
  ustaleniami o Where Winds Meet.
- Przygotowano dokumentację, ochronę danych, kontrole i konfigurację CI.
  Publiczny [przegląd wykonalności](FEASIBILITY.md) wskazuje istniejące
  narzędzia oraz ograniczenia oficjalnych warunków gry. Nie badano jeszcze
  wydania właściciela; w repozytorium nie ma danych gry ani tłumaczenia.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | 34 testy lokalne; wcześniejsze 4/4 konfiguracje CI przeszły dla `87ce177`. Wyniki bieżącego commita sprawdzać osobno. |
| Rozpoznanie wersji, formatów, zasad gry i ryzyka | Przegląd publicznych źródeł i [narzędzie metadanych](INVENTORY.md) gotowe; platforma właściciela, uprawnienia i zgodność narzędzi pozostają nieustalone. |
| Ekstrakcja i zakres tekstów | Nie rozpoczęto; brak wiarygodnych liczników. |
| Pakiet tłumacza i import | Nie powstały. |
| Patcher, instalacja i przywracanie | Nie powstały; `runtime_tested: false`. |
| Czytanka i aktualizacje gry | Planowane; brak implementacji. |

## Otwarte ustalenia

1. Platforma, sklep/launcher, region i wersja gry właściciela; sposób ustalenia
   identyfikatora builda oraz obsługiwany zakres projektu.
2. Język źródłowy i ewentualne języki referencyjne dla tłumacza; zasady
   korzystania z istniejących tłumaczeń i praw do publikacji tekstu gry.
3. Wpływ poznanych warunków gry i zabezpieczeń na wybraną edycję oraz
   zgoda/bezpieczny sposób testowania zmian; patrz [FEASIBILITY.md](FEASIBILITY.md).
4. Silnik i formaty w wydaniu właściciela, powierzchnie tekstowe, polskie glify
   i ograniczenia interfejsu — raporty społeczności wymagają weryfikacji.
5. Licencja własnego kodu, dokumentacji i tłumaczeń. Nie wybrano jej i nie
   dodano pliku `LICENSE`.

## Następny krok

Ustalić platformę, wydanie i sposób postępowania wobec ograniczeń warunków gry.
Dopiero potem, jeśli to potrzebne i uzgodnione, poprosić o minimalny raport
metadanych z instalacji. Nie żądać całej gry ani poświadczeń. Szczegóły w
[planie](ROADMAP.md) i [rozpoznaniu](FEASIBILITY.md).
