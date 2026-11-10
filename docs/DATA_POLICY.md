# Dane gry, prywatność i Git

Repozytorium jest publiczne. Do Git **nie** trafiają oryginalne ani
zmodyfikowane pliki binarne gry: kontenery, wykonywalne pliki i biblioteki,
zasoby, archiwa gry, zapisy, zrzuty pamięci, kopie bezpieczeństwa ani gotowe
pliki gry po patchowaniu. Nie publikujemy też danych konta, czatu, sekretów,
prywatnych zrzutów ekranu ani linków i identyfikatorów prywatnych plików.
Nie należy prosić użytkownika o cały katalog gry ani o poświadczenia.

## Co może być wersjonowane

Kod, testy z wymyślonymi danymi, dokumentacja, małe manifesty oraz własne
narzędzia i tłumaczenia, o ile mamy prawo je publikować. W SRW Y właściciel
pozwolił także na tekstowe dane gry w repozytorium. To użyteczny wzorzec, ale
**nie przesądza praw ani zakresu publikacji dla Where Winds Meet**: przed
pierwszym publicznym commitem tekstu gry ustalić to z właścicielem i sprawdzić
właściwe warunki. Do tego czasu rzeczywiste ekstrakty trzymać prywatnie.

Duże dane i generowane archiwa nie trafiają do Git bez uzasadnionej potrzeby.
Kontrola repozytorium odrzuca obecnie pliki większe niż 10 MiB w indeksie. Jeśli
w przyszłości większy, niebinarny materiał okaże się niezbędny, najpierw
uzgodnić przechowywanie i świadomie zrewidować tę regułę; nie omijać jej przez
`git add -f`.

## Katalogi i wymiana

`local/` jest ignorowanym miejscem na prywatne wejścia; `build/`, `dist/` i
`artifacts/` — na wyniki. Ignorowane katalogi nie są backupem ani częścią
repozytorium. Większe materiały można przekazywać prywatnym kanałem uzgodnionym
z właścicielem. Do publicznego dziennika wpisuj tylko informacje, których
ujawnienie jest bezpieczne, np. wersję, rozmiar i SHA-256; prywatny identyfikator
lub ścieżka z nazwą użytkownika zostają w prywatnych notatkach. Nie umieszczaj
ich w publicznych logach CI i opisach wydań.

Przed każdym commitem:

1. Obejrzyj `git status --short` oraz `git diff --cached --name-status` i
   `git diff --cached`.
2. Uruchom `python tools/check_repository.py` **po dodaniu plików do indeksu**
   i `python tools/run_tests.py`.
3. Sprawdź, czy do commita ani wyników CI nie trafiły pliki gry, dane osobowe,
   sekrety lub prywatne identyfikatory.

`.gitignore` i kontrola indeksu blokują typowe ścieżki, rozszerzenia i duże
pliki. Nie rozpoznają całej zawartości: np. tekst gry lub sekret w `.json` czy
pliku `.md` może przejść kontrolę. Ręczny przegląd pozostaje obowiązkowy.
