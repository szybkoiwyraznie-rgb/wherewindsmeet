# Dziennik eksperymentów i weryfikacji

Dopisuj wyniki chronologicznie. Dla każdej próby zapisz: datę, cel, rodzaj i
wersję wejścia, bezpieczny identyfikator/rozmiar/SHA-256, metodę lub polecenie,
wynik liczbowy, ograniczenia i następny krok. Nie publikuj prywatnych ścieżek,
sekretów ani identyfikatorów plików. Same planowane testy nie są wynikami.

## 2026-11-10 — przegląd wzorca i początek projektu

- **Wejście:** publiczne repozytorium `mtgcrawler`, commit
  `76f8471d13f2cef8700c703ab109de1962e7b8e8`; szczegółowe źródła w
  [PRIOR_ART.md](PRIOR_ART.md). Nie pobierano ani nie badano plików
  Where Winds Meet.
- **Metoda:** przegląd instrukcji agentów, planu wykonalności, importera,
  czytanki oraz workflow testów i wydań. Adaptacja praktyk, bez przenoszenia
  danych ani kodu SRW.
- **Wynik:** przyjęto model PR/checkpointów, lokalnej izolacji plików gry,
  testów bez prywatnych wejść i dokumentowania dowodów. Format gry, ryzyka,
  zakres tekstów i metoda patchowania pozostają nieznane.
- **Ograniczenie:** brak testu w grze, Windows, ekstrakcji i realnego
  tłumaczenia. Następny etap wymaga ustalenia platformy i wydania.

## 2026-11-10 — kontrole repozytorium na danych syntetycznych

- **Wejście:** pliki i indeks repozytorium oraz tymczasowe, syntetyczne
  repozytoria Git; bez plików gry, zwrotek i dostępu do Dysku.
- **Metoda:** `python3 tools/check_repository.py`, `python3 tools/run_tests.py`
  na Linux/Python 3.11 oraz walidacja schematu `.github/workflows/ci.yml`
  przez `@action-validator/cli` 0.6.0.
- **Wynik:** kontrola 22 wpisów indeksu poprawna; **15/15 testów**, bez
  pominięć. Sprawdzono m.in. ignorowane ścieżki, wymuszone dodanie pliku,
  rzeczywisty rozmiar obiektu w indeksie, linki dokumentacji i atrybuty
  Windows. Walidator schematu workflow zwrócił kod 0.
- **Ograniczenie:** nie jest to skan zawartości pod kątem sekretów ani praw do
  danych. Windows, Python 3.12 i wykonanie na GitHub Actions nie były częścią
  lokalnej próby; ich wyniki trzeba sprawdzić osobno.

## 2026-11-10 — GitHub Actions: macierz kontroli

- **Wejście:** repozytorium na commicie
  `bbd11be8b7947181f744400891d8869068f1e7ba`; publiczny przebieg CI
  [42842464649](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/42842464649).
- **Wynik:** 4/4 zadania zakończone sukcesem: `ubuntu-latest` i
  `windows-latest`, każde z Pythonem 3.11 i 3.12. Uruchomiono kontrolę indeksu
  oraz repozytoryjny zestaw testów; nie korzystano z plików gry.
- **Ograniczenie:** to test narzędzi repozytorium, nie gry, patchera ani
  instalacji. Przebieg dotyczy wskazanego commita; kolejne commity mają własne
  wyniki CI.
