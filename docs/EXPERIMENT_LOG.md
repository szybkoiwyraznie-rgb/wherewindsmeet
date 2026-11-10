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
