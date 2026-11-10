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
- Punktem odniesienia jest `mtgcrawler` w wersji opisanej w
  [PRIOR_ART.md](PRIOR_ART.md). Jego ustalenia dotyczące plików SRW nie są
  ustaleniami o Where Winds Meet.
- Przygotowano dokumentację, ochronę danych, kontrole i konfigurację CI.
  Publiczny [przegląd wykonalności](FEASIBILITY.md) wskazuje istniejące
  narzędzia oraz ograniczenia oficjalnych warunków gry. Nie badano jeszcze
  wydania właściciela; w repozytorium nie ma danych gry ani tłumaczenia.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | 34 testy lokalne; wcześniejsze 4/4 konfiguracje CI przeszły dla `3a0a60c`. Wyniki bieżącego commita sprawdzać osobno. |
| Rozpoznanie wersji, formatów, zasad gry i ryzyka | Windows wybrano; Steam rekomendowano. Instalacja, build, uprawnienia i zgodność narzędzi pozostają niepotwierdzone; jest [narzędzie metadanych](INVENTORY.md). |
| Ekstrakcja i zakres tekstów | Nie rozpoczęto; brak wiarygodnych liczników. |
| Pakiet tłumacza i import | Nie powstały. |
| Patcher, instalacja i przywracanie | Nie powstały; `runtime_tested: false`. |
| Czytanka i aktualizacje gry | Planowane; brak implementacji. |

## Otwarte ustalenia

1. Potwierdzenie instalacji Steam, regionu oraz wersji gry i Build ID; zakres
   planowanych testów dla tego klienta.
2. Język źródłowy/referencyjny, wybór modelu, koszty, prawo i warunki
   przetwarzania oraz publikacji tekstu gry. Nie używamy cudzej gotowej
   polonizacji jako źródła tłumaczenia.
3. Wpływ poznanych warunków gry i zabezpieczeń na wybraną edycję oraz
   zgoda/bezpieczny sposób testowania zmian; patrz [FEASIBILITY.md](FEASIBILITY.md).
4. Formaty w wydaniu właściciela, aktywne warstwy, powierzchnie tekstowe,
   polskie glify i ograniczenia interfejsu — raporty społeczności wymagają
   weryfikacji.
5. Licencja własnego kodu, dokumentacji i tłumaczeń. Nie wybrano jej i nie
   dodano pliku `LICENSE`.

## Następny krok

Zalecić niemodyfikowaną instalację Steam, ustalić build i sposób postępowania
wobec warunków gry; rozważyć [kontakt z wydawcą](PUBLISHER_PERMISSION.md).
Dopiero po uzgodnieniu, jeśli to potrzebne, poprosić o minimalny raport
metadanych. Kontynuować projekt na próbkach syntetycznych; nie żądać całej gry
ani poświadczeń. Szczegóły w [planie](ROADMAP.md) i [rozpoznaniu](FEASIBILITY.md).
