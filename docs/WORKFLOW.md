# Workflow projektu

## Git i PR

1. Sprawdź `git status --short --branch` oraz PR z bieżącej gałęzi, np.
   `gh pr list --state open --head "$(git branch --show-current)"` w powłoce
   POSIX. W Arena używaj wyłącznie gałęzi przydzielonej bieżącej sesji.
2. Jeśli PR jeszcze nie istnieje, zrób mały, sensowny checkpoint, wypchnij
   gałąź i od razu otwórz roboczy PR do `main`. Jeśli istnieje, kontynuuj go.
3. Dla każdego spójnego fragmentu obejrzyj indeks i diff, wykonaj kontrole z
   [ENVIRONMENT.md](../ENVIRONMENT.md), zrób commit i wypchnij gałąź. Przy
   niedokończonym kroku opisz ograniczenia. Sprawdź, czy PR wskazuje wypchnięty
   commit. Przed oczekiwaniem na użytkownika i na koniec tury nie zostawiaj
   pracy przeznaczonej do repozytorium tylko lokalnie.
4. W PR wpisz zakres, wyniki testów, ograniczenia i stan testów w grze. Nie
   scalaj ani nie zamykaj go bez prośby właściciela. Nie wykonuj force-push
   ani nie przenoś pracy na inną gałąź bez wyraźnej, dozwolonej instrukcji.
5. Jeśli brak dostępu do GitHub, zgłoś to jawnie. Przy błędzie uwierzytelniania
   poproś o ponowne połączenie GitHub w Arena; nie proś o sekrety.

Po istotnej zmianie zaktualizuj [STATUS.md](STATUS.md), a wynik badań i testów
zapisz w [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md). Rozróżniaj fakt, hipotezę,
test syntetyczny, test na kopii oraz test w prawdziwej grze.

## Przyszły obieg tłumaczenia

| Krok | Wejście → wynik | Bramka przed kolejnym krokiem |
|---|---|---|
| Rozpoznanie | platforma i build → raport faktów i ryzyk | zasady, prawa i bezpieczny sposób pracy wyjaśnione |
| Ekstrakcja | własne pliki gry → rekordy i manifest źródła | znana wersja, identyfikatory, kontekst i policzony zakres |
| Przekazanie | rekordy → pakiet dla tłumacza | czytelne instrukcje, manifest wersji, uzgodniony format |
| Zwrotka | partię tłumacza → zweryfikowane tłumaczenia | niezmienione źródła, poprawne znaczniki i atomowy import |
| Instalacja | zweryfikowane dane + własna zgodna gra → lokalny patch | kontrola builda, kopia, przywracanie i testy |
| Czytanka | przyjęte tłumaczenie + struktura źródła → dokument | dowody kolejności, jawne luki i raport |
| Aktualizacja | stary i nowy build → plan różnic | niepewne dopasowania i zmiany źródła wymagają przeglądu |

Format, języki, sposób instalacji i praktyki współpracy z tłumaczem wymagają
osobnych decyzji. Manifest ma pozwolić ustalić pochodzenie oraz wykryć zmianę
źródła; nie zastępuje kontroli praw do danych. Nie pomijaj błędów, by podać
lepsze liczby pokrycia.

## CI i przyszłe wydania

CI uruchamia kontrolę indeksu i testy bez danych gry dla PR do `main`, push na
`main` oraz ręcznego uruchomienia. Testy powinny być powtarzalne i bez pominięć.
CI ma tylko dostęp
`contents: read` i **nie publikuje** wydań.

Gdy powstanie patcher, zaprojektować osobno: build dla PR bez publikacji,
sprawdzenie zawartości i sum, bezpieczne opisy wydań bez prywatnych danych oraz
publikację dopiero po uzgodnionym przeglądzie. Wydanie ma zawierać narzędzia
oraz uprawnione dane tłumaczenia, nie kopię plików gry. Jest to plan, nie
istniejący workflow release.
