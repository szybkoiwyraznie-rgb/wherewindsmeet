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
  Po błędzie `running scripts is disabled` na komputerze właściciela BAT znów
  uruchamia PowerShell z `-ExecutionPolicy Bypass` (tylko dla tego procesu,
  bez zmian w systemie) i wykonuje `Unblock-File` na swoich `*.ps1`.
  Zmiana przeszła CI na Linux/Windows × Python 3.11/3.12; nie testowano jej
  na komputerze właściciela ani na instalacji gry.
- Punktem odniesienia jest `mtgcrawler` w wersji opisanej w
  [PRIOR_ART.md](PRIOR_ART.md); odtworzono również ZIP z generatora
  `build_kod_kit.py`. Jego ustalenia o SRW nie są ustaleniami o WWM.
- **2026-11-11 odebrano wynik zbieracza** (`WWM_DANE_20261111_181913_13ff7ac1.zip`,
  72 995 594 B, prywatnie w `local/`). Stan `partial` z powodu pominięcia mapy
  `zh_cn` (69 470 988 B) przez limit 90 MiB; 0 problemów odczytu, build
  `25906190` zgodny ze zgłoszonym. Inwentarz 640 plików w `Package`
  i `LocalData/Patch`. Mapy EN: główna 50 550 179 B plus dwa `_diff`
  (1 122 346 B z `LocalData/Patch`, 751 922 B z `Package`), `MANIFEST` ×2,
  `data3` 10 829 572 B, `data205` 7 564 939 B.
- **Rozpoznano kontener map** (szczegóły i liczby w
  [LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)): `0xDEADBEEF`, wersja 1, liczba
  chunków, tabela offsetów, chunki w zstd; po dekompresji jawny tekst z markupem
  gry. Zweryfikowano dekompresję 4386/4386 chunków mapy EN. Nie znamy jeszcze
  wiązania łańcuchów z kluczami ani zapisu zwrotnego.
- **Błąd zbieracza wykryty na realnym wyniku:** `CreateFromDirectory`
  w Windows PowerShell 5.1 zapisał nazwy wpisów z `\`, sprzecznie ze
  specyfikacją ZIP; walidator odrzucił archiwum (`unsafe archive member path`).
  Zamieniono na ręczne wpisy `ZipArchive` z `/` oraz dodano wyraźny komunikat
  walidatora. Dane w odebranym ZIP-ie były kompletne i zostały przeanalizowane.
  Wyjaśniono też, dlaczego test tej ścieżki padał **tylko** na Windows:
  `zipfile` podmienia `\` na `/` w nazwach wpisów przy zapisie i odczycie, więc
  walidator nie widzi tam separatora — paczkę i tak odrzuca, a wieloplatformową
  bramką są pola raportu `source`/`stored_as` czytane z JSON.
- **2026-11-11 odebrano dostawę `oversea` z Dysku Google** (4 pliki, największy
  96 942 617 B; inwentarz z SHA-256 w [OVERSEA_INWENTARZ.md](OVERSEA_INWENTARZ.md)):
  `oversea.zip`, `oversea2.zip`, `patch.zip`, `translate_words_map_zh_cn`.
  Wypakowanie do ignorowanego `local/`. Przyszły `data200`–`204` i `206`;
  `data200` nie ma `TimelinePObject`, a `data205` mamy z wcześniejszego
  zbieracza. Nadal **brakuje `data207`–`data212`**.
- **Nowe sceny:** 47 548 scen i 114 592 kwestii z `data201`–`206`
  (`tools/timeline.py`; wszystkie `text_id` unikalne, 12 920 różnych `entity_tag`).
  Rejestr `MANIFEST` z patcha ma 74 951 `dialog_timelines`; nowe sceny pokrywają
  **58,5%** (43 828 z `dialog_no`; wcześniej 10,1%), **brakuje 31 123 dialogów**.
- **Mapa źródłowa `zh_cn` rozpoznana:** ten sam kontener `0xDEADBEEF` co mapa EN
  (7097 chunków, zstd) — **1 816 408 niepustych** par `id → chiński tekst`
  (3 581 256 wpisów w nagłówkach). Nie same dialogi: także miejsca, imiona,
  przedmioty, interfejs, encyklopedia. Na 50 000 `text_id` ze scen **100%
  występuje w mapie**, 42 208 tekstów identycznych, 7 006 różni się tylko
  łamaniami wiersza.
- **Dopisek sceniczny w nawiasach (nowe):** 1 863 z 50 000 (3,7%) różni się
  treścią — mapa trzyma pełną linię z dopiskiem, scena tylko wypowiadany
  fragment: `（正声）咳咳，…` (1 055, sposób mówienia przed kwestią) oraz
  `喵喵喵喵！（…）` (322, myśl po kwestii). Który wariant renderuje klient —
  **do sprawdzenia w grze**.
- **Format dla tłumacza** gotowy: [format_tlumacza.md](format_tlumacza.md)
  (kolumny, przykłady z prawdziwych danych, zasada „tłumaczyć pełny tekst
  z mapy, nie zgadywać"). Język źródłowy decyzją właściciela: chiński.
- Przygotowano dokumentację, ochronę danych, kontrole i konfigurację CI.
  Publiczny [przegląd wykonalności](FEASIBILITY.md) wskazuje istniejące
  narzędzia oraz ograniczenia oficjalnych warunków gry. Nie badano jeszcze
  wydania właściciela; w repozytorium nie ma danych gry ani tłumaczenia.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | 242 testy lokalne Linux/Python 3.11; `check_repository.py` i `git diff --check` czyste. CI **4/4 zielone** (Ubuntu i Windows × Python 3.11/3.12) po naprawie testu odbioru paczki, który padał tylko na Windows; [dziennik](EXPERIMENT_LOG.md). |
| Rozpoznanie wersji, formatów, zasad gry i ryzyka | Zgłoszono Steam na Windows oraz oznaczenia wersji. Faktycznych plików, formatu, warstw, zakresu warunków i zgodności narzędzi nie sprawdzono; jest [zbieracz](COLLECTOR.md). |
| Ekstrakcja i zakres tekstów | Kontener map rozpoznany, parser par `id → tekst` działa (`tools/locale_records.py`): mapa EN 1 122 784 wpisy, mapa źródłowa `zh_cn` 1 816 408 niepustych. Sceny i mówce odczytane z `data201`–`206`. Nieznany jest zapis zwrotny do plików gry ani weryfikacja w grze. |
| Pakiet tłumacza i import | Format tabeli dla tłumacza gotowy (kolumny, kontekst sceny, zasada pełnego tekstu z mapy). Prototyp szablonu/walidacji wymyślonego JSON; brak ekstrakcji pełnej paczki, importu i integracji z grą. |
| Patcher, instalacja i przywracanie | Nie powstały; są jedynie syntetyczne modele cofania i rotacji kopii, bez zapisu. `runtime_tested: false`. |
| Aktualizacje gry | Skaner ogólnych plików oraz syntetyczny audyt i wybór linii; brak pamięci tłumaczeń, ekstrakcji i obsługi aktualizacji WWM. |
| Aplikacje Windows i czytanka | Docelowe ZIP-y audytora i patchera oraz czytanka są planowane; wstępny ZIP zbieracza jest osobnym narzędziem. |

## Otwarte ustalenia

1. Region, ustawiony język, istnienie kandydackich katalogów i plików oraz
   zakres planowanych testów dla zgłoszonej instalacji Steam. Build ID i numery
   ekranów są zapisane jako zgłoszone, nie jako weryfikacja plików.
2. Język źródłowy/referencyjny (decyzja właściciela: **chiński**, mapa `zh_cn`;
   angielski tylko pomocniczo), wybór modelu, koszty, prawo i warunki
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

Format jest odczytany w obie strony i **potwierdzony na realnej mapie**:
1 122 784 wpisy, `tools/apply_translation.py` podmienia teksty o dowolnej
długości, weryfikuje wynik i zapisuje nową mapę (200 podmian w 11 s).

Dalej: **uzupełnić brakujące 31 123 dialogi** (potrzebne `data207`–`212` albo
inne źródło — z `data201`–`206` pokrycie rejestru wynosi 58,5%), potem
**sprawdzić w grze**, który wariant linii z dopiskiem w nawiasach renderuje
klient, oraz **skrypt instalacyjny** dla użytkownika (kopiowanie, backup,
przywracanie).
