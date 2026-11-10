# Instrukcje dla agentów — Where Winds Meet PL

To osobny projekt polskiej wersji **Where Winds Meet**, na bardzo wczesnym
etapie. Nie przenoś ustaleń o silniku, formatach, platformie ani języku
źródłowym SRW Y na tę grę. Wskazówki poniżej adaptują sposób pracy z
[`mtgcrawler`](docs/PRIOR_ART.md), nie jego dane ani kod patchera.

## Początek każdej sesji

1. Przeczytaj `README.md`, `ENVIRONMENT.md`, `docs/STATUS.md`,
   `docs/ROADMAP.md`, `docs/FEASIBILITY.md`, `docs/WORKFLOW.md`,
   `docs/DATA_POLICY.md` oraz ostatnie wpisy w `docs/EXPERIMENT_LOG.md`.
   Zajrzyj do `docs/PRIOR_ART.md` przed
   ponownym badaniem problemów już opisanych w źródłach.
2. Sprawdź bieżącą gałąź, `git status` i istniejący otwarty PR. Nie nadpisuj
   cudzych lub niezacommitowanych zmian. W Arena pracuj i wypychaj **wyłącznie
   na gałęzi przydzielonej bieżącej sesji**, nie na `main`; nie przełączaj jej
   ani nie twórz innej. Nie zakładaj, że stara nazwa gałęzi z dokumentacji nadal
   obowiązuje.
3. Jeśli nie ma PR z tej gałęzi, przygotuj najmniejszy sensowny checkpoint,
   wypchnij go i otwórz roboczy PR przed większą pracą. Wykorzystaj istniejący
   PR, jeśli jest. Commituj i wypychaj każdy spójny fragment pracy; przed
   końcem tury lub oczekiwaniem na użytkownika wypchnij wszystko, co nadaje się
   do repozytorium. Sprawdź sukces push i aktualny head PR. Nigdy nie scalaj
   ani nie zamykaj PR bez prośby użytkownika.
4. Przed commitem obejrzyj listę i diff plików w indeksie; uruchom kontrole z
   `ENVIRONMENT.md`. Nie dodawaj plików przez ślepe `git add -f`. Przy błędzie
   uwierzytelniania GitHub poproś o ponowne połączenie GitHub w Arena — nigdy
   nie proś o hasła, tokeny ani kody 2FA. Jeśli push lub PR jest niemożliwy,
   powiedz o tym wprost i nie przedstawiaj pracy jako wypchniętej.

## Zasady projektu

- Pliki gry, ich zmodyfikowane kopie, archiwa, zapisy i prywatne dane zostają
  poza Git. `.gitignore` i kontrola indeksu są tylko zabezpieczeniem pomocniczym,
  nie dowodem, że commit nie zawiera chronionych danych. Tekst i metadane mogą
  być wersjonowane po decyzji właściciela i sprawdzeniu praw; szczegóły w
  `docs/DATA_POLICY.md`.
- Zaczynaj od publicznych źródeł i minimalnych metadanych. Nie proś o cały
  katalog gry, dane logowania ani pliki, które nie są konieczne. Pliki wrażliwe
  trzymaj lokalnie; nie umieszczaj prywatnych linków ani identyfikatorów w
  publicznych opisach i logach.
- Platforma, wydanie i język źródłowy właściciela pozostają nieustalone;
  publiczne informacje o grze i istotne ograniczenia warunków są w
  `docs/FEASIBILITY.md`. Nie obiecuj zgodności z aktualizacjami ani
  bezpieczeństwa konta. Przed pracą na prawdziwej grze wyjaśnij zasady i ryzyko;
  nie obchodź zabezpieczeń ani anti-cheat. Nie modyfikuj instalacji użytkownika
  bez uzgodnionego planu, kopii i sposobu przywrócenia.
- Oddzielaj fakty, hipotezy i niewiadome. Dla badań zapisuj wejście, wersję,
  metody, liczby, hashe, wyniki i ograniczenia w `docs/EXPERIMENT_LOG.md`;
  `docs/STATUS.md` ma wskazywać aktualny stan i następny krok. Nie zgłaszaj
  testu w grze, Windows ani skuteczności patcha bez odpowiednich dowodów.
- Przyszły pakiet tłumacza, import, patcher i czytanka muszą mieć wiązanie z
  wersją źródła, testy na danych syntetycznych i jawne raporty. Nie dopasowuj
  niepewnego tłumaczenia ani kolejności zdarzeń przez zgadywanie. Błędy danych,
  tokenów lub niezgodności wersji mają zatrzymywać operację, nie powodować
  częściowego cichego zapisu.
- Nie uruchamiaj automatycznej publikacji, dopóki nie powstanie i nie zostanie
  sprawdzony bezpieczny proces wydawania. Nie publikuj danych gry ani surowych
  notatek zawierających prywatne identyfikatory.
