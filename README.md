# Where Winds Meet — polska wersja językowa

Nieoficjalny projekt polskiej wersji gry **Where Winds Meet**. Chcemy zbudować
powtarzalny proces: teksty z gry → pakiet dla tłumacza → sprawdzony import →
polska wersja w grze. W planie są również czytanka i obsługa aktualizacji gry.

**Stan: organizacja projektu.** Nie ma jeszcze ekstraktora, pakietu dla tłumacza,
patchera ani czytanki. Nie sprawdzono też działania w grze. Platforma, wydanie,
wersja i język źródłowy tłumaczenia wymagają ustalenia.

## Od czego zacząć

- [Stan i najbliższy krok](docs/STATUS.md)
- [Plan etapów](docs/ROADMAP.md), [rozpoznanie gry i ryzyka](docs/FEASIBILITY.md)
  oraz [sposób pracy](docs/WORKFLOW.md)
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
tools/         narzędzia projektu; na razie tylko kontrole repozytorium
tests/         testy bez plików gry
local/         prywatny katalog roboczy, ignorowany przez Git
build/         lokalne wyniki, ignorowane przez Git
```

Katalogi źródeł i tłumaczeń powstaną, gdy będzie znany format i zasady
przechowywania danych. Nie umieszczamy w Git plików binarnych gry ani gotowych
kopii zmodyfikowanych plików. Projekt nie jest powiązany z twórcami gry.
