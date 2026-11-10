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
  W repozytorium nie ma danych gry ani tłumaczenia.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | Przygotowywane w pierwszym PR. |
| Rozpoznanie wersji, formatów, zasad gry i ryzyka | Nie rozpoczęto. |
| Ekstrakcja i zakres tekstów | Nie rozpoczęto; brak wiarygodnych liczników. |
| Pakiet tłumacza i import | Nie powstały. |
| Patcher, instalacja i przywracanie | Nie powstały; `runtime_tested: false`. |
| Czytanka i aktualizacje gry | Planowane; brak implementacji. |

## Otwarte ustalenia

1. Platforma, sklep/launcher, region i wersja gry właściciela; sposób ustalenia
   identyfikatora builda oraz obsługiwany zakres projektu.
2. Język źródłowy i ewentualne języki referencyjne dla tłumacza; zasady
   korzystania z istniejących tłumaczeń i praw do publikacji tekstu gry.
3. Tryby sieciowe, warunki korzystania z gry, integralność klienta i ewentualne
   zabezpieczenia oraz bezpieczny, dozwolony sposób testowania zmian.
4. Silnik, formaty, dostępne narzędzia, powierzchnie tekstowe, polskie glify
   i ograniczenia interfejsu — wszystko wymaga dowodu, nie analogii do SRW.

## Następny krok

Po ustaleniu platformy i wydania przeprowadzić osobny etap rozpoznawczy:
przejrzeć dostępne źródła, ocenić warunki i ryzyko, a następnie — tylko jeśli
potrzeba — poprosić o minimalny raport metadanych z instalacji. Najpierw
udokumentować pytania i kryteria powodzenia; nie żądać całej gry. Szczegóły
w [planie](ROADMAP.md).
