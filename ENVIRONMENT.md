# Środowisko projektu

## Wymagania obecnego etapu

- Git dostępny w `PATH`.
- Python 3.11 lub 3.12 do uruchamiania testów i opcjonalnych skryptów.
  Obecne kontrole używają wyłącznie biblioteki standardowej; nie trzeba
  instalować `pip`-em bibliotek ani mieć plików gry. Właściciel uruchamia
  [zbieracz Windows](docs/COLLECTOR.md) bez instalowania Pythona.
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
metadanych opisano w [docs/INVENTORY.md](docs/INVENTORY.md); aktualny
zbieracz, jego budowę i prywatny odbiór opisuje [docs/COLLECTOR.md](docs/COLLECTOR.md),
a oznaczenia Steam — [docs/STEAM_REFERENCE.md](docs/STEAM_REFERENCE.md). Prototyp pakietu
na wymyślonych danych opisuje [docs/TRANSLATION_BUNDLE.md](docs/TRANSLATION_BUNDLE.md),
a porównanie aktualizacji, odczytowy skaner plików oraz modele przywracania —
[docs/UPDATES_AND_RESTORE.md](docs/UPDATES_AND_RESTORE.md) i
[docs/TWO_APPLICATIONS.md](docs/TWO_APPLICATIONS.md). Skaner testujemy na razie
wyłącznie na sztucznych katalogach; nie jest ekstraktorem ani patcherem WWM.
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
bajty. Źródła `collector/` i `instalator/` mają CRLF, PowerShell ma UTF-8 BOM, a BAT jest ASCII;
buildery (`tools/build_collector_kit.py`, `tools/build_installer_kit.py`) i testy sprawdzają bajty w ZIP-ach. Windows CI uruchamia rozpakowane
skrypty na sztucznej instalacji; sama konfiguracja atrybutów nie jest testem
rzeczywistej gry.
