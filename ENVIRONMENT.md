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
Dysku Google ani sekretów. Pokrycie przekładu (co w grze zostanie po angielsku)
mierzy read-only `python3 tools/pokrycie_tlumaczenia.py` — czyta tylko `index/`
i `tlumaczenie/`, bez `zstandard` i bez plików gry. `run_tests.py` zwraca błąd również wtedy, gdy nie
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

**Budowanie czyta wyłącznie pliki z repozytorium.** Czytanka
(`tools/czytanka_czysta.py`), paczka dla tłumacza (`tools/buduj_paczke.py`),
łatka (`tools/zbuduj_latke.py`, `tools/one_click_patch.py`) i instalator
(`tools/build_installer_kit.py`) biorą wszystko z `index/`, `tlumaczenie/`
i `zwrotki/` — **nie** z `google_drive/`, nie z `local/` i nie z Dysku.
**Dysk Google, connector `download_file`:** zapisuje plik **na dysk sandboxa**
(`google_drive/<nazwa>`, ścieżka w wyniku narzędzia). **Nie** wkleja bajtów
do rozmowy i **nie** zwraca base64 do kontekstu. `curl`/`wget` na
`drive.google.com` w sandboxie nie działa (sieć tylko GitHub/npm/PyPI).
Potrzebny plik z Dysku → `download_file` → praca z `google_drive/…` → wynik
indeksu/mapy do Gita; binarki gry zostają poza Git. Spis paczek:
`index/paczki.json`, `docs/PLIKI_W_PACZKACH.md`. Rozpakowanie:
`python3 tools/spis_paczek.py --zrodlo google_drive --rozpakuj local/dane`.

Pliki z Dysku (baza gry, paczki aktualizacji) są **tylko** materiałem do
inwestygacji: czytają je narzędzia `tools/szukaj_w_bazie.py`,
`tools/cutsceny_z_bazy.py`, `tools/pamiatki_z_bazy.py`, `tools/poi_z_bazy.py`
i `tools/kolejnosc_gry.py` (ten ostatni importuje bazę dopiero w funkcji,
więc nie ciągnie jej do budowania). Pilnuje tego
`tests/test_budowanie_standalone.py`.

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
