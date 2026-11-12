# Wstępny zbieracz Where Winds Meet — Windows

## Co to jest

Odczytowy zestaw do rozpoznania instalacji i zbierania cotygodniowych
aktualizacji gry: rozpakuj ZIP, uruchom `URUCHOM.bat` (pierwsze rozpoznanie)
albo `URUCHOM_AKTUALIZACJE.bat` (pliki po patchu gry), otrzymaj ZIP na
Pulpicie i przekaż go prywatnie. Windows PowerShell 5.1 jest składnikiem Windows; użytkownik nie
instaluje Pythona, zależności ani niczego nie pobiera przez skrypt.

Na życzenie właściciela, po tym jak domyślna polityka wykonywania zablokowała
skrypt na jego komputerze, BAT uruchamia PowerShell z parametrem
`-ExecutionPolicy Bypass` — tak jak paczki SRW Y tego projektu. Parametr
obejmuje **tylko ten jeden proces**: nie zmienia polityki w rejestrze ani
ustawień systemowych, nie wymaga administratora i niczego nie instaluje.
BAT wykonuje też `Unblock-File` na plikach `*.ps1` w swoim folderze, żeby
znacznik „pobrane z internetu” nie blokował uruchomienia. To nie jest
obchodzenie zabezpieczeń gry; gra pozostaje tylko czytana. Zbieracz nie instaluje ani nie cofa tłumaczenia. Jest osobny od
planowanych [audytora i patchera](TWO_APPLICATIONS.md).

Właściciel wskazał wzorce SRW Y. W repozytorium `mtgcrawler` odnaleziono
[generator `build_kod_kit.py`](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/2b675b15e190248c47f0e30791b9dbbc46e08e04/srw-y-translation/tools/build_kod_kit.py).
Jego ZIP powstaje w ignorowanym katalogu, a nie jest śledzonym plikiem Git.
Odtworzenie generatora z tego commita dało ZIP 3 810 B zawierający instrukcję,
BAT i PowerShell. To inspiracja dla **obsługi**, nie dowód podobieństwa silników
ani formatu i nie kopia danych SRW. WWM ma własny wybór plików i ograniczenia.

## Instrukcja dla właściciela

1. Zamknij grę i poczekaj, aż Steam zakończy aktualizację. Rozpakuj otrzymany
   `WWM_ZBIERZ_DANE.zip` do nowego folderu **poza grą**.
2. Kliknij dwa razy `URUCHOM.bat`. Program szuka Steam w rejestrze, sprawdza
   `libraryfolders.vdf` i manifest aplikacji `3564740`, także dla dodatkowych
   bibliotek. Przy kilku instalacjach poprosi o numer. Gdy nie znajdzie gry,
   otworzy okno wyboru folderu. Można też przeciągnąć główny folder gry na BAT.
3. Na Pulpicie powstaje `WWM_DANE_<data>_<losowy-id>.zip`. Okno pokazuje
   rozmiar i SHA-256; zostaje otwarte po zakończeniu. Przejrzyj archiwum, wgraj
   je na własny Dysk Google i daj znać. Jeśli stan jest **niepełny**, wyślij
   mimo to: raport zawiera powody pominięcia lub błędów. Jeśli ZIP ma ponad
   **100 MiB**, najpierw powiedz o tym: aktualne połączenie do Dysku ma limit
   104 857 600 B na pobranie i nie obiecujemy, że duży ZIP da się odebrać.
4. Jeśli ZIP w ogóle nie powstał, przekaż komunikat z okna; nie wysyłaj haseł.
   Każde uruchomienie ma inną nazwę i nie nadpisuje starszych wyników.

## Dostawa archiwum

Gotowy ZIP nie zawsze da się przekazać przez connector Dysku Google: 2026-11-11
filtr bezpieczeństwa dostawcy connectora odrzucił to archiwum („blocked because
of its content”), choć paczki `SRW_Y_*_PROSBA.zip` o tym samym układzie
instrukcja + BAT + PS1 przechodzą. Różnica jest w treści skryptu: 25 KB,
`Get-Process`, odczyt rejestru Steam, kopiowanie plików, SHA-256 i tworzenie
ZIP-a — kombinacja heurystycznie podejrzana, mimo że operacja jest odczytowa.
Nie zmieniamy treści po to, by ominąć filtr.

Bez Pythona i bez nowej publikacji te same bajty daje archiwum repozytorium:
pobierz `https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/archive/refs/heads/main.zip`,
rozpakuj poza grą i uruchom `collector/URUCHOM.bat`. Git ma dla `.bat`/`.ps1`
ustawione `-text`, a sprawdzenie archiwum z `main` dało SHA-256 `zbierz.ps1`
`dd9c1ecf235ca9702c4a1ad12d24ff742ddfc3950ba007b01b785bfd94e25ce4` i identyczny
BOM/CRLF jak w repozytorium, więc to nie jest inna wersja narzędzia.

## Dokładny zakres

- `INWENTARZ.jsonl`: względne ścieżki, rozmiary i czas modyfikacji plików pod
  `Package` i `LocalData/Patch`, z limitem 250 000 pozycji. To nie pełny spis
  całej instalacji. Część nazw/katalogów o charakterze prywatnym jest pomijana,
  podobnie jak linki/reparse; problemy są zgłaszane. Bez pełnej ścieżki do
  instalacji, ale same względne nazwy mogą być wrażliwe.
- `pliki/`: kompletne kopie nazwanych map `translate_words_map_en` i
  `translate_words_map_zh_cn` oraz rozpoznanych wariantów `__small`, `_mobile`
  i `_diff`, znalezionych w katalogach `locale` obu skanowanych gałęzi.
  Dodatkowo dokładne nazwy `MANIFEST`, `data3` i `data205` bezpośrednio w
  `HD/oversea` lub `HD/v2`. Są to **kandydaci** z publicznych opisów, nie
  gwarancja pokrycia. Żadnych arbitralnie wskazanych plików ani całej gry.
- Priorytet ma główna mapa EN, następnie EN diff i inne EN, `MANIFEST`, mapy
  chińskie, a na końcu kandydaci `data3`/`data205`. Unikalne kopie mają łączny
  limit **90 MiB**, w tym najwyżej **20 MiB** na dwa ostatnie typy. Gdy plik się
  nie mieści, jest `skipped_limit`, a nie uciętą kopią. Dane o identycznym
  SHA-256 przechowuje się tylko raz; raport łączy wszystkie oryginalne ścieżki
  z daną kopią. Wszystkie kwoty dotyczą rozmiarów przed kompresją; sam ZIP może
  być większy niż limit odbioru ze względu na inwentarz i narzut.
- `RAPORT.json` zawiera stany skanowanych gałęzi, listę ośmiu znanych ścieżek
  i ich obecności/niedostępności, odkrytych kandydatów, rozmiary, SHA-256,
  powiązania z kopiami, błędy, limity i ograniczenia. `RAPORT.txt` streszcza
  wynik. Brak lokalizacji może być oznaczony `not_found_or_unavailable`, nie
  stwierdza więc pewnego braku, gdy dostęp zawiódł. Numer buildu Steam jest
  odczytywany z manifestu tylko w rozpoznanym układzie, nie dowodzi autentyczności.
- Nazwy i filtry nie są gwarancją prywatności: wynik może zawierać tekst i
  inne dane gry oraz prywatne nazwy. Nie przesyłać publicznie ani nie wkładać
  do Git. Zbieracz nie kopiuje celowo haseł, zapisów, logów, zrzutów, EXE/DLL,
  kopii zapasowych ani danych całej gry. Użytkownik powinien przejrzeć wynik.

Tworzony poza grą katalog tymczasowy jest usuwany po normalnym zakończeniu.
Awaryjne zamknięcie może go zostawić jako `.WWM_ZBIERANIE_*` na Pulpicie.
Program nie wykonuje wywołań sieciowych, lecz wybrany system plików może być
sieciowy lub synchronizowany. Na czas zbierania należy zatrzymać aktualizację;
kontrola rozmiaru, czasu i SHA-256 nie tworzy atomowej migawki, nie gwarantuje
odporności na wyścigi i nie potwierdza autentyczności. Znane nazwy procesów są
sprawdzane pomocniczo, ale nie jest to gwarancja wykrycia każdego klienta.

## Odbiór, walidacja i dalsza praca

Po otrzymaniu wyniku pobrać go **prywatnie** i przenieść do ignorowanego
`local/`. Przed analizą sprawdzić bez rozpakowywania:

```sh
python tools/validate_collector_return.py local/WWM_DANE_....zip
```

Walidator ogranicza rozmiary, odrzuca nieznane/niebezpieczne i podwójne wpisy,
sprawdza CRC podczas odczytu, SHA-256, rozmiary, powiązania i liczbę wpisów
inwentarza. Na ekranie pokazuje jedynie agregaty i stan `partial`/`collected`;
nie potwierdza autentyczności ani kompletności. Nie rozpakowuje archiwum.
Konieczne są prywatne dalsze oględziny zawartości i oddzielenie zgłoszeń od
ustaleń. Plików gry i prywatnych identyfikatorów nie wolno wrzucać do Git,
CI ani publicznego opisu PR. `local/` nie jest kopią zapasową.

Mapa skrót → tekst może nie zawierać źródła, mówców czy struktury scen;
publiczny [opis formatu](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/Obsidian-Vault/knowladge/Format-Spec.md)
wskazuje również kandydatów w `data*` i `MANIFEST`, lecz liczby i struktura
innej wersji nie potwierdzają instalacji właściciela. Po inwentarzu może być
potrzebny kolejny, dokładnie dobrany zbieracz. Wynik nie jest jeszcze
odczytanym tekstem, tłumaczeniem, patcherem ani testem w grze.

## Budowa i kontrole

Źródła są w `collector/`; projektowy Python buduje mały ZIP z samych narzędzi:

```sh
python tools/build_collector_kit.py --output artifacts/WWM_ZBIERZ_DANE.zip
python tools/run_tests.py
```

Archiwum ma stałe znaczniki czasu, sześć plików (`CZYTAJ_TO.txt`, `URUCHOM.bat`,
`URUCHOM_AKTUALIZACJE.bat`, `SPAKUJ_DANE.bat`, `zbierz.ps1`, `spakuj_dane.ps1`), brak kompresji
i jest czytane ponownie przy budowie. BAT jest ASCII/CRLF; PowerShell — UTF-8 BOM/CRLF.
Git ignoruje artefakty ZIP. Testy Windows wykonują **rozpakowane** BAT i
Windows PowerShell na fikcyjnej instalacji, a testy Linux sprawdzają builder,
kodowanie i walidator. Wynik dla konkretnego commita zob. w dzienniku i CI.
Nigdy nie nazywaj testów syntetycznych testem rzeczywistej gry.

## Uzupełnienie korpusu: `spakuj_dane.ps1`

`zbierz.ps1` ma z założenia limit payloadu 90 MB, więc nie uniesie całego korpusu:
same dialogi leżą w `Package/HD/oversea/data200`–`data212` (ok. 133 MB), a rejestr
`MANIFEST` wymienia 74 950 tabel dialogów (budowa bazy: [BAZA_GRY.md](BAZA_GRY.md)).

Do cotygodniowych patchy służy `URUCHOM_AKTUALIZACJE.bat` (`zbierz.ps1 -Tryb aktualizacja`),
który zbiera do jednego ZIP-a (<90 MiB, format `wwm-collection-v2`):
- potrzebne pliki z `LocalData/Patch/HD/oversea/` (`MANIFEST`, `data*`, `index*`, `locale/translate_words_map_{zh_cn,en}(_diff)`),
- `Package/HD/oversea/MANIFEST`, `data1001`, `data1200`, `index1001`, `index1200`,
- mapę źródłową `translate_words_map_zh_cn` oraz warstwy `_diff` wyłącznie dla `zh_cn` i `en` (wszystkie inne języki jak `de`, `es`, `fr`, `ja`, `ko`, `pt_br`, `ru`, `th`, `vi`, `zh_tw`, warianty `__small`/`_mobile`, katalogi `model/` i `bulk_data/` oraz pliki binarne/audiowizualne typu `.mpk`, `.bin`, `CameraZone.json`, `VirtualWindow.json`, `Audio_Area*` są na jawnej blackliście — natomiast pliki `index*` muszą pozostać, bo `baza_gry.py` wymaga ich do dekodowania schematów kolumn i offsetów rekordów w `data*`).

Gdy duża aktualizacja klienta zmieni też bazę `Package/HD/oversea/data*`
powyżej 90 MiB, służy osobny skrypt `spakuj_dane.ps1` (z wygodnym skrótem
dwukliku `SPAKUJ_DANE.bat`, który automatycznie szuka gry w Steam), który
**tylko czyta** katalog gry, zachowuje pełne ścieżki względne pod `pliki/`,
liczy SHA-256, zapisuje `SPIS.json`, stosuje tę samą czarną listę zbędnych
języków i zasobów i automatycznie dzieli wynik na części po ok. 85 MiB
(poniżej limitu 100 MiB pobierania z Dysku):

```powershell
# duża aktualizacja (domyślne: data*, index*, MANIFEST, mapy zh_cn/en i ich _diff, LocalData/Patch)
powershell -ExecutionPolicy Bypass -File .\spakuj_dane.ps1 -Gra "D:\...\Where Winds Meet" -Zakres duza_aktualizacja

# same dialogi (data200-data212 bez data205, ~133 MB w częściach <85 MiB)
powershell -ExecutionPolicy Bypass -File .\spakuj_dane.ps1 -Gra "D:\...\Where Winds Meet" -Zakres dialogi

# kontekst: pozostałe dataN, indexN, MANIFEST oraz LocalData/Patch (bez blacklistowanych plików)
powershell -ExecutionPolicy Bypass -File .\spakuj_dane.ps1 -Gra "D:\...\Where Winds Meet" -Zakres kontekst

# wszystko naraz (w częściach po ok. 85 MiB, z pominięciem blacklisty)
powershell -ExecutionPolicy Bypass -File .\spakuj_dane.ps1 -Gra "D:\...\Where Winds Meet" -Zakres wszystko
```

`-ExecutionPolicy Bypass` dotyczy tylko tego procesu — skrypt nie zmienia rejestru
ani polityki systemu, nie dotyka zapisów gry i nie zapisuje nic w katalogu gry.
