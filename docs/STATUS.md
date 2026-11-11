# Stan projektu

Aktualizacja: **2026-11-11**. Jest to punkt wejścia dla kolejnej sesji; historię
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
  i zakresie czy autentyczności referencji. Brak gotowych ZIP-ów audytora i
  patchera; osobny [zbieracz](COLLECTOR.md) służy tylko rozpoznaniu.
- Na życzenie właściciela przygotowano [zbieracz Windows](COLLECTOR.md):
  instrukcja, BAT i PowerShell tworzą jeden ZIP z inwentarzem oraz wybranymi
  kopiami map i kandydatów kontekstu. Ręczne oględziny zostały odrzucone.
  Kompletność tekstów/kontekstu, aktualna instalacja i prawa pozostają nieznane.
  Na prośbę właściciela BAT przestał nadpisywać politykę wykonywania PowerShell;
  jeśli system blokuje skrypt, instrukcja zaleca przerwanie bez obniżania polityki.
  Zmiana przeszła CI na Linux/Windows × Python 3.11/3.12; nie testowano jej
  na komputerze właściciela ani na instalacji gry.
- Punktem odniesienia jest `mtgcrawler` w wersji opisanej w
  [PRIOR_ART.md](PRIOR_ART.md); odtworzono również ZIP z generatora
  `build_kod_kit.py`. Jego ustalenia o SRW nie są ustaleniami o WWM.
- Przygotowano dokumentację, ochronę danych, kontrole i konfigurację CI.
  Publiczny [przegląd wykonalności](FEASIBILITY.md) wskazuje istniejące
  narzędzia oraz ograniczenia oficjalnych warunków gry. Nie badano jeszcze
  wydania właściciela; w repozytorium nie ma danych gry ani tłumaczenia.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | 180 testów lokalnych Linux/Python 3.11; kod zbieracza `075c8ab` przeszedł 4/4 konfiguracje CI Windows/Linux × Python 3.11/3.12. Zmiana polityki PowerShell również przeszła 4/4 konfiguracje push i PR; [dziennik](EXPERIMENT_LOG.md). |
| Rozpoznanie wersji, formatów, zasad gry i ryzyka | Zgłoszono Steam na Windows oraz oznaczenia wersji. Faktycznych plików, formatu, warstw, zakresu warunków i zgodności narzędzi nie sprawdzono; jest [zbieracz](COLLECTOR.md). |
| Ekstrakcja i zakres tekstów | Nie rozpoczęto; brak wiarygodnych liczników. |
| Pakiet tłumacza i import | Prototyp szablonu/walidacji wymyślonego JSON; brak ekstrakcji, importu i integracji z grą. |
| Patcher, instalacja i przywracanie | Nie powstały; są jedynie syntetyczne modele cofania i rotacji kopii, bez zapisu. `runtime_tested: false`. |
| Aktualizacje gry | Skaner ogólnych plików oraz syntetyczny audyt i wybór linii; brak pamięci tłumaczeń, ekstrakcji i obsługi aktualizacji WWM. |
| Aplikacje Windows i czytanka | Docelowe ZIP-y audytora i patchera oraz czytanka są planowane; wstępny ZIP zbieracza jest osobnym narzędziem. |

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

Przekazać sprawdzony [zbieracz ZIP](COLLECTOR.md). Właściciel uruchamia BAT i
sam wgrywa jeden wynik na Dysk Google. Odebrać go prywatnie do ignorowanego
`local/`, zweryfikować bezpiecznie raport, sumy i zakres, a następnie rozpoznać
format oraz luki kontekstu; nie obiecywać, że same mapy wystarczą. Pamiętać o
limicie 100 MiB odbioru przez aktualne połączenie Dysku. Nie prosić o ręczne
spisywanie plików, całą grę ani poświadczenia.

Równolegle można kontynuować prace syntetyczne. **Przed zapisem w instalacji**
uzgodnić prawa, konkretny plan, kopię i przywracanie; zgoda na zbieranie nie
zastępuje tych kroków. [Kontakt z wydawcą](PUBLISHER_PERMISSION.md) jest
opcjonalny. Szczegóły w [planie](ROADMAP.md) i [rozpoznaniu](FEASIBILITY.md).
