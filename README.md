# Where Winds Meet — polska wersja językowa

Nieoficjalny projekt polskiej wersji gry **Where Winds Meet**. Chcemy zbudować
powtarzalny proces: teksty z gry → pakiet dla tłumacza → sprawdzony import →
polska wersja w grze. W planie są również czytanka i obsługa aktualizacji gry.

**Stan: rozpoznanie i organizacja projektu.** Celem jest Windows; jako pierwszą
wersję referencyjną rekomendujemy Steam. Właściciel nie zainstalował jeszcze gry.
Priorytetem jest własne tłumaczenie i natywny tekst w grze, a nakładka jest
planem awaryjnym. Właściciel wskazał kierunek ograniczony do zmian tekstu przy
wyłączonej grze; nie potwierdziliśmy niezależnie zakresu dopuszczalnych zmian.
Powstały prototypy [pakietu i walidacji](docs/TRANSLATION_BUNDLE.md) oraz
[audytu aktualizacji i modeli przywracania](docs/UPDATES_AND_RESTORE.md) na
wymyślonych danych. Właściciel wybrał [dwie aplikacje Windows](docs/TWO_APPLICATIONS.md):
audytor i patcher. Jest ogólny skaner SHA-256 testowany na sztucznych katalogach;
nie ma jeszcze ekstraktora, importera do gry, instalatora, archiwów aplikacji
ani czytanki. Działania na grze nie sprawdzono.

## Od czego zacząć

- [Stan i najbliższy krok](docs/STATUS.md)
- [Plan etapów](docs/ROADMAP.md), [rozpoznanie gry i ryzyka](docs/FEASIBILITY.md),
  [wybór wersji Windows i analiza narzędzi](docs/WINDOWS_OPTIONS.md),
  [raport metadanych](docs/INVENTORY.md), [prototyp pakietu tłumacza](docs/TRANSLATION_BUNDLE.md),
  [aktualizacje i cofanie](docs/UPDATES_AND_RESTORE.md),
  [dwie aplikacje Windows](docs/TWO_APPLICATIONS.md) oraz [sposób pracy](docs/WORKFLOW.md)
- [Środowisko i uruchamianie kontroli](ENVIRONMENT.md)
- [Zasady pracy z danymi gry](docs/DATA_POLICY.md)
- [Instrukcje dla agentów](AGENTS.md)
- [Źródła wzorców z projektu SRW](docs/PRIOR_ART.md)

Podstawowe kontrole repozytorium, bez instalowania bibliotek Pythona:

```sh
python tools/check_repository.py
python tools/run_tests.py
```

## Układ repozytorium

```text
.github/       CI i szablony współpracy
docs/          status, decyzje, plan i dziennik eksperymentów
tools/         kontrole, raport metadanych i prototypy na fikcyjnych danych
tests/         testy i syntetyczne przykłady bez plików gry
local/         prywatny katalog roboczy, ignorowany przez Git
build/         lokalne wyniki, ignorowane przez Git
```

Katalogi źródeł i tłumaczeń powstaną, gdy będzie znany format i zasady
przechowywania danych. Nie umieszczamy w Git plików binarnych gry ani gotowych
kopii zmodyfikowanych plików. Projekt nie jest powiązany z twórcami gry.
