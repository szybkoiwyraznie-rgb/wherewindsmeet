# Środowisko projektu

## Wymagania obecnego etapu

- Git dostępny w `PATH`.
- Python 3.11 lub 3.12. Obecne kontrole używają wyłącznie biblioteki
  standardowej; nie trzeba instalować `pip`-em bibliotek ani mieć plików gry.
- GitHub CLI (`gh`) jest potrzebne do obsługi PR, nie do uruchomienia testów.

Lokalnie sprawdzono Linux i Python 3.11. W GitHub Actions przeszły również
kontrole na Windows i Pythonie 3.12 (szczegóły w `docs/EXPERIMENT_LOG.md`).
Wynik konkretnego kolejnego commita należy sprawdzić osobno w GitHub Actions.

## Kontrole z katalogu repozytorium

```sh
python --version
git status --short --branch
python tools/check_repository.py
python tools/run_tests.py
git diff --check
```

W Windows można zamiast `python` użyć np. `py -3.11`. Skrypt
`check_repository.py` sprawdza pliki **w indeksie Git**, więc nowe pliki trzeba
najpierw dodać do indeksu, aby je skontrolował. Testy nie korzystają z gry,
Dysku Google ani sekretów. `run_tests.py` zwraca błąd również wtedy, gdy nie
uruchomiono żadnego testu lub któryś test został pominięty. Oddzielne narzędzie
metadanych opisano w [docs/INVENTORY.md](docs/INVENTORY.md); zakres jego
późniejszego użycia na instalacji trzeba będzie uzgodnić. Prototyp pakietu
na wymyślonych danych opisuje [docs/TRANSLATION_BUNDLE.md](docs/TRANSLATION_BUNDLE.md).
Opcjonalne odtworzenie zewnętrznego eksperymentu syntetycznego ma osobne
zależności i ostrzeżenia w [dzienniku](docs/EXPERIMENT_LOG.md); nie jest częścią CI.

## Katalogi i wejścia

`local/`, `build/`, `dist/`, `artifacts/` i pobrane archiwa są ignorowane.
Używaj ich na własne, prywatne próbki i wyniki; nie są częścią działającego
clone'a ani CI. Nie umieszczaj poświadczeń w repozytorium ani w przykładach.
Dla przyszłych narzędzi zapisuj wersje i zależności w repozytorium, a przed
ich dodaniem sprawdzaj licencje. Konkretne biblioteki do gry nie są jeszcze
wybrane.

## Windows i końce wierszy

Dokumenty i kod tekstowy są domyślnie wersjonowane z LF. Zgodnie z praktyką SRW
pliki `.bat`, `.cmd` i `.ps1` są oznaczone `-text`: Git ma zachować zapisane
bajty, również w archiwum pobranym z GitHub. Gdy powstaną takie pliki, zapisz i
sprawdź w repozytorium CRLF; dla skryptów PowerShell 5.1 z polskimi znakami
sprawdź też UTF-8 z BOM. Sama konfiguracja atrybutów nie jest testem działania
na Windows.
