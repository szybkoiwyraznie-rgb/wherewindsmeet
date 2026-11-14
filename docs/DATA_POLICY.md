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
Właściciel wybrał niezależne tłumaczenie: nie używamy gotowej polonizacji Arimy
ani innych niezweryfikowanych cudzych zwrotek. Przed przekazaniem tekstów gry
zewnętrznemu modelowi ustalić prawa i zasady przetwarzania danych.

[Prototyp pakietu](TRANSLATION_BUNDLE.md) jest obecnie testowany tylko na
wymyślonych danych. Jego `prepare` wypisuje pełny tekst źródła i kontekst na
standardowe wyjście: nie uruchamiaj go na tekstach gry ani nie kieruj prywatnych
wyników do publicznych logów, PR lub śledzonych plików. Raport walidacji nie
zawiera tekstów ani ścieżek, ale zawiera wyliczone z danych skróty, które też
mogą służyć jako identyfikatory; przed udostępnieniem oceń ich wrażliwość.
Prototyp [audytu aktualizacji](UPDATES_AND_RESTORE.md) w trybach `todo` i
`review` wypisuje tekst i ID, a `review` także poprzednie przekłady. Model
przywracania w trybie `--details` wypisuje podane logiczne ID. Oba narzędzia
są przeznaczone wyłącznie do fikcyjnych danych, nie do publicznych wyników
zawierających prywatny materiał. Syntetyczny [model linii i rotacji kopii](TWO_APPLICATIONS.md)
w trybach `delta`, `review`, `backlog` i `--details` także ujawnia podane
teksty lub ID; jego manifestów nie należy mylić z bezpieczną referencją gry.
Odczytowy skaner hashy w trybie `private` ujawnia względne ścieżki, rozmiary,
hashe i pseudonim lokalizacji: jego wynik jest lokalny i prywatny, a sam
skaner na razie testowany wyłącznie na sztucznych katalogach.

Duże dane i generowane archiwa nie trafiają do Git bez uzasadnionej potrzeby.
Kontrola repozytorium odrzuca obecnie pliki większe niż 10 MiB w indeksie. Jeśli
w przyszłości większy, niebinarny materiał okaże się niezbędny, najpierw
uzgodnić przechowywanie i świadomie zrewidować tę regułę; nie omijać jej przez
`git add -f`. Submoduły także wymagają osobnego przeglądu i są na razie
odrzucane przez kontrolę indeksu.

## Decyzja właściciela z 2026-11-11: teksty i wyciąg z gry w repozytorium

Właściciel zdecydował, że do Git trafiają **teksty, indeksy, powiązania,
wnioski i dokumentacja, a poza Git zostają wyłącznie binarne pliki gry**
([CEL.md](CEL.md)). Powód: wyniki ekstrakcji żyły tylko w ignorowanym `local/`,
które jest regularnie czyszczone, a skrypty budujące paczki nie mogą zależeć
ani od `local/`, ani od plików przesyłanych prywatnym kanałem.

Stan od wersji `wwm-indeks-v2` (katalog `index/`, zapisuje go
`tools/wyciag.py`, czyta `tools/indeks.py`):

- `index/teksty_X.jsonl` — każdy unikalny tekst źródłowy **raz**: chiński
  oryginał i pomocnicza wersja angielska z gry; wszystkie inne pliki wskazują
  tekst kluczem (16 znaków SHA-256 tekstu źródłowego).
- `index/sceny_N.jsonl`, `zadania.jsonl`, `wybory.jsonl`, `postacie.jsonl`,
  `encyklopedia.jsonl`, `miejsca.jsonl` i pozostałe — sceny i powiązania.
- Każdy plik jest mniejszy niż 10 MiB (limit repozytorium); podział jest stały
  (pierwszy znak klucza, numer dialogu modulo 8), więc aktualizacja gry zmienia
  tylko wiersze, które się zmieniły. Żaden plik nie jest dodawany przez
  `git add -f`.
- Poprzedni indeks `wwm-indeks-v1` (same teksty chińskie, numer dialogu
  przesunięty o jedną scenę) został zastąpiony w całości.

Zapisany szczery warunek: **warunków wydawcy nie zweryfikowaliśmy
niezależnie**, a decyzja o publikacji tekstu gry (chińskiego i angielskiego)
należy do właściciela. Jeśli okaże się, że publikacji nie można utrzymać,
katalog `index/` usuwa się z repozytorium jednym commitem; narzędzia czytają
wyciąg z dowolnego katalogu (`--indeks`), więc działają także na kopii poza
repozytorium.

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
