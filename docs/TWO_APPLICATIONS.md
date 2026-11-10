# Dwie aplikacje Windows: audytor aktualizacji i patcher

To **uzgodniony kierunek produktu**, nie gotowe aplikacje. Właściciel chce dwie
paczki ZIP z uruchamianiem przez BAT: pierwsza wykrywa zmiany i przygotowuje
**tylko nowe teksty i zmienione linie**, druga instaluje i cofa spolszczenie.
Nie ma jeszcze ekstraktora WWM, kompletnego audytora, działającego patchera ani
archiwów ZIP. Jest ogólny, odczytowy skaner hashy do testów na sztucznych
katalogach oraz modele porównywania linii i kopii na wymyślonych danych; nie
zostały sprawdzone na instalacji gry.

## 1. Audytor — wszystkie pliki, potem tylko zmienione linie

Docelowo audytor uruchamiany z Windows ma kolejno:

1. Ustalić zakres: katalog instalacji **oraz pozostałe katalogi gry, jeżeli
   okaże się, że zawierają istotne warstwy**. Przeskanować wszystkie zwykłe
   pliki tego jawnego zakresu, a pominięte, niedostępne, nowe, usunięte lub
   zmienione nazwy wykazać osobno. Nie podążać bez kontroli za linkami i
   punktami reparse. Jeśli zakres jest niepełny lub trwa aktualizacja,
   powiedzieć o tym zamiast uznać raport za kompletny.
2. Strumieniowo policzyć SHA-256 i porównać ze stanem **ostatniego
   zainstalowanego patcha**, przy czym zachować też odrębny manifest
   **czystych oryginałów**. Ten sam plik może mieć różne oczekiwane hashe w
   obu manifestach. Dopiero pierwszy pełny skan zakłada punkt odniesienia;
   bez poprzedniego stanu nie można uczciwie zgłosić różnic po aktualizacji.
3. Dla plików o niezmienionych bajtach nie przebudowywać ich ani nie powtarzać
   ekstrakcji, jeśli istnieje sprawdzony cache dla tego samego zakresu,
   wersji parsera i ustawień. **Nie zmieniać pliku w grze.** Zmieniony plik
   sprawdzić i przetworzyć jego tekst; nowy, nieznany lub uszkodzony format
   zgłosić. Odcisk informuje o zmianie bajtów, ale nie mówi sam, czy plik
   zmieniła oficjalna aktualizacja, inny mod czy błąd.
4. Połączyć wyniki zgodnie z rozpoznaną kolejnością warstw. Gdy zmieni się
   warstwa zależna, może być konieczne ponowne obliczenie **wynikowych tekstów**
   również dla wcześniej odczytanych rekordów; można przy tym użyć ich cache
   bez ponownego odczytu lub zapisu niezmienionego pliku. Zmiana wersji parsera,
   zakresu lub niekompletny cache wymaga odpowiedniej ponownej analizy.
5. Porównać tekst według potwierdzonych ID wystąpień i linii, a nie samych
   scen. Do **kolejki aktualizacji** trafia cała nowa lub zmieniona linia,
   nie cały dialog i nie tylko zmienione słowo. Domyślnie dołączyć jedynie
   potrzebny kontekst (np. rolę lub nazwę sceny), a sąsiednie linie udostępnić
   jako opcjonalną referencję, nie jako kolejne zadania tłumaczenia. Identyczny
   tekst na nowym ID, niepewna tożsamość, zmieniony kontekst lub
   znaczniki trafiają do przeglądu, a nie do automatycznego przypisania.
   Nieprzetłumaczone albo nieznane linie z poprzednich wersji mają **osobny
   backlog**, nie są przedstawiane jako zmiany tej aktualizacji.
6. Przyjąć częściową zwrotkę względem dokładnego manifestu nowego źródła,
   sprawdzić ID, znaczniki i zgodność, a następnie zastosować zatwierdzone
   wyniki w przyszłym procesie budowy patcha. Niezmienione, zatwierdzone
   przekłady mają być ponownie używane zgodnie z polityką **bez ponownego
   wysyłania lub ręcznej kontroli każdego z nich**, gdy tożsamość, zakres,
   kontekst i znaczniki zostały potwierdzone. Niepewne przypadki pozostają w
   przeglądzie. Tego importu ani pamięci zatwierdzeń jeszcze nie ma.

**Granica linii nie jest dziś znana dla WWM.** Rekord źródłowy może zawierać
kilka wizualnych wierszy lub znaczniki układu. Nie wolno bez rozpoznania
mechanicznie dzielić go po `\n`: przyszły parser musi zachować granice,
identyfikatory i strukturę potrzebną do odtworzenia oryginalnego pola. Gdy nie
można wiarygodnie wskazać pojedynczej linii, oznaczyć przypadek do przeglądu,
nie udawać precyzji. Nie znamy też stabilności rzeczywistych ID między buildami.

Skan wszystkich bajtów kosztuje odczyt całej wybranej instalacji; czas zależy
od dysku i rozmiaru gry. Liczyć hashe blokami, pokazywać postęp i przechowywać
indeks lokalnie. Sam rozmiar lub data pliku nie są dowodem równości; można ich
użyć do wstępnej informacji, ale nie zamiast pełnego sprawdzenia przed zapisem.
SQLite/indeks dyskowy jest **propozycją**, jeszcze nie implementacją. W trakcie
skanowania zmiany plików/launchera są ryzykiem; kontrola przed i po odczycie
nie zastępuje rzeczywistego snapshotu ani blokady.

## 2. Patcher — jedna aktualna kopia każdego zmienionego pliku

W stanie ustalonym chcemy jedną kopię **najnowszego potwierdzonego oryginału**
dla każdego pliku objętego spolszczeniem, poza katalogiem gry. Patcher ma
pamiętać powiązane: instalację, build, rolę pliku i hashe oryginału, backupu
oraz zainstalowanego patcha. Hash działa tylko względem zaufanego manifestu;
sam nie dowodzi, że nowe bajty pochodzą od wydawcy. Źródło aktualnej referencji
trzeba dopiero opracować dla konkretnej wersji gry.

| Sytuacja | Planowana decyzja |
|---|---|
| Pierwsza instalacja, obecny plik = potwierdzony oryginał `O1` | Sprawdzić `O1`, sporządzić i zweryfikować kopię `O1`, następnie zainstalować `P1` po pełnym preflight. |
| Nowe tłumaczenie, ale gra się nie zmieniła: obecny plik = `P1` | **Nie robić backupu z `P1`.** Zachować zweryfikowane `O1` i przygotować nowy patch na jego podstawie. Gdy wynik jest bajt w bajt taki sam, nie ruszać pliku. |
| Gra zaktualizowała plik: obecny plik = potwierdzony oryginał `O2` | Przed podmianą przygotować osobną kopię `O2` i zweryfikować hash. Stare `O1` zachować do czasu pomyślnego zakończenia całej operacji i możliwości odzyskania po przerwaniu. Potem można bezpiecznie usunąć nieużywaną starą kopię. |
| Gra zostawiła w pliku poprzedni patch `P1` | Starego `O1` można użyć dla nowego buildu **wyłącznie**, gdy zaufana referencja potwierdzi, że właśnie `O1` jest oryginałem tego pliku w nowym buildzie. Inaczej zatrzymać i odzyskać właściwy oryginał, nie zapisywać `P1` jako backupu. Nawet po potwierdzeniu potrzebne są kontrola zależności i pełny preflight. |
| Brak lub niezgodna kopia, nieznany obecny plik, niepewny build albo niekompletny zakres | **Nie nadpisywać ani nie usuwać** plików. Zatrzymać całą operację i wyjaśnić rozbieżność. |

Po pomyślnej aktualizacji chcemy więc **jedną aktualną kopię na plik**, a nie
nieograniczoną historię. Tymczasowo podczas transakcji mogą istnieć dwie
wersje kopii. Starej nie kasować, jeżeli nadal wskazuje na nią manifest lub
niedokończony dziennik odzyskiwania, albo gdy wynik jest niepewny.

### Cofnięcie po aktualizacji gry

Przy potwierdzonym tym samym buildzie: jeśli aktualny plik odpowiada
zainstalowanemu patchowi, a kopia potwierdzonemu oryginałowi tego buildu,
może być kandydatem do przywrócenia; jeśli jest już oryginałem, pozostaje bez
zmian. Jeśli build się zmienił lub stan jest nieznany, bieżący model cofania
blokuje operację. Najpierw trzeba osobno ustalić aktualny oryginał i stan
wszystkich plików; nie zakładamy, że stary backup pasuje tylko dlatego, że
istnieje. Weryfikacja platformy może być jednym z narzędzi odzyskania, ale nie
jest gwarantowanym pełnym rollbackiem ani usunięciem obcych plików.

Przed jakąkolwiek przyszłą podmianą: wyłączona gra, pełny preflight wszystkich
plików i kopii, wersji, wolnego miejsca i ścieżek, przygotowanie wyników,
ponowne sprawdzenie i dziennik transakcji z odzyskiwaniem. `os.replace` może
być atomowe dla pojedynczego pliku na odpowiednim systemie plików, ale nie
czyni wieloplikowego patcha atomowym. Uruchomienie launchera lub aktualizacji w
trakcie pozostaje nierozwiązanym wyścigiem. Zasady szczegółowe:
[UPDATES_AND_RESTORE.md](UPDATES_AND_RESTORE.md).

## Planowane archiwa i konwencja SRW Y

Kształt jest docelowy, nazwy robocze; **ZIP-ów jeszcze nie zbudowano**.

```text
WWM_AUDYTOR.zip                 WWM_PATCHER.zip
  AUDYTUJ.bat                   PATCHER.bat
  skrypty/                      COFNIJ.bat
  CZYTAJ_TO.md                  SPRAWDZ.bat
                                skrypty/
                                CZYTAJ_TO.md
```

Jak w [opisie SRW Y](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/docs/OWNER_STEPS_S9_PATCHER.md):
rozpakowanie całej paczki i osobny dwuklik dla instalacji/cofnięcia; jasny
raport, weryfikacja SHA-256 i odmowa przy obcej wersji. Tamten projekt używa
BAT + PowerShell bez instalacji Pythona; dla WWM planujemy podobnie prostą
obsługę, ale zależności audytora i faktyczny format gry są jeszcze nieznane.
Nie skopiowano kodu ani danych SRW. Nie należy po cichu zmieniać ustawień
zabezpieczeń systemu. Jeśli powstaną skrypty Windows: BAT ASCII/CRLF, a
PowerShell 5.1 z polskimi komunikatami UTF-8 z BOM i CRLF; testować prawdziwe
uruchomienie na Windows, nie tylko bajty archiwum. Do ZIP-a nie trafią oryginalne
ani zmodyfikowane pliki gry.

## Dostępne prototypy — bez obsługi formatu WWM

Żaden z nich nie tworzy ZIP-ów, nie zmienia plików gry, nie kopiuje ani nie
usuwa plików i nie potwierdza buildu. Poniższy skaner **czyta bajty zwykłych
plików wskazanego katalogu**, a modele linii i kopii czytają testowe JSON-y.
Każdy wypisuje wynik na stdout; sam nie zapisuje plików.

### Ogólny skaner plików — testy na sztucznych katalogach

`tools/scan_file_changes.py` to pierwszy działający element przyszłego audytora,
nie kompletny audytor WWM. Rekurencyjnie czyta zwykłe pliki wybranego katalogu
blokami po 1 MiB, liczy SHA-256 i może porównać dwa prywatne wyniki: identyczne,
zmienione, dodane oraz nieobecne pod dawną ścieżką. Nie wyciąga tekstu i nie
stwierdza, że zmiana lub brak to na pewno oficjalna aktualizacja gry. Sam
program nie zapisuje ani nie usuwa plików, choć system operacyjny może zmienić
czas ostatniego dostępu podczas odczytu. Na razie testujemy go **wyłącznie na
sztucznych katalogach**, nie na instalacji WWM.

```sh
python tools/scan_file_changes.py --root <sztuczny-katalog>
python tools/scan_file_changes.py --root <sztuczny-katalog> --mode private
python tools/scan_file_changes.py --root <sztuczny-katalog> --previous <prywatny-wynik.json>
```

- Pierwszy skan bez `--previous` podaje `no_baseline`, nie wymyśla delty.
  Następny może użyć pełnego wyniku trybu `private` z poprzedniego przebiegu;
  plik tego wyniku musi być **poza skanowanym katalogiem**. W przykładzie
  `<...>` oznacza argument do zastąpienia, nie dosłowną nazwę pliku.
- `report` jest domyślny i ujawnia tylko liczniki/statusy, nie nazwy lub hashe
  plików. `private` zawiera względne ścieżki, rozmiary, hashe, problemy i listę
  zmian — to dane prywatne, nie publikować ich w Git/logach. Fingerprint
  lokalizacji może identyfikować instalację i nie jest zabezpieczeniem hasłem.
- **Samodzielny zapis stdout przez powłokę to zapis pliku:** nie przekierowuj go
  do katalogu skanowania ani do wcześniejszego wyniku/żadnego istniejącego
  pliku. Powłoka może go wyzerować jeszcze przed uruchomieniem skryptu.
  PowerShell 5.1 zapisuje `>` w UTF-16, którego czytnik JSON nie obsługuje;
  ewentualny prywatny plik musi być UTF-8 (z BOM lub bez). Testy przechwytują
  wynik procesu i zapisują go poza sztucznym katalogiem.
- Linki i punkty reparse są pomijane z błędem; link w samej ścieżce katalogu
  lub w jej rodzicach powoduje odmowę. Niedostępny/zmieniany plik, katalog,
  niereprezentowalna ścieżka lub przekroczony limit oznaczają `incomplete` i blokują
  porównanie, a nie generują fałszywej listy usunięć. Odmowę powoduje również
  inna lokalizacja względem poprzedniego wyniku. Kod wyjścia `0` oznacza
  poprawny skan/porównanie bez wykrytych problemów, **również przy braku
  baseline**; `2` oznacza niekompletność/blokadę, `1` — błędne wejście.
- Kontrole statystyk przed i po odczycie oraz ponowny przegląd ścieżek wykrywają
  część zmian w trakcie pracy, ale nie są atomowym snapshotem, blokadą ani
  ochroną przed wrogimi podmianami i wyścigami na Windows. `complete` oznacza
  brak wykrytych problemów, nie gwarancję spójnego obrazu. Nie sprawdza stanu
  gry/launchera, nie uwierzytelnia plików ani poprzedniego wyniku i nie
  upoważnia do zapisu. Pracuje w RAM, ma limit 250 000 wpisów i 64 MiB na wynik
  lub wczytany manifest; nie ma jeszcze paska postępu, cache ani wielu korzeni.

### Kolejka samych linii

```sh
python tools/audit_translation_lines.py --old-source tests/fixtures/synthetic_update_old.json --new-source tests/fixtures/synthetic_update_new.json --old-bundle tests/fixtures/synthetic_update_old_return.json --assume-comparable
python tools/audit_translation_lines.py --old-source tests/fixtures/synthetic_update_old.json --new-source tests/fixtures/synthetic_update_new.json --old-bundle tests/fixtures/synthetic_update_old_return.json --assume-comparable --mode delta
python tools/audit_translation_lines.py --old-source tests/fixtures/synthetic_update_old.json --new-source tests/fixtures/synthetic_update_new.json --old-bundle tests/fixtures/synthetic_update_old_return.json --assume-comparable --mode review
python tools/audit_translation_lines.py --old-source tests/fixtures/synthetic_update_old.json --new-source tests/fixtures/synthetic_update_new.json --old-bundle tests/fixtures/synthetic_update_old_return.json --assume-comparable --mode backlog
```

Dla przykładu: `delta` zawiera **2** linie — jedną zmienioną i jedną z nowym
tekstem. Istniejący tekst pod nowym ID, puste pola oraz zmiana samego kontekstu
trafiają do `review`, nie są automatycznie tłumaczone ani przenoszone.
`backlog` ma dwie wcześniejsze niewiadome/niepełne linie, nie zmiany
aktualizacji. `review` zawiera wcześniejsze teksty i przekłady; `delta` i
`backlog` także ujawniają teksty oraz **cały podany w wejściu kontekst** —
prototyp nie skraca go automatycznie. Nie wkładaj tam całych scen ani nie
kieruj wyników do publicznych logów.

Każdy `source` wejścia musi reprezentować **jedną** fikcyjną linię i nie może
zawierać znaków podziału wiersza. Nie dowodzi to, że rzeczywista gra udostępnia
linię w taki sposób. `--assume-comparable` jest niezweryfikowanym zapewnieniem
o pełnym zakresie i stabilnych ID. Obydwa wyniki `delta` i `backlog` są
częściowymi zwrotkami v1 związanymi z całym nowym źródłem; **nie przenoszą**
przekładów, nie zawierają statusu zatwierdzenia i nie są importerem. Dlatego
prototyp pokazuje także niezmienione przekłady jako niezatwierdzonych kandydatów;
nie należy mylić tego z docelową automatyczną obsługą zatwierdzonej pamięci.
Są ograniczone do 10 000 rekordów i 8 MiB na źródło.

### Model wymiany kopii

```sh
python tools/model_backup_refresh.py --recorded tests/fixtures/synthetic_restore_recorded.json --observed tests/fixtures/synthetic_restore_observed.json --new-reference tests/fixtures/synthetic_refresh_reference.json --assume-trusted-new-reference --details
```

Fikcyjny przykład pokazuje jeden niezmieniony patch i jeden potwierdzany
oryginał nowszej wersji: hipotetycznie pierwszą kopię można zachować, a drugą
przygotować do rotacji. `--assume-trusted-new-reference` to jedynie deklaracja
wywołującego; model nie sprawdza pochodzenia referencji, hashy, zależności ani
procesów. Wszystkie działania są **hipotetyczne**: nawet
`needs_further_preflight` ma `write_authorized: false` oraz
`old_backup_deletion_authorized: false`. Kod wyjścia `0` oznacza poprawne
obliczenie modelu, także przy blokadzie; nie używać go jako zgody na zapis.
Obserwacje niedostępne są `null`, nie oznaczają potwierdzonej nieobecności.
Model wymaga kompletnych, zgodnych zestawów plików i istniejącej zgodnej kopii;
nie modeluje pierwszej instalacji ani usuwania plików utworzonych przez patch.
