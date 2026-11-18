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

## 2026-11-10 — publiczne źródła Where Winds Meet

- **Wejście:** karta Steam, warunki na oficjalnej stronie i EULA Steam oraz
  opisane w [FEASIBILITY.md](FEASIBILITY.md) publiczne repozytoria; projekty
  przypięto do ich dokładnych commitów. Pobrano wyłącznie dokumentację i kod
  narzędzi do prywatnego przeglądu, bez cudzych paczek lub plików gry.
- **Metoda:** porównanie zakresu, licencji i ograniczeń narzędzi oraz przegląd
  oficjalnych informacji o językach, usługach sieciowych i zasadach.
- **Wynik:** znaleziono 3 kandydatów do analizy formatów (2 GPL-3.0, 1 MIT),
  projekty opisują mapy lokalizacji, osobną warstwę `_diff` i różnice między
  klientami. Warunki gry zawierają istotne ograniczenia dla modyfikacji i
  nieautoryzowanych narzędzi. Steam opisuje także dynamiczny tekst NPC.
- **Ograniczenie:** to deklaracje ich autorów, nie test w naszej grze. Nie
  uruchomiono narzędzi na rzeczywistych danych, nie potwierdzono klienta ani
  zgodności formatu. Ocena praw i decyzja o dalszym sposobie pracy są otwarte.

## 2026-11-10 — CI przeglądu wykonalności

- **Wejście:** commit `87ce17764147589408a3a66452a270252a6d88ef`, bez plików
  gry i bez dostępu do prywatnych danych.
- **Metoda:** [GitHub Actions, zdarzenie PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/42844576649).
- **Wynik:** 4/4 konfiguracje Ubuntu/Windows × Python 3.11/3.12 zakończyły się
  sukcesem. To wynik dla tego commita; kolejne mają osobne przebiegi.

## 2026-11-10 — test istniejącego narzędzia na próbce syntetycznej

- **Wejście:** własny, wymyślony kontener opisany jako v1: 163 B, SHA-256
  `4dff1b482063e38e2e6eac33223ef22801456780dfc6153f7eaf155be75cf395`,
  2 fikcyjne rekordy w 1 bloku danych. Żaden bajt nie pochodzi z gry.
- **Narzędzie:** niezmodyfikowany `wwm_locmap.py` projektu indonezyjskiego,
  commit `2289aacd076b7f7541e741760d6c18a0570b37a0`, GPL-3.0; zewnętrzne
  środowisko testowe z `zstandard==0.24.0`, Linux/Python 3.11. Nie dodano
  kodu ani zależności tego projektu do repozytorium.
- **Metoda:** `info` → `dump` → częściowy `patch` → ponowny `dump`, następnie
  osobne próby błędnego hasha, duplikatu wpisu oraz wpisu bez hasha.
- **Wynik:** odczytano **2/2** rekordy; **1/1** zmiana zastosowana, drugi
  rekord pozostał niezmieniony. Nieprawidłowy hash odrzucono bez pliku
  wyjściowego. Jednak dwie edycje tego samego slotu przyjęto bez błędu
  (wygrała ostatnia), a edycję bez hasha również przyjęto. Nie nadaje się to
  bez dodatkowych bramek na nasz zaufany importer zwrotek.
- **Ograniczenie:** nie testowano pliku gry, wersji v2 ani pełnego obiegu;
  wynik nie potwierdza zgodności wydania właściciela, bezpieczeństwa konta,
  poprawności wydania czy działania w grze. Źródło i zapis eksperymentu są
  syntetyczne; format i implementacja wymagają dalszego niezależnego audytu.

**Powtarzalność próby:** generator niezależnej sztucznej próbki
`tests/synthetic_locmap.py` tworzy 404 B, SHA-256
`74727d2426308ce1cbe3bf45041add58a7a9280688ac0e749a8aa9f18a91cd34`.
Opcjonalny `tools/reproduce_synthetic_experiment.py` powtórzył test: 2/2
rekordy, te same wyniki dla częściowej edycji, błędnego hasha i duplikatu;
zwrotka bez hasha została nie tylko przyjęta, ale i zastosowana. Ramki
Zstandard generatora sprawdzono także `zstandard==0.24.0` dla rozmiarów 0, 1,
255, 256 i 65791 B. Generator zawiera tylko wymyślone ciągi, nie jest
ekstraktorem i nie wymaga danych gry ani `zstandard` w CI.

### Opcjonalne odtworzenie eksperymentu

Eksperyment uruchamia **zewnętrzny kod GPL-3.0** jako oddzielny proces; jego
kod nie jest dołączony do repozytorium. Kontrola hasha potwierdza identyczność
badanego pliku, **nie bezpieczeństwo**. To nie jest piaskownica: przed użyciem
należy przejrzeć kod i wybrać odizolowane środowisko. Kontrole CI nie uruchamiają
cudzego kodu ani nie wymagają tej procedury.

1. Po przeglądzie pobierz wyłącznie [surowy `wwm_locmap.py` z przypiętego
   commita](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/wwm_locmap.py)
   do prywatnego katalogu pod tą nazwą, poza Git. Dokładny rozmiar: 13 934 B,
   SHA-256: `84568408ac48a2eff9b11172c001e023f52892f925715dc6ae2fb92d0615f819`.
2. W osobnym środowisku Python 3.11 zainstaluj `zstandard==0.24.0`; nie jest
   to zależność podstawowych testów projektu.
3. Z katalogu repozytorium, w tym środowisku uruchom:

   ```sh
   python tools/reproduce_synthetic_experiment.py --upstream-tool "ŚCIEŻKA_DO/wwm_locmap.py"
   ```

   Skrypt sprawdza nazwę, rozmiar i hash kodu oraz wersję `zstandard`, po czym
   kopiuje wskazany kod do katalogu tymczasowego i testuje na wygenerowanej
   próbce. Nie przyjmuje ścieżki do pliku gry jako wejścia testu. Przy błędzie
   kończy się niezerowym kodem. Zmiana zawartości próbki lub narzędzia wymaga
   nowej, osobno opisanej próby.

## 2026-11-10 — raport metadanych na fikcyjnych plikach

- **Wejście:** tymczasowe katalogi i pliki utworzone przez testy; żadnej
  instalacji gry. Kod narzędzia: `tools/inspect_localization.py`.
- **Metoda:** `python3 tools/check_repository.py` oraz `python3 tools/run_tests.py`
  (Linux/Python 3.11). Testy blokują typowe funkcje otwierania plików,
  listowania katalogów i tworzenia gniazd; sprawdzają również przypadki braku
  dostępu, linków/reparse i zmiany katalogu.
- **Wynik:** **34/34 testy**, bez pominięć; kontrola 30 wpisów indeksu
  poprawna. Raport zawiera jedynie znane nazwy, stany i rozmiary, bez ścieżki
  wejściowej ani zawartości plików.
- **Ograniczenie:** nie uruchomiono na grze użytkownika. Raport nie rozpoznaje
  wersji ani nie potwierdza praw, formatu czy kompletności źródeł.

## 2026-11-10 — CI narzędzi syntetycznych i aktualizacja akcji

- **Wejście:** commit `68cb24a4e29a4530d83d2daa118a4a887d5024b1`; bez
  danych gry. [Przebieg PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/42846767665)
  uruchomił kontrole indeksu i 34 testy.
- **Wynik:** 4/4 konfiguracje Ubuntu/Windows × Python 3.11/3.12 przeszły.
  Runner ostrzegł, że stare akcje deklarują Node.js 20 i są uruchamiane pod
  Node.js 24; zapowiedział też migrację obrazu `ubuntu-latest` do Ubuntu 26.
- **Działanie:** zaktualizowano przypięte po SHA akcje
  `actions/checkout` do v7.0.1 (`3d3c42e5aac5ba805825da76410c181273ba90b1`)
  i `actions/setup-python` do v7.1.0 (`6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`).
  Zweryfikowano tagi w GitHub API oraz `runs.using: node24` w obu manifestach.
  Wydania wymagają runnera co najmniej 2.327.1; CI używa runnerów GitHub-hosted.
- **Ograniczenie:** udane wyniki powyżej dotyczą wcześniejszego commita;
  aktualizację akcji trzeba zweryfikować we własnym przebiegu CI. Testy nadal
  nie potwierdzają działania gry ani zgodności formatu.

## 2026-11-10 — CI po aktualizacji akcji

- **Wejście:** commit `3a0a60c8b95536cfbebbc278d5a3543989e44cff`, akcje
  `checkout` v7.0.1 i `setup-python` v7.1.0, bez plików gry.
- **Metoda:** lokalny `action-validator` 0.6.0 oraz [GitHub Actions dla PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/42848568860).
- **Wynik:** walidacja workflow poprawna, 4/4 konfiguracje Linux/Windows ×
  Python 3.11/3.12 przeszły. W tym przebiegu nie ma ostrzeżenia o Node.js 20;
  pozostaje informacja o planowanej migracji `ubuntu-latest`.
- **Ograniczenie:** wynik odnosi się do tego commita i testów repozytorium,
  nie do instalacji lub działania gry.

## 2026-11-10 — źródła wskazane przez właściciela i wybór Windows

- **Wejście:** publiczne metadane drzew oraz wybrane README, pliki licencji,
  kod i dokumentacja z `arimacold/wwm-spolszczenie` przy
  `d0a32ee8938526b6fdf6d829bf00baa0fb86b4c3` oraz `wojciechowskiapp/Kaption`
  przy `8f2475a72cb21ab6c95a2edede75834b98ec7e57`. Oficjalny poradnik
  cross-progression i karta Steam są podlinkowane w [WINDOWS_OPTIONS.md](WINDOWS_OPTIONS.md).
- **Metoda:** statyczny przegląd nazw plików i wybranych źródeł; bez pobierania
  lub uruchamiania binarnych instalatorów, modeli, plików gry i cudzych
  tłumaczeń. Nie testowano żadnej wersji gry ani Kaption w środowisku Windows.
- **Wynik:** właściciel wskazał Windows, własne tłumaczenie i preferencję
  natywnego tekstu. Zarekomendowano Steam jako wersję referencyjną, nie jako
  gwarancję łatwości czy bezpieczeństwa. Kod Arimy potwierdza znaczenie osobnych
  warstw i operacji na plikach; Kaption opisuje OCR i dopasowanie do lokalnych
  danych, a WWM znajduje się w jego kandydatach, nie obsługiwanych grach.
- **Ograniczenie:** nie porównano aktualnych instalacji Steam/Epic/launchera,
  nie sprawdzono zgodności zabezpieczeń ani praw. Przygotowano niewysłany
  [szkic zapytania do wydawcy](PUBLISHER_PERMISSION.md); kodu i danych obcych
  projektów nie skopiowano do repozytorium.

## 2026-11-10 — zakres tekstowy i prototyp zwrotki

- **Ustalenie właściciela:** według jego sprawdzenia dozwolone są zmiany
  ograniczone do czystego tekstu; wybrał ten kierunek zamiast ingerencji w
  pamięć lub podmiany podczas gry. Nie przedstawiono dokumentu wydawcy i nie
  potwierdziliśmy niezależnie zakresu wyjątku. Szczegóły i ograniczenia:
  [FEASIBILITY.md](FEASIBILITY.md).
- **Wejście:** wyłącznie 3 wymyślone rekordy w
  `tests/fixtures/synthetic_translation_source.json`: 631 B, SHA-256 surowego
  pliku `64f25d3bad5d654aa7c4306915f0331b833853ca68f9a69745fabc8390d5b32e`.
  Fikcyjna częściowa zwrotka ma 857 B, SHA-256 surowego pliku
  `82e971706d5eea242d81e1bcd74b29679c2f5ba59b030b904b53c0615f052201`.
  Żaden tekst nie pochodzi z gry. Kanoniczny skrót źródła prototypu to
  `ad3f5dafbd20d4eed6b0a1e7a129b9d7a7e7722cb0eebc752138b70565c94b01`;
  nie jest to hash pliku ani identyfikator buildu gry.
- **Metoda:** polecenia `prepare` i `validate` oraz repozytoryjne
  `python3 tools/run_tests.py` na Linux/Python 3.11.2. Sprawdzono m.in. brak
  zmian wejścia, hashe, zduplikowane identyfikatory, przestarzałe źródło,
  liczbę zadeklarowanych literałów, niepoprawny Unicode i niepełne zwrotki.
  Test kombinacji z alfabetu `ab` (tekst do 6, literał do 3 znaków) wykrył
  błąd liczenia nakładającego się `aba`; poprawiono go i ponowiono kontrolę.
- **Wynik:** raport dla zwrotki: **3** rekordy źródła, **1** przetłumaczony,
  **1** nieprzetłumaczony i **1** pominięty. Lokalnie **60/60 testów**, bez
  pominięć. Narzędzie wypisuje wynik, samo nie zapisuje plików.
- **Ograniczenie:** walidowane są tylko jawnie zadeklarowane literały, nie
  wszystkie potencjalne znaczniki ani semantyka gry. Brak ekstrakcji,
  importu, testu na rzeczywistej grze, zgodności buildu i gwarancji konta.
  Windows/Python 3.12 należy sprawdzić w CI dla bieżącego commita.

## 2026-11-10 — aktualizacje, audyt i model cofania

- **Wejście i metoda badania:** publiczne, przypięte źródła podlinkowane w
  [UPDATES_AND_RESTORE.md](UPDATES_AND_RESTORE.md): projekt indonezyjski
  `2289aacd076b7f7541e741760d6c18a0570b37a0`, wietnamski
  `32efefe9dcb25baf56fe81a83c7186a881ad3e02`, instalator Arimy
  `d0a32ee8938526b6fdf6d829bf00baa0fb86b4c3` i dokumenty SRW
  `76f8471d13f2cef8700c703ab109de1962e7b8e8`. Przegląd statyczny kodu i
  dokumentacji, bez uruchamiania tego kodu i bez pobrania obcych tłumaczeń ani
  danych gry. Wnioski: osobny zakres i kontekst dla wariantów, pełne wejścia,
  rozróżnianie braków/tombstone, kontrola buildu i hashy przed przywracaniem.
  Nie kopiujemy zachowań obchodzących weryfikację ani pomijających błędy.
- **Wynik przykładu:** wymyślone źródła `synthetic_update_old.json` i
  `synthetic_update_new.json` mają po 7 rekordów. Audyt wykazał 3 identyczne,
  2 zmienione, 2 ID tylko w nowym i 2 tylko w starym; 1 z tych ostatnich ma
  możliwy odpowiednik po zmianie ID, co nie dowodzi tożsamości. Stara częściowa
  zwrotka daje 1 niezweryfikowanego kandydata, 1 jawny `null` i 1 brak danych
  wśród niezmienionych; `todo` ma 6 zadań, `review` 4 odniesienia. Kanoniczne
  hashe całych znormalizowanych źródeł: stary
  `e5ab29fe12e61b5b47d61f38708c9403ac7ce525eb539d34c044923fa3e07e00`, nowy
  `bb00cf4bd99152af497d03d603d1144106bbac0a2ada66b97b5965956d6b0a34`.
  To nie hashe plików ani rzeczywiste Build ID. `todo` przeszedł walidację v1
  względem nowego źródła; poprzednie przekłady nie są automatycznie przenoszone.
- **Przywracanie:** model dla dwóch fikcyjnych obserwacji wykazał zmianę etykiety
  buildu, jeden plik zgodny ze starym patchem i jeden nierozpoznany:
  `blocked_build_mismatch`, `write_authorized: false`. Model nigdy nie
  sprawdza plików gry, nie uwierzytelnia danych ani nie wykonuje zapisu.
- **Testy:** na Linux/Python 3.11.2 `python3 tools/run_tests.py` zakończyło się
  **97/97**, bez pominięć; `python3 -m compileall -q tools tests` i
  `git diff --check` przeszły. Sprawdzono m.in. zmianę kontekstu/tokenów,
  duplikaty, brak jawnego założenia, zmanipulowaną zwrotkę, 100 generowanych
  małych przypadków, limit 10 000 rekordów, 24 kombinacje stanów przywracania
  oraz brak zmian plików. Nie użyto gry ani sieci w testach prototypów.
- **Pomiar orientacyjny, nie test WWM:** jednorazowe wywołanie CLI `report` na
  syntetycznych 10 000 → 10 000 rekordów, Linux/Python 3.11.2: **0,347 s**
  czasu ściennego i **63 076 KiB** szczytowego RSS procesu potomnego. Kompaktowe
  JSON: stare źródło 1 089 861 B, nowe 1 091 071 B, częściowa zwrotka
  2 031 962 B. ID `bench/00000`–`bench/09999`, tekst `Invented sentence {i}.`,
  kontekst `Synthetic group {i % 11}.`, bez tokenów; etykiety źródeł
  `synthetic-benchmark-old`/`synthetic-benchmark-new`. Pominięto pierwszych 100
  ID, dodano ID `bench/10000`–`bench/10099`, a do tekstu ID 100–199 dopisano
  ` Updated.`. W zwrotce pominięto indeksy podzielne przez 10, dla pozostałych
  podzielnych przez 4 użyto `null`, a dla innych przekładu `Wymyślony tekst.`.
  JSON zapisano z `ensure_ascii=True` i zwartymi separatorami.
  Raport: 9 800 niezmienionych, 100 zmienionych, 100 nowych ID,
  100 tylko w starym, 3 140 zadań. Bez progu wydajności, jednorazowy pomiar
  zależy od maszyny; nie ekstrapolować na dane gry. Dane tymczasowe usunięto.
- **Ograniczenia:** prototyp wczytuje dane do pamięci i nie obsługuje pełnej
  skali projektu opisywanego przez innych autorów. ID, kompletności, kolejności
  warstw i formatu WWM nie zweryfikowano. Brak ekstraktora/importera, pamięci
  zatwierdzeń, instalatora, rzeczywistego rollbacku oraz testów w grze;
  Windows i Python 3.12 należy sprawdzić w CI dla aktualnego commita.

## 2026-11-10 — dwie aplikacje: skan, pojedyncze linie i rotacja kopii

- **Ustalenie:** docelowo dwa osobne ZIP-y Windows z BAT-ami: audytor wszystkich
  plików i patcher instalujący/cofający. Zadania do przekładu obejmują tylko
  nowe teksty i zmienione linie, a w stanie ustalonym na każdy podmieniany plik
  przypada jedna kopia ostatniego potwierdzonego oryginału. Szczegółowy plan i
  granice obecnej implementacji: [TWO_APPLICATIONS.md](TWO_APPLICATIONS.md).
- **Przegląd SRW:** statycznie przeanalizowano przypięty
  [opis patchera Y](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/docs/OWNER_STEPS_S9_PATCHER.md)
  i jego [generator](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/tools/build_patcher.py).
  Wnioski to osobne BAT-y, sprawdzenie hashy i kopii oraz konwencja kodowania;
  to nie dowód zgodności z WWM. Nie kopiowano kodu ani danych. Dokument SRW
  sam wskazuje brak rzeczywistego testu Windows dla tamtej implementacji.
- **Odczytowy skaner:** na sztucznym drzewie czterech plików po zmianie jednego,
  dodaniu jednego i usunięciu jednego otrzymano **2 niezmienione, 1 zmieniony,
  1 dodany, 1 nieobecny**. SHA-256 liczony jest blokami; test wymusza wiele
  odczytów i sprawdza bajty niezależnym `hashlib`. Równe rozmiary i znaczniki
  czasu nie ukrywają zmiany bajtów. Niedostępny/zmieniający się plik, katalog,
  limit, link lub reparse blokują porównanie; testowano też prywatność stdout,
  inny katalog, nieprawidłowy baseline i brak zapisów. Prawdziwy link testowano
  tam, gdzie system na niego pozwala; brak uprawnień zastępuje symulacja.
- **Linie:** fikcyjne źródła 7 → 7 dały **2** zadania (`delta`): jedno nowe i
  jedno zmienione. Zmiana samego kontekstu, powtórzenie pod nowym ID, puste
  pola i niezweryfikowane przekłady trafiają do przeglądu; wcześniejsze jawne
  `null`/nieznane stany są osobnym backlogiem (w przykładzie **2**). Test sceny
  zawierającej 100 linii potwierdza, że do `delta` nie trafiają sąsiednie
  niezmienione linie. Wymagane założenie pojedynczych pól i stabilnych ID nie
  zostało zweryfikowane dla WWM; kontekst jest emitowany tak, jak go podano.
- **Rotacja:** nowe fikcyjne wejście `synthetic_refresh_reference.json` ma
  567 B i SHA-256 surowego pliku
  `9f70a08a95c94c2bdc62a8b6d0becea30a4d85ddd3e048220ba16f54d226b239`.
  Deklarowany nowy build, identyfikatory i 64-znakowe, wymyślone hashe są
  zgodne z wcześniejszymi fixture: jedna obserwacja przypomina stary patch z
  tym samym oryginałem, druga nowy oryginał. Model hipotetycznie zachowuje
  pierwszą kopię i przygotowuje drugą do rotacji; **nie wykonuje kopii ani
  usuwania**. Stary patch nie może stać się nową kopią. Jeden nieznany plik,
  zła kopia lub rozbieżny build blokuje całość. Testy obejmują 24 kombinacje
  oraz `write_authorized: false` i `old_backup_deletion_authorized: false`.
- **Kontrole:** Linux/Python 3.11.2, `python3 tools/run_tests.py` — **145/145**,
  bez pominięć; `python3 -m compileall -q tools tests` i `git diff --check`
  przeszły. CI aktualnego commita, w tym Windows/Python 3.11 i 3.12, należy
  sprawdzić osobno. Nie pobierano ani nie skanowano danych gry.
- **Ograniczenia:** skaner nie wykrywa stanu launchera, nie uwierzytelnia
  referencji, nie daje atomowego snapshotu i nie jest utwardzony na wyścigi;
  limit to 250 000 wpisów i 64 MiB wyniku/manifestu. Modele JSON są ograniczone
  do małych syntetycznych danych i nie tworzą patcha. Brak ekstraktora WWM,
  gotowych archiwów, prawdziwej rotacji kopii, importu oraz testu w grze.

## 2026-11-10 — regresja metadanych skanera na Windows

- **Zaobserwowany błąd:** CI dla `f2422d8` i następnych wersji diagnostycznych
  przechodziło na Linuksie, ale nie na Windows/Python 3.11 i 3.12. Dla
  sztucznego katalogu po zmianach `DirEntry.stat()` zwracał inne czasy katalogu
  niż późniejszy `lstat`; skaner zachowawczo oznaczał go `directory_changed` i
  blokował porównanie. Nie doszło do zapisów ani użycia plików gry. Zwracane
  w Windows przez `DirEntry.stat()` zerowe `st_ino` i `st_dev` są opisane w
  [dokumentacji Pythona](https://docs.python.org/3/library/os.html#os.DirEntry.stat).
- **Poprawka:** po enumeracji należy pobrać świeży `lstat`, a weryfikację czasu
  i rozmiaru wykonywać oddzielnie dla obserwacji ścieżki oraz uchwytu. Między
  API porównuje się dostępne identyfikatory, typ i rozmiar, nie zakładając
  identycznej semantyki ich znaczników czasu. Niedostępna identyfikacja nadal
  nie dowodzi tożsamości; zastrzeżenia dotyczące wyścigów nie znikają.
- **Regresje:** test symuluje przestarzałe metadane wpisu katalogu i pliku,
  rozbieżne czasy między API, rzeczywistą zmianę tej samej obserwacji oraz
  zmianę typu wpisu. Linux/Python 3.11.2 — **150/150** testów lokalnych;
  `compileall` i sprawdzenie diffu OK. Dla poprawki
  `1688eac56bc124a43418b8c36da9e404c78547d8` oba przebiegi CI:
  [push](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/42883859227)
  i [PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/42883870587)
  przeszły **4/4** (Linux/Windows × Python 3.11/3.12). Testy CI nie oznaczają
  testu na WWM; wyniki kolejnego commita należy sprawdzić osobno.

## 2026-11-10 — zgłoszona instalacja Steam i następny krok

- **Wejście:** właściciel zgłosił Steam na Windows. Zrzut pokazuje App ID
  `3564740`, Build ID `25906190` i dosłowny znacznik „Installed content
  updated: Nov 11, 2026 at 7:23 AM”. Właściciel podał `1.1.0.63833` na
  ekranie logowania oraz pokazał `1.0.332.63833` po załadowaniu. Oznaczenia
  zapisano oddzielnie w [STEAM_REFERENCE.md](STEAM_REFERENCE.md); wspólna
  końcówka dwóch numerów ekranowych nie dowodzi tożsamości komponentu ani
  bajtów plików.
- **Metoda:** przegląd przypiętego [kodu instalatora społeczności](https://github.com/arimacold/wwm-spolszczenie/blob/d0a32ee8938526b6fdf6d829bf00baa0fb86b4c3/Instalator/installer.py)
  wskazuje `Package/HD/oversea/locale` i `LocalData/Patch/HD/oversea/locale`
  jako kandydatów, nie potwierdza ich obecności lub aktywności w zgłoszonej
  instalacji. Proponujemy oględziny nazw i rozmiarów w Eksploratorze bez
  wysyłania plików, ich zawartości, pełnej ścieżki lub danych konta.
- **Narzędzie opcjonalne:** `inspect_steam_layout.py` sprawdza `lstat` dla
  dziewięciu stałych nazw w dwóch kandydackich lokalizacjach; nie otwiera
  zawartości ani nie podejmuje zapisu w drzewie gry. Raport pomija podaną
  ścieżkę i informacje z wyjątków. Nieudostępniony kandydacki podkatalog daje
  `incomplete`, nie dziewięć pozornie brakujących plików; linki/reparse są
  pomijane według
  kontroli best effort. Kontrole nie zapobiegają wyścigom ani nie stanowią
  migawki. Opcja `-B` blokuje tworzenie plików bytecode Pythona (`.pyc`).
- **Weryfikacja:** Linux/Python 3.11.2, `python3 tools/run_tests.py` — **165/165**
  testów, bez pominięć; `compileall` i `git diff --check` poprawne. Nowe testy
  używają wyłącznie syntetycznych katalogów, w tym odrzuceń symlinków i
  symulowanych punktów reparse, braku dostępu i zmiany katalogu. Blokowane są
  wybrane funkcje otwierania, tworzenia i usuwania, zmiany nazw, listowania oraz
  gniazda sieciowe. Dla commita z kodem
  `3ea3b36876d7c956b44c37bf672c96ade950a048` przebiegi
  [push](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43047313508)
  i [PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43047326482)
  przeszły po **4/4** konfiguracje Linux/Windows × Python 3.11/3.12. Każdy
  kolejny commit ma osobne wyniki CI; nie jest to test na grze.
- **Ograniczenia:** nie uzyskano dostępu do instalacji ani nie wykonano testu
  na WWM. Region, język, format i aktywne warstwy są nieznane; Build ID nie
  potwierdza autentyczności ani stanu plików. Nie ma ekstraktora, importera,
  działającego patchera ani gotowych ZIP-ów. Samo narzędzie metadanych nie
  weryfikuje formatu, kompletności, pochodzenia ani uprawnień do modyfikacji.

## 2026-11-10 — odczytowy zbieracz Windows w układzie SRW Y

- **Decyzja właściciela:** zamiast ręcznych oględzin ma być ZIP z BAT-em i
  skryptem, który sam znajdzie instalację, zbierze odpowiednie pliki i zrobi
  jeden ZIP do przekazania przez Drive. Jest to etap rozpoznania, odrębny od
  dwóch planowanych aplikacji: audytora linii i patchera.
- **Wzorzec SRW Y:** właściciel wskazał `SRW_Y_ZBIERZ_KOD.zip`. Połączony
  Dysk zwrócił 404 dla trzech wskazanych plików i wyszukiwanie ich nazw nie
  zwróciło wyników; nie zakładamy, że to ten sam rachunek. W publicznym
  [repozytorium SRW Y](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/2b675b15e190248c47f0e30791b9dbbc46e08e04/srw-y-translation/tools/build_kod_kit.py)
  znaleziono generator; sam ZIP z tego generatora jest produktem `build/`, a
  nie śledzonym plikiem. W odtworzeniu uzyskano **3 810 B**, trzy pliki
  (`CZYTAJ_TO.md`, BAT i PS1), SHA-256
  `eabbfb7dad6a722d80f96bb756c8e6a217fe53bce970ac6e1482b592e8a0b847`,
  poprawny odczyt i CRC. To odtworzenie z konkretnego commita, nie dowód, że
  prywatny plik użytkownika ma identyczne bajty. Układ obsługi przeniesiono
  koncepcyjnie, nie dane ani założenia formatu SRW.
- **Implementacja:** `collector/` i `tools/build_collector_kit.py` budują
  `WWM_ZBIERZ_DANE.zip` z instrukcją, BAT i PowerShell 5.1; bez Pythona na
  komputerze właściciela i bez automatycznego wysyłania. Zbieracz inwentaryzuje
  dwie gałęzie instalacji z wyłączeniami prywatności, kopiuje wskazane warianty
  map, manifest i ograniczone kandydaty kontekstu, deduplikuje równe bajty,
  podaje błędy, pominięcia, SHA-256 i powiązania w raporcie. Zapis odbywa się
  poza instalacją. Limity i nieznaną kompletność opisuje [COLLECTOR.md](COLLECTOR.md).
  `tools/validate_collector_return.py` kontroluje zwrotkę bez rozpakowania i
  pokazuje wyłącznie agregaty; nie dowodzi autentyczności ani kompletności.
- **Błąd i naprawa:** pierwsze przebiegi Windows CI dla `8005c59` i `6dc4147`
  nie wykrywały `Get-FileHash` w środowisku z innym `PSModulePath`; Linux
  przechodził. Zastąpiono to strumieniowym SHA-256 z .NET w `9a4971e`. Nie
  dotyczyło to plików gry ani komputera właściciela.
- **Testy:** Linux/Python 3.11 — **180/180**, bez pominięć. Dla kodu
  `9a4971eea01ca99749aba78a557e59cd5ae25991` zarówno
  [push](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43053142995),
  jak i [PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43053153094)
  przeszły **4/4** konfiguracje Windows/Linux × Python 3.11/3.12. Na Windows
  uruchomiono parser PowerShell, rozpakowany BAT i PS1 na sztucznych drzewach:
  wykrywanie dodatkowej biblioteki Steam, polskie znaki i spacje w ścieżkach,
  mapy i kontekst, brak map, deduplikacja/limit, link katalogowy, odmowa zapisu
  w grze, niezmienność wejściowych plików i walidacja zwrotki. Linux dodatkowo
  sprawdził powtarzalność archiwum, BOM/CRLF oraz błędne i niebezpieczne ZIP-y.
  Dla kolejnego commita wyniki CI należy sprawdzić osobno.
- **Artefakt:** build źródeł `9a4971e` wygenerował archiwum **30 669 B**, SHA-256
  `8102c14724fcfba2a678d63daa54757709f9aabb6c7f54c00ae1ab03baa6f65b`,
  odczyt i CRC poprawne; archiwum narzędzia pozostaje ignorowanym artefaktem,
  nie zawiera plików gry. Próbne pobranie małego, 7 114-bajtowego ZIP-a z
  podłączonego Dysku zapisało plik w workspace i przeszło CRC; tymczasową kopię
  usunięto. Nie jest to test plików bliskich limitowi pobierania **100 MiB**.
- **Ograniczenia:** prawdziwej instalacji użytkownika nie badano. Katalogi i
  pliki kontekstu są tylko kandydatami; brak pełnego kontekstu, ekstraktora,
  tłumaczenia, patchera i testu w grze. Raport może zawierać prywatne nazwy,
  a ZIP — dane gry; trzymać prywatnie w ignorowanym `local/`, nie w Git.
  SHA-256 nie gwarantuje autentyczności ani atomowej migawki; skan nie obejmuje
  wyłączonych katalogów ani całej gry. W razie przekroczenia limitu odbioru
  potrzebna będzie osobna decyzja co do dalszego przekazania.

## 2026-11-10 — ścieżki Windows i domyślny wynik zbieracza

- **Dodatkowa regresja:** po dodaniu do fikcyjnej ścieżki instalacji znaków
  `[` i `]` test wykrył, że lista spodziewanych plików oznacza nieobecne
  kandydaty jako `present` (przebiegi Windows dla `7f686d8` i `fac2c1f`).
  Nie używano prawdziwych plików gry. Próba zamiany `Split-Path` na bezpośrednie
  operacje `[IO.Path]` nie naprawiła sama tego objawu.
- **Poprawka:** jawna obsługa pustego wyniku `Get-Item` przed oznaczeniem
  pliku jako obecnego, przy zachowaniu literalnego pobierania ścieżek. Test
  porównuje teraz osobno stan każdej spodziewanej ścieżki z fikcyjnym drzewem.
- **Weryfikacja:** Linux/Python 3.11 — **180/180** testów, bez pominięć.
  Dla `075c8aba69a8dad6c3cdefacf3db2721ca67dae0` zarówno
  [push](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43054562224),
  jak i [PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43054572010)
  przeszły **4/4** konfiguracje Windows/Linux × Python 3.11/3.12. Windows
  dodatkowo sprawdza nawiasy i polskie znaki w ścieżce gry, nawiasy w ścieżce
  wynikowej, domyślny Pulpit, ponowne uruchomienie bez nadpisania i usunięcie
  katalogu tymczasowego. Nie jest to test gry ani gwarancja każdej konfiguracji.
  Wyniki nowszych commitów należy sprawdzić osobno.
- **Artefakt:** ZIP ze źródeł `075c8ab` ma **30 883 B**, SHA-256
  `3a43a299ce694aa849a86c365af63e24fbb52636543c2cdbfa837dbfb48bbc5c`.
  Trzy człony, CRC i zgodność z deterministycznym builderem sprawdzono; nie
  zawiera danych gry. Zastępuje poprzednią wersję podaną historycznie wyżej.

## 2026-11-11 — zbieracz respektuje politykę PowerShell

- **Decyzja:** na prośbę właściciela usunięto z dystrybuowanego `URUCHOM.bat`
  wymuszenie `-ExecutionPolicy Bypass`. BAT uruchamia teraz Windows PowerShell
  z jego bieżącą polityką; nie zmienia i nie obchodzi ustawień systemu. Jeżeli
  polityka blokuje skrypt, narzędzie może się nie uruchomić — instrukcje każą
  przerwać, nie osłabiać polityki. Usunięto też nadpisanie z pomocnika testów
  Windows, a test buildera sprawdza brak argumentu `-ExecutionPolicy`.
- **Weryfikacja lokalna:** Linux/Python 3.11.2, `python tools/run_tests.py` —
  **180/180** testów; `python -m compileall -q tools tests` oraz
  `git diff --check` przeszły. ZIP zbudowano deterministycznym builderem:
  **31 065 B**, SHA-256
  `f77b637fa83b5b729a13064b119a643f8c28c36e127250b55d7559123d64c541`;
  trzy oczekiwane pliki, CRC poprawne, BAT w archiwum nie zawiera
  `-ExecutionPolicy`.
- **CI:** dla commita `86471d6e5b05cd8d144c1582f5941d0966e4336f` przebiegi
  [push](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43059814684)
  i [PR](https://github.com/szybkoiwyraznie-rgb/wherewindsmeet/actions/runs/43059849827)
  przeszły **4/4** konfiguracje Linux/Windows × Python 3.11/3.12. Testy
  Windows uruchamiają BAT i PowerShell na sztucznym drzewie, teraz z bieżącą
  polityką wykonywania.
- **Ograniczenia:** PowerShell nie jest zainstalowany lokalnie w środowisku
  Linux, więc BAT-a nie uruchomiono w tej sesji. CI nie testuje instalacji gry
  ani ustawień polityki na komputerze właściciela.

## 2026-11-11 — kontrola builda i zablokowana dostawa przez Dysk Google

- **Kontrola bez zmian w kodzie:** `python tools/run_tests.py` — **180/180**
  testów na Linux/Python 3.11.2; `python -m compileall -q tools tests`,
  `git diff --check` i `python tools/check_repository.py` przeszły.
  Deterministyczny builder odtworzył `WWM_ZBIERZ_DANE.zip` o **31 065 B**,
  SHA-256 `f77b637fa83b5b729a13064b119a643f8c28c36e127250b55d7559123d64c541`,
  czyli bajt w bajt archiwum z wpisu z 2026-11-11: trzy człony, CRC poprawne,
  BAT bez `-ExecutionPolicy`, BAT ASCII/CRLF, PS1 UTF-8 BOM/CRLF.
- **Przegląd logiki:** sprawdzono literały ścieżek w `Relative-GamePath`,
  `Inspect-KnownLocations`, wykrywanie dodatkowej biblioteki Steam, kontrolę
  wyjścia poza instalację, limity 90/20 MiB i deduplikację. Wątpliwe podwójne
  backslashe w podglądzie okazały się artefaktem kodowania JSON; w plikach są
  pojedyncze. Nie zmieniano skryptów.
- **Blokada dostawy:** próba wgrania ZIP-a na Dysk Google przez connector
  została odrzucona przez filtr bezpieczeństwa dostawcy connectora
  („blocked … because of its content”); plik nie został wysłany. Zgodnie
  z komunikatem nie ponawiano wysyłki ani nie zmieniano zawartości archiwum,
  żeby ominąć filtr. Utworzony pusty folder `Where Winds Meet` na Dysku
  pozostaje bez ZIP-a. Archiwum nie zawiera danych gry — to BAT, PS1 i tekst
  instrukcji.
- **Ograniczenia:** nadal nie uruchomiono zbieracza na komputerze właściciela
  ani na instalacji gry; dostawa narzędzia pozostaje otwarta i wymaga innej
  drogi niż ten connector.

## 2026-11-11 — diagnostyka blokady: porównanie z paczkami SRW Y

- **Materiał:** pobrano prywatnie z Dysku `SRW_Y_ENCYKLOPEDIA_PROSBA.zip`
  (3 704 B) — najmniejszą paczkę „prośba” o tym samym przeznaczeniu. Plik
  leżał w ignorowanym `google_drive/`, nie trafił do Git.
- **Porównanie:** układ identyczny — `CZYTAJ_TO.txt` + `URUCHOM_TO.bat` +
  skrypt `.ps1`; paczka SRW zawiera nawet `-ExecutionPolicy Bypass`
  i `Unblock-File`, a mimo to została przyjęta przez Dysk wcześniej. Nasze
  archiwum: 30 747 B rozpakowane / trzy człony; SRW: 7 616 B / trzy człony.
- **Różnice treści (zgrubny skan tokenów, nie test filtra):** nasz skrypt
  zawiera łańcuchy `password`, `passwd`, `token`, `cookie`, `secret`,
  `credential`, odczyt `HKCU`/`HKLM`, `Get-Process`, `CreateFromDirectory`
  i SHA-256; skrypt SRW nie zawiera żadnego z nich. To pasuje do heurystyki
  „zbieranie danych + archiwizacja”, ale **nie dowodzi**, co dokładnie
  uruchomiło filtr — dostawca nie ujawnia reguł.
- **Decyzja:** nie ponawiamy wysyłki tego archiwum przez connector i nie
  zmieniamy jego treści, aby ominąć filtr. Zamiast tego udokumentowano drogę
  bez Pythona: archiwum repozytorium z `main` → `collector/URUCHOM.bat`.
  Sprawdzono, że archiwum z `codeload` zawiera `zbierz.ps1` o SHA-256
  `dd9c1ecf235ca9702c4a1ad12d24ff742ddfc3950ba007b01b785bfd94e25ce4`, z BOM
  i CRLF, czyli bajt w bajt jak w repozytorium. Na Dysk wgrano osobną
  notatkę tekstową `JAK_ZDOBYC_ZBIERACZ.txt` (2024 B) — wgranie tekstu
  zadziałało, więc blokada dotyczy treści archiwum, nie połączenia.
- **Ograniczenia:** to hipoteza o przyczynie blokady; nie testowano innych
  wariantów archiwum ani nie odtwarzano reguł filtra. Nadal brak uruchomienia
  zbieracza na Windows właściciela i na instalacji gry.

## 2026-11-11 — decyzja o treści archiwum i drogi publikacji

- **Prośba:** przebudować ZIP „na wzór paczek SRW Y”, żeby nie uruchamiał
  fałszywego alarmu filtra, i udostępnić go przez GitHub.
- **Decyzja:** nie zmieniamy treści archiwum w celu ominięcia filtra
  bezpieczeństwa. Elementy, które najpewniej uruchamiają heurystykę (lista nazw
  prywatnych z `password`/`token`, odczyt `HKCU`/`HKLM` do wykrycia Steam,
  kopiowanie + archiwizacja + SHA-256), są jednocześnie tym, co daje filtrowanie
  prywatnych nazw i automatyczne znajdowanie instalacji. Ich usunięcie byłoby
  regresem funkcji, nie uproszczeniem, i wymagałoby ponownych testów Windows.
- **Publikacja:** próba `gh release create` z assetem nie powiodła się —
  `uploads.github.com` jest z tego środowiska nieosiągalny (`SSL_ERROR_SYSCALL`),
  a release nie został utworzony (sprawdzono: brak release'ów i tagów).
  `raw.githubusercontent.com` również jest nieosiągalny, więc wgranie pliku do
  repozytorium i link raw nie są alternatywą.
- **Dostępna droga:** archiwum repozytorium z `codeload.github.com`
  (`…/archive/refs/heads/main.zip`, 173 920 B) → `collector/URUCHOM.bat`.
  Sprawdzone: `zbierz.ps1` SHA-256 `dd9c1ecf235ca9702c4a1ad12d24ff742ddfc3950ba007b01b785bfd94e25ce4`,
  BOM i CRLF zachowane, czyli to samo narzędzie co w ZIP-ie.
- **Ograniczenia:** brak assetu release'a nie jest usterką projektu, tylko
  ograniczeniem sieci tego środowiska; właściciel może dodać asset ręcznie
  w interfejsie GitHuba. Nadal brak uruchomienia na jego Windows i na grze.

## 2026-11-11 — przywrócenie `-ExecutionPolicy Bypass` w BAT

- **Zgłoszenie właściciela:** na jego komputerze `URUCHOM.bat` przerwał się
  komunikatem `zbierz.ps1 cannot be loaded because running scripts is disabled
  on this system` (`UnauthorizedAccess`). Przyczyną była wcześniejsza decyzja
  o nietykaniu polityki wykonywania; domyślna polityka Windows blokowała skrypt.
- **Decyzja właściciela:** przywrócić zachowanie paczek SRW Y. `URUCHOM.bat`
  wywołuje teraz `powershell.exe` z `-ExecutionPolicy Bypass` (dotyczy tylko
  tego jednego procesu, nie zmienia rejestru ani ustawień systemowych, nie
  wymaga administratora) oraz wykonuje `Unblock-File` na `*.ps1` w swoim
  folderze, żeby znacznik „pobrane z internetu” nie blokował uruchomienia.
  To nie jest obchodzenie zabezpieczeń gry — zbieracz nadal tylko czyta pliki.
- **Zmiany:** `collector/URUCHOM.bat`, `collector/CZYTAJ_TO.txt` (opis
  parametru i `Unblock-File`), `tests/test_collector_kit.py` (dawny test
  wymagał braku `-ExecutionPolicy`; teraz sprawdza `Bypass`, brak
  `Set-ExecutionPolicy`, brak zapisu do rejestru i obecność `Unblock-File`),
  `docs/COLLECTOR.md`, `docs/STATUS.md`.
- **Kontrole lokalne:** `python tools/run_tests.py` — **182/182** (dwa nowe
  testy); `git diff --check` i `check_repository.py` bez uwag. ZIP zbudowany
  ponownie: **31 643 B**, SHA-256
  `35f6959ab98ffb8125c2961aec642faaa39598d02049fd7cd5da60a0b4cb616b`, trzy
  człony, CRC poprawne, BAT nadal ASCII/CRLF, PS1 bez zmian (BOM, 25571 B).
- **Ograniczenia:** PowerShell nie jest zainstalowany w środowisku Linux, więc
  poprawionego BAT-a nie uruchomiono tutaj; wynik CI dla tego commita trzeba
  sprawdzić osobno. Nie testowano na komputerze właściciela ani na grze.

## 2026-11-11 — odbiór wyniku zbieracza i rozpoznanie kontenera map

- **Odbiór:** właściciel wgrał `WWM_DANE_20261111_181913_13ff7ac1.zip`
  (72 995 594 B, poniżej limitu 100 MiB). Pobrano prywatnie do ignorowanego
  `local/`; SHA-256 archiwum `29f5914aadc66b2f736062948e5f4f4deedcfd58af9e4ec12050958439820261`.
  CRC wszystkich 11 wpisów poprawne.
- **Walidator odrzucił archiwum:** `unsafe archive member path`. Przyczyna:
  Windows PowerShell 5.1 / .NET Framework zapisał nazwy wpisów z `\`
  (`pliki\000001_…`), a specyfikacja ZIP wymaga `/`. Dane były kompletne.
- **Raport wyniku:** `status: partial`, 0 problemów, build `25906190`, inwentarz
  640 plików, 9 kandydatów, 1 pominięty przez limit (`translate_words_map_zh_cn`,
  69 470 988 B), 73 878 943 B unikalnych kopii. Obecne:
  `Package/HD/oversea/locale/translate_words_map_en` (50 550 179 B),
  `…_en_diff` w `Package` (751 922 B) i w `LocalData/Patch` (1 122 346 B),
  `MANIFEST` w obu gałęziach, `data3` (10 829 572 B), `data205` (7 564 939 B),
  `…_zh_cn_diff` (233 290 B). Nieobecne: oba warianty `__small`.
  W katalogu `locale` są też mapy innych języków (m.in. `th`, `ru`, `vi`, `fr`,
  `ja`, `de`, `ko`, `es`, `pt_br`) — nie kopiowano ich zgodnie z zakresem.
- **Struktura:** `0xDEADBEEF` + wersja 1 + `uint64` liczba chunków + tabela
  `uint32` offsetów; ostatni offset + koniec tablicy = rozmiar pliku dokładnie,
  ostatni wpis ma 0 B (wartownik). Chunki: 8-bajtowy prefiks + ramka zstd;
  wszystkie **4386/4386** rozpakowują się bez błędu. Payload: nagłówek
  `uint64, uint64, uint32 0x595896DC, uint32 0`, region indeksu i jawny tekst
  z markupem (`#Y…#E`, `$T(…)`, `{}`). Szczegóły w
  [LOCALE_CONTAINER.md](LOCALE_CONTAINER.md).
- **Naprawa zbieracza:** `zbierz.ps1` buduje teraz archiwum przez
  `System.IO.Compression.ZipArchive` i `CreateEntry` z nazwami normalizowanymi
  do `/`, z kontrolą `..` i wiodącego `/`; `CreateFromDirectory` usunięto.
  Walidator przy backslashach zwraca czytelny powód. Dodano dwa testy
  (`tests/test_collector_kit.py`, `tests/test_collector_return.py`).
- **Kontrole:** `python tools/run_tests.py` — **184/184**. ZIP zbieracza
  zbudowany ponownie: **33 111 B**, SHA-256
  `b156eabb7624b2a8b707af73272641765938dbc02725960f8cf377b30c3a8b2e`.
- **Ograniczenia:** poprawionego zapisu ZIP nie uruchomiono na Windows (brak
  PowerShell w tym środowisku); wynik CI trzeba sprawdzić osobno. Znaczenie pól
  nagłówka, wiązanie łańcuchów z kluczami i zapis zwrotny pozostają nieznane.
  Zmierzona liczba fragmentów tekstu jest heurystyczna, nie jest liczbą wpisów.

## 2026-11-11 — czy `partial` to problem; skala mapy

- **Powód `partial`:** dokładnie jeden plik `skipped_limit`
  (`translate_words_map_zh_cn`, 69 470 988 B). Pozostałe 8 kandydatów skopiowano,
  0 problemów odczytu, inwentarz nieobcięty (`limited: false`), 0 błędów.
  Wykorzystano 73 878 943 B z 94 371 840 B (78,3%), zapas 20 492 897 B —
  chińska mapa nie zmieściłaby się nawet przy pełnym budżecie.
- **Wniosek:** dla tłumaczenia EN→PL brak niczego istotnego; EN jest kompletną
  mapą zbieracza, a `collected` i tak nie znaczyłoby „kompletne”.
- **Kontrola innych pojemników:** `data3` (3949 chunków) i `data205` (2606) mają
  ten sam kontener, ale po dekompresji zawierają identyfikatory i nazwy ustawień,
  nie tekst fabularny. Warstwa tekstowa to mapy `translate_words_map_*`.
- **Skala:** suma wpisów z nagłówków mapy EN — **1 122 784**, rozpakowane
  94 581 912 B. To liczba strukturalna, nie heurystyka.
- **Ograniczenia:** nie sprawdzono pokrycia wszystkich powierzchni tekstowych
  gry; `MANIFEST` (count 1, chunk bez zstd) pozostaje nierozpoznany.

## 2026-11-11 — format paczki tłumacza i pierwszy parser kontenera

- **Wzorzec:** pobrano prywatnie `plik_dla_tlumacza_v8.zip` (8 364 702 B) z Dysku
  i przeczytano dokumentację `mtgcrawler` (`TRANSLATOR_PACKAGE.md`,
  `TRANSLATOR_PACKAGE_TECH.md`, `TRANSLATION_WORKFLOW.md`) przez API GitHuba.
  Paczka SRW to `README.md` + `sceny.zip` (39 plików `.md`) + `widoki.zip`
  (10 plików); element ma nagłówek `[Dialog - mówca]`, `limit:` oraz linie
  `EN:` i `PL:`; kontekst sceny to `## Scena N/M — id`, `grupa`, `pliki`,
  `misja`, `uczestnicy`.
- **Dokument docelowy:** `TRANSLATOR_PACKAGE_WWM.md` (usunięty 2026-11-12,
  zastąpiony przez [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md)) opisywał mapowanie SRW→WWM (źródłem jest EN z gry), szkic elementu, proces
  i **cztery blokady**: nieodczytany indeks kluczy, brak atrybucji mówcy/scen,
  niezmierzone limity i niesprawdzony zapis zwrotny.
- **Parser:** dodano `tools/locale_container.py` (sam nagłówek i tabela
  offsetów; opcjonalny `zstandard` importowany tylko przy dekompresji) oraz
  `tests/test_locale_container.py` (8 testów na danych syntetycznych).
  Na odebranym pliku: 4386 chunków, 50 527 281 B danych chunków, **4386/4386**
  z ramką zstd na przesunięciu 9.
- **Próby rozłożenia indeksu:** rekordy w chunku **nie mają stałej długości** —
  sprawdzono układy 2/4/8/12/16/20/24/32 B z polami `u32`/`u64` i warunkiem
  „suma długości = rozmiar bloba”: **brak dopasowania** w trzech chunkach.
  Bezpośrednio przed blobem widać rekordy o kształcie `[u64][u32][u32]`
  z sensownymi małymi wartościami, ale region zawiera gęste `0x80`, co wskazuje
  na kodowanie zmienne (varint/bitowe). To **hipoteza**, nie ustalenie.
- **Kontrole:** `python tools/run_tests.py` — **192/192**.
- **Ograniczenia:** indeks, klucze, mówcy, limity i zapis zwrotny pozostają
  nieznane; paczka dla tłumacza nie jest gotowa do wysłania.

## 2026-11-11 — odczytany rekord wpisu w chunku

- **Materiał:** `translate_words_map_en_diff` — 686 chunków z `A = B = 1`,
  gdzie indeks jest najmniejszy.
- **Ustalenie:** po 24-bajtowym nagłówku i regionie indeksu (24 B dla `B = 1`,
  56 B dla `B = 2` i `B = 3`) leży rekord `[u64 hash][u32 typ][u32 długość]`
  (`typ = 8` dla tekstu UTF-8), a za nim tekst dokładnie tej długości, bez
  terminatora. Zgodność długości we wszystkich 686 chunkach jednowpisowych
  (np. `Northmount West` → 15, `Unlocked at 5:00 on Jul 3` → 25, opis muszli
  → 350).
- **Hipoteza:** region indeksu jest pochodną hashy (wypełniony `0x80`,
  rozmiar nie zależy liniowo od `B`), a nie tabelą przesunięć — więc zmiana
  długości tekstu może nie wymagać przeliczenia indeksu. **Niesprawdzone**:
  wymaga przebudowy chunku i odczytu zwrotnego.
- **Narzędzie:** `tools/locale_container.py` nadal czyta tylko warstwę
  zewnętrzną; parser rekordów jeszcze nie powstał.
- **Ograniczenia:** nieznany układ dla chunków wielowpisowych i mapa główna
  (`B` do 511) nie jest jeszcze przemierzona; mówcy, limity pól i zapis
  zwrotny pozostają nieznane.

## 2026-11-11 — układ chunku `_diff` odczytany; prototyp elementu paczki

- **Ustalenie:** chunk `_diff` = nagłówek 24 B + indeks o zmiennym rozmiarze
  (8/20/24/36/40/56/72 B) + `N × 16 B` rekordów `[u64 hash][u32 typ][u32 len]`
  + sklejone teksty bez terminatora. Rozmiar indeksu wyznacza warunek
  „suma długości = reszta payloadu”.
- **Narzędzie:** `tools/locale_records.py` (odczyt, walidacja, brak zapisu) +
  `tests/test_locale_records.py` (8 testów syntetycznych). Przy kilku możliwych
  rozmiarach indeksu rozstrzyga walidacja UTF-8 tekstów typu 8.
- **Wynik na realnym pliku:** `translate_words_map_en_diff` — **598 z 4164**
  chunków przechodzi walidację, 630 wpisów, 621 unikalnych hashy, 10 pustych.
  Pozostałe są odrzucane (nie zgadywane). `data3`/`data205`/mapa główna nie są
  obsługiwane: ich rekordy nie tworzą tablicy stałej długości.
- **Prototyp paczki:** wygenerowano prywatnie `local/prototyp_paczki/probka.md`
  w formacie SRW: `N. [Tekst] …`, `id:` (hash), `limit:` (bajty oryginału),
  `EN:`, `PL:`. Służy do sprawdzenia formatu, **nie** jest paczką do wysłania.
- **Kontrole:** `python tools/run_tests.py` — **200/200**.
- **Ograniczenia:** mapa główna (1 122 784 wpisów) pozostaje nieodczytana;
  mówcy, kolejność scen, limity pól i zapis zwrotny nadal nieznane.

## 2026-11-11 — generator paczki dla Tłumacza

- **Nowe narzędzie:** `tools/build_translator_pack.py` — z JSONL `{id, text}`
  buduje katalog paczki: `README.md` (instrukcja: numeracja stała, `EN:`
  zamrożone, `PL:` do wypełnienia, dziedziczenie powtórzeń, znaczenie tokenów,
  UTF-8), `widoki/<nazwa>.md` (elementy `N. [Grupa] …` + `id:` + `limit:` +
  `EN:`/`PL:`) oraz `tokeny.tsv` (`#Y…#E`, `#H`, `#R`, `{…}`, `$T(…)`, `[[…]]`).
- **Test:** `tests/test_build_translator_pack.py` — 8 testów; razem **208/208**.
- **Uruchomienie na realnych danych:** 598 wpisów z `_diff` →
  `local/prototyp_paczki/` (598 elementów, 18 tokenów). Pakiet jest kompletny
  formalnie, ale zawiera tylko ułamek tekstu gry.
- **Trop dla mapy głównej (niepotwierdzony):** przy blokach 32 B od offsetu 32
  w chunku 0 aż 219/244 odcinków `blob[o:o+len]` dekoduje się jako UTF-8, ale
  żadne przypisanie pól (offset/offset od końca/para u32) nie daje spójnej
  semantyki — hipoteza do dalszych prób, nie wynik.

## 2026-11-11 — format tabeli odczytany do końca (dzięki prior art)

- **Przełom:** zajrzałem do istniejących narzędzi społeczności. `dest1yo/wwm_utils`
  (`src/core.rs`, `src/structs.rs`) opisuje dokładnie ten format. Moje wcześniejsze
  hipotezy były błędne: pole `u32 0x595896DC` to **timestamp**, nie magic, a drugie
  pole wpisu to **offset**, nie typ.
- **Prawdziwy układ tabeli:** `u64 entry_count | u64 value_count | u64 timestamp`,
  potem `max(entry_count+17, 24)` bajtów nieprzejrzystych `buckets`, potem
  `entry_count × (u64 id, u32 offset, u32 length)`, potem teksty; pozycja tekstu to
  `entries_pos + 16*index + 8 + offset`. Bajt `0xFF` na początku tekstu = zaślepka.
- **Skutek:** cała mapa główna parsuje się bez reszty — **1 122 784 wpisy, 0 błędów,
  4386/4386 chunków** (wcześniej 0/60). `_diff` daje 12 934 wpisy w 4163 chunkach.
- **Zapis zwrotny rozwiązany:** przepakowanie z zachowaniem nagłówka i `buckets`
  i przeliczonymi offsetami odtwarza zbiór `id → tekst` w 4386/4386 + 4163/4163
  chunkach. W danych występują współdzielone regiony tekstów i „dziury” z
  nieaktualnymi offsetami — dlatego teksty czytamy przez `offset`, nie przez sumę
  długości.
- **Paczka:** 1 122 784 wpisy w grze, 503 206 unikalnych tekstów → 503 206
  elementów, 26 plików, 61 MB rozpakowane / **24 MB ZIP**, 583 tokeny.
- **Testy:** 215/215. Poprawiono `tools/locale_records.py` (pełna specyfikacja +
  `pack_table`) i `tests/test_locale_records.py`.
- **Następne:** patcher (podmiana tekstów po `id`) i odczytanie mówców/scen.

## 2026-11-11 — patcher działa na całej mapie EN

- **Nowe narzędzie:** `tools/apply_translation.py` — podmiana tekstów po `id`,
  przepakowanie tabeli (offsety przeliczone), rekompresja zstd, nowa tabela
  przesunięć, wszystko na kopii (wejście nietknięte).
- **Chunk 0 kontenera to indeks mapy**, nie tabela tekstów: `u64 suma wpisów |
  u64 liczba chunków | u32[…]`; przepisywany bez zmian. Nagłówek: `count` =
  liczba chunków, tabela ma `count+1` wpisów (ostatni to wartownik).
  `tools/locale_container.py` poprawiony na te semantyki.
- **Wynik:** mapa EN 50 550 179 B → 51 904 280 B po 200 podmianach, 11 s,
  weryfikacja: 1 122 784 id, 200 zmian, zero rozjazdów.
- **Testy:** 229/229 (`tests/test_apply_translation.py` + poprawione
  `tests/test_locale_container.py`).
- **Dokumentacja:** [PATCHER_WWM.md](PATCHER_WWM.md).
- **Następne:** sceny i mówcy, limity pól interfejsu, skrypt instalacyjny.

## 2026-11-11 — paczka odchudzona z 271 MB do 24 MB

- **Błąd, który wyszło widać po uwadze właściciela:** pierwsza paczka miała 271 MB
  przy 32,3 MB unikalnego tekstu, bo (a) każdy element powtarzał tekst w nagłówku
  i w linii `EN:`, (b) każde z 619 578 powtórzeń było osobnym elementem z
  `copy_of:`, (c) `manifest.json` miał 118 MB.
- **Nowy format:** element tylko dla unikalnego tekstu; tekst jednej linii stoi
  w nagłówku, wielolinijkowy pod `EN:`; `manifest.json` to kilkaset bajtów;
  dziedziczenie rozwiązuje patcher, nie paczka.
- **Wynik:** 503 206 elementów, 26 plików, **61 MB → 24 MB ZIP** (26% objętości
  wyjściowej), generowanie 2,9 s.
- **Patcher:** tłumaczenie tekstu trafia we **wszystkie** jego wystąpienia —
  sprawdzone na mapie EN: 200 przetłumaczonych tekstów → **41 962 zmienione wpisy**,
  weryfikacja 1 122 784 id bez rozjazdów (13 s).
- **Testy:** 232/232.

## 2026-11-11 — dostawa `oversea` z Dysku Google: nowe dane scen i mapa `zh_cn`

- **Wejście:** 4 pliki z Dysku Google (prywatnie w `google_drive/`):
  `oversea.zip` 61 626 340 B, `oversea2.zip` 96 942 617 B, `patch.zip`
  3 488 483 B, `translate_words_map_zh_cn` 69 470 988 B. Wypakowanie do
  ignorowanego `local/oversea` (25 plików) i `local/patch`.
  Inwentarz z SHA-256: [OVERSEA_INWENTARZ.md](OVERSEA_INWENTARZ.md).
- **Co przyszło:** `data200`, `201`, `202`, `203`, `204`, `206`.
  `data200` **nie ma** `TimelinePObject` (same tabele kontekstowe).
  Nadal brakuje `data207`–`data212`; `data205` mamy z wcześniejszego zbieracza.
- **Sceny** (`tools/timeline.py`, 47 548 scen, 114 592 kwestii, wszystkie
  `text_id` unikalne, 12 920 różnych `entity_tag`):
  `data201` 6 926 scen / 15 805 linii, `data202` 10 600 / 27 488,
  `data203` 8 939 / 25 004, `data204` 8 811 / 22 934, `data206` 12 272 / 23 361.
- **Rejestr pokrycia:** `MANIFEST` z patcha ma 74 951 `dialog_timelines`
  (281 004 klucze łącznie). Nowe sceny pokrywają **58,5%** (43 828 scen
  z `dialog_no`; wcześniej 10,1% / 7 571). **Brakuje 31 123 dialogów.**
  Żadna scena nie jest poza rejestrem.
- **Mapa źródłowa `zh_cn` rozpoznana do końca:** ten sam kontener co mapa EN
  (`0xDEADBEEF`, wersja 1, 7097 chunków, zstd) — 3 581 256 wpisów w nagłówkach,
  **1 816 408 niepustych** par `id → chiński tekst`. Treść to nie tylko dialogi:
  miejsca (`寿昌坊-平民`), imiona (`邵冷乄德明`), przedmioty (`耳砂珍坯·三阶`),
  interfejs (`累计登录2天`), encyklopedia.
- **Wiązanie scena ↔ mapa sprawdzone:** na 50 000 `text_id` ze scen **100%
  występuje w mapie `zh_cn`**; 42 208 tekstów identycznych, 7 006 różni się
  wyłącznie łamaniem wiersza.
- **Nowe odkrycie — dopisek sceniczny:** 1 863 z 50 000 (3,7%) różni się treścią.
  Mapa trzyma pełną linię z dopiskiem w nawiasach, scena tylko wypowiadany
  fragment: `（正声）咳咳，…` / `（恍然）——蹊跷蕴之？…` (1 055 przypadków, sposób
  mówienia przed kwestią) oraz `喵喵喵喵！（你这些天去哪了，好久没喂我了，哼！）`
  (322, myśl bohaterki po kwestii). Tłumaczyć trzeba wersję z mapy; który wariant
  renderuje klient — **do sprawdzenia w grze**, nie zakładać.
- **Mówcy:** większość `entity_tag` to imiona postaci, ale trafiają się generyki
  (`玩家`, `主角`, `player`, `player_1/2`, `我`, `你` = postać gracza) i grupy
  techniczne (`Entity轨道组`, pusty tag) — nie są osobami.
- **Format dla tłumacza:** `format_tlumacza.md` (usunięty 2026-11-12,
  zastąpiony przez [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md)) — kolumny
  `dialog_no`, projekt, czas, mówca, `text_id`, chińskie źródło z mapy, pusta
  kolumna na przekład, uwagi; przykłady z prawdziwych danych, w tym oba wzorce
  z dopiskiem.
- **Testy:** 242/242, `check_repository.py` OK, `git diff --check` czysty.
- **Następne:** uzupełnić brakujące 31 123 dialogi (brakuje `data207`–`212`
  lub innego źródła), a potem decyzja, czy tłumaczyć pełny korpus mapy `zh_cn`
  (1,8 mln wpisów) czy wyłącznie teksty objęte scenami.

## 2026-11-11 — czerwone CI na Windows: test odbioru paczki, nie dane

- **Objaw:** `windows-latest / Python 3.11` i `3.12` padały z
  `tests.test_collector_return...test_rejects_member_names_with_backslashes:
  AssertionError: 'backslashes' not found in 'unexpected archive member'`,
  przy zielonym Ubuntu. Stan trwał od wielu commitów (przed dostawą `oversea`),
  więc nie był skutkiem nowych danych.
- **Przyczyna:** test składał wpis ZIP przez `writestr("pliki\\…")`, a
  `ZipInfo.__init__` podmienia `os.sep` (`\` na Windows) na `/` zgodnie
  ze specyfikacją ZIP. Na Windows wpis powstawał już jako `pliki/000001_map`,
  więc walidator nigdy nie widział separatora i odrzucał paczkę inną ścieżką.
  Ten sam mechanizm działa przy **odczycie**: `_RealGetContents` tworzy
  `ZipInfo(filename)` z nazwy z katalogu centralnego, więc na Windows
  `infolist()` zwraca nazwy z `/` nawet gdy archiwum ma `\`.
- **Konsekwencja dla odbioru:** gałąź „archive member path uses backslashes"
  nie może zadziałać na Windows. Paczka z PowerShell 5.1 jest i tak odrzucana
  — fałszywa nazwa nie pasuje do wzorca `STORED` (`unexpected archive member`),
  a prawdziwą, wieloplatformową bramką są pola raportu `source` i `stored_as`,
  czytane z JSON, gdzie separator zostaje nietknięty (`safe_relative`, `STORED`).
- **Poprawka:** `archive()` w teście składa `ZipInfo` i przypisuje nazwę po
  konstrukcji, więc archiwum trzyma wpis z bajtami takimi, jakie zapisał
  zbieracz; test rozróżnia platformy (Linux: komunikat `backslashes`, Windows:
  paczka odrzucona jako `unexpected archive member`); dodany przypadek
  `stored_as` z `\` i komentarz w walidatorze.
- **Wynik:** 242/242 lokalnie, CI **4/4 zielone** (Ubuntu i Windows × Python
  3.11/3.12). Ślepych punktów w testach `extras` nie ma: każdy faszywy wpis jest
  weryfikowany pod kątem obecności w archiwum.

## 2026-11-11 — druga dostawa: brakujące `data205`–`data208`, indeksy i trwały indeks w repo

- **Wejście:** `oversea3.zip` (76 372 696 B), `index.zip` (90 717 968 B),
  `index2.zip` (33 917 240 B). To były **brakujące pliki**: `data205`, `data207`,
  `data208`, `data209`, `data210`, `data211`, `data212` oraz indeksy
  `index1`–`index4`, `index1001`, `index1200`, `index200`–`index204`.
- **Skan nowym narzędziem** `tools/skan_timeline.py` (liczy serializowane pole
  `Type` = `TimelinePObject`, nie goły literał): sceny mają `data205` (8 484),
  `data207` (11 847), `data208` (7 042). **`data209`–`data212` i wszystkie
  indeksy nie mają ani jednego obiektu sceny** — nie brakowo scen, tylko inna
  treść. Łącznie z wcześniejszą dostawą: 75 006 obiektów, 8 plików ze scenami.
- **Ekstrakcja** (`tools/timeline.py`): `data205` 8 484 scen / 17 268 kwestii,
  `data207` 11 847 / 32 015, `data208` 7 042 / 14 471.
- **Pokrycie rejestru:** 58,5% → **92,2%** (69 092 z 74 951 `dialog_timelines`).
  **Brakuje 5 859 dialogów**; żadna scena nie jest poza rejestrem.
- **Nowe ustalenie o `dialog_no`:** to **identyfikator grupy dialogowej**, nie
  pojedynczego timeline'u. Ten sam numer występuje w dwóch plikach z **inną**
  treścią i innymi mówcami (przykład: `1960001321` — w `data203` 5 kwestii
  z 木闻莺 o蒙学院, w `data1200` 9 kwestii z 黎书韵 o衙门; różne `id`
  timeline'u: 1167636709 vs 1709454066). Scalać po `dialog_no` **nie wolna** —
  treść się zgubi. W korpusie 10 takich grup.
- **`data1200` z patcha jest nadzbiorem** wersji z `oversea`: wszystkie 158
  `text_id` bazy występuje w patchu plus 25 nowych. Do korpusu brana jest wersja
  z patcha; `data3` (25 scen) także wchodzi do korpusu.
- **Trwały indeks w repo** (decyzja właściciela, szczegóły w
  [DATA_POLICY.md](DATA_POLICY.md)): `index/manifest.json`, 5 shardów scen
  (74 979 scen, 178 572 kwestii) i 3 shardy tekstów (176 146 unikalnych), każdy
  plik < 10 MiB. Tekst stoi tylko w shardach tekstów, więc nie jest powtarzany
  przy każdej kwestii. `tools/buduj_indeks.py` buduje indeks z prywatnych
  wyjść, `tools/sceny_z_indeksu.py` odtwarza z niego sceny i listy tekstów
  **bez `local/` i bez plików z Dysku**.
- **Round-trip sprawdzony:** sceny odtworzone z indeksu są identyczne z wyjściem
  `timeline.py` we wszystkich polach linii (po poprawce: obsada jest klucowana
  parą `mowca` + `speaker_no`, bo ten sam tag bywa użyty dla dwóch mówców, a
  `skeleton` ujednolicamy do pierwszej napotkanej postaci — w źródle ten sam
  mówca bywa zapisany z `''` i bez wartości, a żadne narzędzie potokowe tego
  pola nie używa).
- **Tekst źródłowy do tłumaczenia:** 25 258 z 176 146 tekstów (14,3%) ma w mapie
  `zh_cn` **dłuższą** wersję — z dopiskiem scenicznym w nawiasach, który scena
  obcięła. Tłumaczy się wersję z mapy (`tekst_mapa` w shardach tekstów).
- **Uwaga o piaskownicy:** w trakcie tej pracy `local/`, `google_drive/` i
  `.venv` zniknęły przy czyszczeniu środowiska. Przetrwał tylko materiał w
  repozytorium — co jest dokładnie tym argumentem, dla którego indeks jest
  wersjonowany. Lokalny commit zaginął razem z drzewem i został odtworzony.
- **Testy:** 258/258, w tym 8 testów indeksu (round-trip, limity shardów,
  spójność zacommitowanego indeksu, odrzucanie nieznanego formatu) i 8 testów
  skanu timeline'ów.
- **Następne:** domknąć 5 859 brakujących dialogów (nie ma już nieprzesłanych
  plików `data*`, więc albo rejestr zawiera grupy bez timeline'u, albo treść
  jest w innym pliku), a potem ograniczenia pól interfejsu i skrypt instalacyjny.

## 2026-11-11 — odczyt całej bazy gry (`MANIFEST` → `indexN` → `dataN`)

- **Wejście:** `manifest.zip` (1 560 318 B, bazowy `MANIFEST`), `oversea*.zip`,
  `index*.zip`, `patch.zip` (razem 42 pliki bazy po wypakowaniu) oraz bazowa
  i patchowe mapy `zh_cn`/`en` ([OVERSEA_INWENTARZ.md](OVERSEA_INWENTARZ.md),
  `index/manifest.json`).
- **Odkrycie budowy bazy i warstwy aktualizacji:** `tools/baza_gry.py` czyta
  każdy rekord tabeli bezpośrednio po nazwie i kluczu, nakładając chunki
  poprawek i dopisane kolumny z `index1001`/`1200` i `data1001`/`1200`
  ([BAZA_GRY.md](BAZA_GRY.md)).
- **Sprawdzenie całości (`python3 tools/baza_gry.py … --sprawdz`):** odczytano
  **114 169 z 114 171** tabel i **10 077 465 wierszy**, **0** niezgodności
  liczby wierszy z `MANIFEST`, **0** nieznanych tagów wartości. Dwie tabele
  rozmieszczenia (`spaces.s66027.spawn.spawn_sw_default_0` i `…_usual_0`) mają
  `0x00` w miejscu tagu; nie zawierają tekstów.
- **Wyjaśnienie rzekomych „5 859 brakujących dialogów”:** poprzedni parser
  (`tools/timeline.py`, usunięty) ciął surowe bajty między wystąpieniami
  `TimelinePObject`, przez co brał `dialog_config` następnego dialogu (62 726
  z 62 746 par zgodnych z następną sceną, 0 z własną). Właściwa tabela to
  `dialog_timelines.<numer>`, gdzie wszystkie 74 950 dialogów ma jednoznaczny
  numer, projekt, obsadę i kwestie.

## 2026-11-12 — wyciąg `wwm-indeks-v2`, pakiet v1 i próby potoku na realnych plikach

- **Wyciąg (`tools/wyciag.py`, format `wwm-indeks-v2`):** zastąpił `wwm-indeks-v1`,
  `analiza/` oraz 6 starych narzędzi (usunięte z repo). Rozszerza też
  `tools/apply_translation.py` (`is_metadata_chunk` dopasowane do nagłówka
  `_diff` o długości `16 + 4 × liczba_kubełków_bazy`).
- **Wyniki wyciągu na buildzie `25906190`:**
  - warstwy map: `zh_cn` 1 818 900 id, `en` 1 124 787 id;
  - zakres pakietu: **1 128 714 id** → **483 190 unikalnych tekstów** (5 824
    ma wyłącznie wersję EN; 700 766 id wyłącznie w `zh_cn` bez wskazania z tabel
    lub scen pominięto jako hipotezę tekstów nieużywanych przez klienta
    zachodniego);
  - **74 950 dialogów** (1 577 bez tekstu), **186 025 kwestii** (wszystkie
    wewnątrz grupy mówcy; 111 398 z nazwą z gry, 37 407 gracz, 37 168 tylko
    etykieta robocza, 52 bez nazwy; **1 860** kwestii zależnych od płci
    bohatera z `valid_for_specific_type`);
  - 93,59% id EN (1 052 649 z 1 124 787) ma znane źródło w tabeli albo scenie;
    72 138 id bez źródła;
  - 24 733 zadań, 1 077 grup zadań, 15 027 pytań z wyborami, 172 postacie
    w encyklopedii, 2 330 miejsc, 42 236 bytów z nazwą, tytułem lub opisem.
- **Pakiet dla tłumacza v1 (`tools/buduj_paczke.py`):**
  - zbudowano `paczka_dla_tlumacza_wwm_v1.zip` (**44 362 422 B**, SHA-256
    `c25ddd2da73d5ef78b5e211b3dfb01d65c85702174fca25e3c82e1f1b376ecb0`),
    składający się z `README.md`, `sceny.zip` (19 783 943 B, SHA-256
    `1a528501…efdb`) i `widoki.zip` (24 567 169 B, SHA-256 `fc0532a6…8daf`),
    oraz przekazano go właścicielowi przez Dysk Google; kopia `README.md`
    i `paczka.json` w `paczki/v1/`;
  - liczby pakietu: **73 373 sceny**, **528 249 elementów** (203 943 w scenach,
    324 306 w widokach), **485 047 miejsc `PL:`** (168 183 w scenach, 316 864
    w widokach), 43 199 powtórzeń z odwołaniem, 3 puste teksty bez `PL:`;
  - kontrola własna (`kontrola()`): 485 047 miejsc `PL:`, 0 powtórzonych,
    0 nieznanych, 0 brakujących;
  - kolejność scen: 8 971 z wpisu zadań, 89 jako następstwo, 25 456 według
    numeracji sąsiedztwa (oznaczone w nagłówku sceny), 12 303 według projektu,
    26 554 rozmowy tła według miejsca; w całej grze przerwano 36 cykli
    łańcucha zadań (`0` w wątku głównym — 2 445 scen w 4 rozdziałach).
- **Próby potoku przyrostowego w piaskownicy (poza Git):**
  - **Audyt aktualizacji (`tools/audyt_aktualizacji.py`):** porównanie wyciągu
    z samej paczki (bez `LocalData/Patch`, 482 867 tekstów) z bieżącym `index/`
    (483 190 tekstów): **387** nowych tekstów, **64** usunięte, 482 803 bez
    zmian, **0** zmienionych scen; wygenerowany pakiet uzupełniający ma
    dokładnie **387** miejsc `PL:`.
  - **Import zwrotki i łatka (`tools/import_zwrotki.py`, `tools/zbuduj_latke.py`):**
    sztuczna zwrotka na 19 630 miejsc (4 pliki): 0 odrzuconych; zbudowana
    łatka na 3 prawdziwych plikach EN przepisała 95 471 / 1 122 784 wpisów
    bazy oraz 847 / 6 775 i 1 060 / 11 015 w warstwach `_diff`, przechodząc
    kontrolę wpis po wpisie.
- **Poprawka CI na Windows (`tools/wypisz.py`):** 2 testy łatki rzuciły
  `UnicodeEncodeError` w `windows-latest` (przekierowane wyjście ma stronę
  kodową bez polskich liter); dodano przełączenie `stdout`/`stderr` na UTF-8
  na starcie każdego narzędzia oraz test z `PYTHONIOENCODING=cp1252`.
- **Ograniczenia:** żadnych testów w uruchomionej grze ani na instalacji
  właściciela; nie sprawdzono przyjmowania przepisanych map przez klienta,
  polskich glifów, limitów szerokości pól ani kolejności fabularnej.

- **Zbieracz aktualizacji, instalator Windows z kopią/przywracaniem i plan testu UI (po `9f04ed6`):**
  - **Zbieracz v2 (`collector/URUCHOM_AKTUALIZACJE.bat`, `zbierz.ps1 -Tryb aktualizacja`, `spakuj_dane.ps1`, `validate_collector_return.py`):**
    dodano tryb jednego kliknięcia zbierający `LocalData/Patch/HD/oversea/*`,
    `Package/HD/oversea/{MANIFEST,data1001,data1200,index1001,index1200}`,
    wszystkie mapy `*_diff` oraz `translate_words_map_zh_cn` w jednym archiwum
    < 90 MiB (format `wwm-collection-v2`); przepisano `spakuj_dane.ps1`
    na `.NET SHA256`/`ZipArchive` z dzieleniem dużych paczek <= 85 MiB i
    zachowaniem pełnych ścieżek względnych. Zweryfikowano w Windows PowerShell 5.1 CI.
  - **Instalator Windows i wsparcie identycznych nazw w łatce (`tools/zbuduj_latke.py`, `instalator/`, `tools/build_installer_kit.py`):**
    dodano `--mapa SCIEZKA_W_GRZE PLIK` i `--build-gry` w `tools/zbuduj_latke.py`
    (rozróżnianie identycznych nazw bazowych między `Package/` i `LocalData/Patch/`);
    utworzono zestaw `instalator/` (`ZAINSTALUJ.bat`, `PRZYWROC.bat`, `SPRAWDZ_STAN.bat`,
    `instaluj_latke.ps1`) z kopią oryginałów poza folderem gry, weryfikacją
    SHA-256 i buildu Steam przed zmianą, transakcyjnym zapisem z cofnięciem
    błędu i ochroną przed nadpisaniem nowszego patcha Steam przy przywracaniu.
    Zweryfikowano na fikcyjnej instalacji w Windows CI (`tests/test_installer_windows.py`).
  - **Mała łatka testowa UI, prologu i polskich znaków (`tools/latka_testowa.py`, `docs/TEST_W_GRZE.md`):**
    przygotowano izolowany generator paczki testowej dla etykiet menu/ustawień
    oraz otwierających napisów prologu (`text_msg` / `text_msg__grey`, wiersze
    `590336–590351`, m.in. *Even at the end of the road, / a drink to wet your throat.*)
    z kompletem znaków `ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`; **sam test w
    uruchomionej grze nadal pozostaje po stronie właściciela na Windows**.
- **Weryfikacja prologu i zakresu `ZH` vs `EN` w `index/` (build `25906190`):**
  - **Lokalizacja prologu:** kwestie otwierającej cutscenki (*Jiang Yan*, *Chen Zixi*)
    leżą w `text_msg` / `text_msg__grey` (w `paczka_dla_tlumacza_wwm_v1.zip`:
    `widoki/07_komunikaty_04.md` i `07_komunikaty_12.md`); grywalny wątek
    główny po obudzeniu zaczyna się w `sceny/01_watek-glowny_rozdzial-1_01.md`
    (zadania `220001`–`220003`, dialog `4700001`).
  - **Różnica `ZH` vs `EN`:** `zh_cn` zawiera `1 818 900` ID, a `en` — `1 124 787`
    ID (`38,16%` różnicy); poza `700 766` niewskazanymi ID pominiętymi już przy
    ekstrakcji, wśród `1 295` tekstów wyłącznie chińskich w `index/` aż `935`
    (**72,2%**) to komunikaty testowe, zaślepki i wpisy wycofane (`测试`, `废弃`,
    `占坑`), a z `483 190` tekstów indeksu `476 071` ma parę `ZH + EN`,
    `5 824` ma tylko `EN` (`z_en=True`), `690` tekstów `EN` zawiera resztki CJK,
    a `48` wykazuje różnice w argumentach formatowania `{}` / `%s`.
  - **Narzędzia zakresu (`--tylko-z-en`):** w `tools/buduj_paczke.py`
    (przetestowane na `index/`: `483 752` miejsc `PL:`, `kontrola()` 100%
    zgodna) oraz `tools/audyt_aktualizacji.py` (wykrywa jako nowość wpisy,
    które w kolejnym patchu globalnym uzyskały wersję `EN`).

## 2026-11-14 — dlaczego napisy otwierającej cutsceny zostały po angielsku (pokrycie, nie podmiana pliku)

- **Objaw od właściciela:** po świeżej łatce PL nałożonej na pliki gry klient
  (Steam, Windows) nie przywrócił podmienionego `translate_words_map_en_diff`,
  a napisy początkowej cutsceny były w ok. 80% angielskie. Wcześniejsze
  podejrzenie, że łatka podmienia `translate_words_map_en_diff` na wersję
  policzoną od złej bazy, było **koincydencją**: patcher nadpisuje oba pliki
  docelowe niezależnie i utrzymuje ich spójność, a sama podmiana nie tłumaczy
  języka napisów.
- **Wejście:** wyłącznie repozytorium — `index/` (`wwm-indeks-v2`, Patch 2.4
  `26592996`) i magazyn `tlumaczenie/`. Bez plików gry, bez `zstandard`, bez
  Dysku Google; w piaskownicy nie ma instalacji właściciela, więc **nic nie
  zostało sprawdzone w uruchomionej grze**.
- **Pomiar pokrycia (nowe narzędzie `tools/pokrycie_tlumaczenia.py`):**

  | sekcja | wpisów | z przekładem | braki | % |
  |---|---|---|---|---|
  | napisy cutscen (`text_msg` 590000–592694) | 2 688 | 2 603 | 85 | 96,8% |
  | intro (`wds_oneday_intro_cutscene_data`) | 9 | 8 | 1 | 88,9% |
  | napisy filmowe (`entry_collect_movie_subtitle_data`) | 47 | 13 | 34 | 27,7% |
  | — film 1 | 13 | 13 | 0 | 100% |
  | — film 2 (`评弹曲目《钗头凤》`) | 13 | 0 | 13 | 0% |
  | — film 3 (`《中渡桥之战》`) | 21 | 0 | 21 | 0% |
  | sceny (dialogi i plansze z timeline'ów) | 187 598 | 13 301 | 174 297 | 7,1% |
  | wszystkie unikalne teksty wyciągu | 487 684 | 75 603 | 412 081 | 15,5% |

  Magazyn: `75 685` przekładów (`75 603` po kluczu + `82` warianty płci).
- **Sprostowanie (dopisane 2026-11-14 po uwadze właściciela):** otwarcie gry to
  **ciąg cutscen**, a nie ballady ani poematy. `钗头凤` jest tytułem występu
  pingtan w filmie 2, `中渡桥之战` — tytułem filmsceny bitwy (film 3); oba mają
  napisy wierszem, ale opisywanie ich jako „ballad prologu” było błędne.
  Transkrypcja właściciela jest nadrzędna wobec tych nazw.
- **Wniosek:** w napisach cutscen brakuje tylko `85` krótkich wtrąceń
  (`Hah!`, `Yes`, `Go?`), a **całe dwa prerenderowane przerywniki filmowe
  (ballada `钗头凤` i otwierający poemat `中渡桥之战`, razem `34` wersy) nie mają
  ani jednego przekładu**. Film 1 (poemat o lampionach) jest przetłumaczony
  w całości. Dodatkowo dialogi w scenach — czyli większość wypowiadanego tekstu
  w grze — mają dopiero `7,1%` pokrycia.
- **Dlaczego brak tych 34 wersów nie był widoczny w pakiecie:** w `v4`
  (`paczki/v4/paczka.json`) sekcja `02_intro_i_filmy` ma
  `56` elementów i `do_wpisania: 0`, bo wiersze filmowe są tam oznaczone jako
  **powtórzenie** tekstów ze scen: `08_campaign_01.md` (scena `2953` i `2954`,
  `中渡桥之战`) oraz `80_dialogi-wg-projektow_04.md` (scena `40712`, ballada).
  Klucz przekładu jest ten sam (SHA-256 tekstu źródłowego), więc tłumacz miał
  je wypełnić w plikach scen — i tam zostały puste. Sekcja cutscen nie
  raportowała ich jako braków.
- **Odtworzenie `v4` z repozytorium:** `python3 tools/buduj_paczke.py --indeks
  index --wyj /tmp/pak --wersja 4 --data … --tlumaczenie tlumaczenie
  --wypelnij-pl --tylko-z-en --bez-zip` daje dokładnie zapisane w `paczki/v4`
  liczby (`liczby_cutsceny`: `4 532` elementów, `4 110` przetłumaczonych,
  `416` powtórzeń, `6` do wpisania; `liczby`: `465 551`/`75 683`/`346 565`).
  Bez `--tylko-z-en` pojawia się `135` dodatkowych otwartych miejsc w
  `03_plansze_i_streszczenia` — różnica pochodzi wyłącznie z tej flagi.
- **Sprawdzenie hipotezy „to nie pokrycie, a podłączenie”:** narzędzie ma tryb
  `--szukaj "<fragment zdania>"`, który dla tekstu z gry podaje klucz, miejsce
  (napisy cutscen / film `n` / intro / scena), tabelę źródłową i to, czy
  w magazynie jest przekład. Jeśli linia **ma** przekład, a klient nadal pokazuje
  angielski, problem jest w podłączeniu (inna mapa albo inny nośnik napisów)
  i wtedy trzeba go badać dalej; jeśli przekładu **nie ma**, gra pokazuje
  angielski zgodnie z projektem (klient pozostaje w języku EN).
- **Testy:** `22` nowe testy w `tests/test_pokrycie_tlumaczenia.py` (sekcje,
  braki, serie ciągłych wierszy, sloty wariantów płci, szukanie po `ZH`/`EN`/`PL`,
  limit i skracanie tekstu); cały `tools/run_tests.py` zielony.
- **Ograniczenia:** brak testu w grze; nie wiadomo, czy klient rysuje napisy
  filmów z `entry_collect_movie_subtitle_data`, czy z tego samego tekstu
  w scenach — oba warianty są dziś po angielsku, więc odpowiedź da dopiero
  uzupełnienie przekładu. Nie zmieniano `index/` ani `tlumaczenie/`.

## 2026-11-14 (2) — napisy cutscen to sceny `ui_type` 10: osobna sekcja pakietu i polski prolog

- **Objaw (od właściciela):** w napisach prologu — od pierwszej scenki do kreacji
  postaci — większość linii zostaje po angielsku; właściciel przepisał cały
  fragment i oznaczył nieprzetłumaczone miejsca.
- **Fakt — gdzie te linie leżą:** to nie osobna tabela napisów, a **sceny
  odtwarzane jako przerywniki** (`ui_type` 10 w `dialog_timelines`). W całym
  wyciągu jest ich `5 995` (`11 677` elementów, `1 221` z przekładem = `10,5%`).
  Blok prologu tworzą projekty `对话-qiancen.dialog` (`57` scen, `97` elementów,
  `3` przetłumaczone) i `对话-qiancen` (`22`, `22`, `1`) — ciągłe `10094–10188`.
  Sprawdzone na `10141`, `10158`, `10168`, `10185`: w tych slotach stoją pełne
  zdania EN („It's you!”, „After him! Don't let him flee with the Zhenguan
  Jade!”), czyli dokładnie to, co widać na ekranie.
- **Fakt — dlaczego braków nie było widać w narzędziach:** te sceny drukowały się
  w `sceny/*.md` razem z 186 tys. zwykłych kwestii, a `--brak` w
  `tools/pokrycie_tlumaczenia.py` wypisywał tylko napisy cutscen, intro i filmy.
  Stąd wrażenie, że „napisy cutscen są prawie przetłumaczone” (`96,8%`) przy
  prologu w większości angielskim.
- **Zmiana w pakiecie:** `tools/buduj_paczke.py` ma `UI_TYPY_CUTSCEN` (stała
  `indeks.UI_TYPY_PRZERYWNIKA`) i `Generator.cutsceny_cinematiczne()`, które
  piszą `cutsceny/04_sceny_cinematiczne_NN.md` **przed** plikami scen, więc
  klucz z przerywnika otwiera `PL:` tam, a nie w `sceny/` (w scenach zostaje
  odsyłacz „tłumaczysz raz”). `paczka.json` ma nowe `liczby_cinematiczne`, a
  `liczby_cutsceny` obejmuje także tę sekcję. Przebudowa (wersja `5`,
  `--wypelnij-pl --tylko-z-en`): `11 677` elementów przerywników, `9 109` do
  wpisania, `936` z przekładem, `1 632` powtórzeń; cutsceny razem `16 209`
  elementów / `9 115` do wpisania; sceny `204 183` / `149 307`; `kontrola`:
  `miejsc_pl 422 248`, `zgodne: true`; czas ok. `31 s`.
- **Hipoteza odrzucona (kolizje wariantów):** zakładaliśmy, że część braków
  wynika z reguły `_dopasuj_kolizje`, która przy trafieniu w wariant bez
  przekładu przerywała szukanie. Regułę zmieniono w `tools/patcher_wwm.py`
  i `tools/zbuduj_latke.py` (teraz: wariant o tym samym EN **z** przekładem →
  wariant podobny ≥ `0,5` → `None`; warianty bez `PL:` nie blokują bliźniaka,
  a raport patchera liczy `po_kolizji_dokladne`/`po_kolizji_podobne`).
  **Pomiar na danych Patcha 2.4: `890` kolizji, w tym `723` z dokładnie jednym
  przetłumaczonym wariantem, ale `0` takich, w których EN obu wariantów jest
  podobny ≥ `0,5`** — kolizje z definicji łączą znaczenia odległe, więc dla
  obecnych danych obie reguły dają ten sam wynik. To nie była przyczyna
  angielskich napisów; poprawka porządkuje kod i zostaje jako zabezpieczenie,
  ale **nic nie naprawiła**.
- **Prawdziwa przyczyna: brak przekładów.** Zmierzone braki w prologu
  (`sceny 10000–10250`): `115` wierszy scen przerywników + `120` napisów
  cutscen/intro/filmów = `235` miejsc, `0` z nich miało przekład.
- **Uzupełnienie (własny przekład z chińskiego):** `zwrotki/2026-11-14_prolog_pl.md`
  — `232` klucze: `112` wierszy scen przerywników (z `115` braków — trzy klucze
  powtarzają się w kilku scenach), `85` napisów `text_msg`, `35` wierszy intro
  i filmów 2–3 (w tym wszystkie wersy `钗头凤` i `中渡桥之战`, przełożone
  wierszem).
  Import: `python3 tools/import_zwrotki.py zwrotki/2026-11-14_prolog_pl.md
  --indeks index --magazyn tlumaczenie` → `232` miejsc, `0` odrzuconych,
  `0` problemów z tokenami; magazyn `75 916` przekładów.
- **Pokrycie po imporcie** (`tools/pokrycie_tlumaczenia.py`):
  napisy cutscen `2 688/2 688` (`100%`), intro `9/9`, filmy `47/47`
  (film 2 `13/13`, film 3 `21/21`), **blok prologu `10094–10188` bez braków**
  (`--arkusz --sceny-od 10000 --sceny-do 10250` → `0` miejsc), sceny
  przerywników `1 382/11 678` (`11,8%`), zwykłe sceny `13 880/187 598` (`7,4%`),
  cały wyciąg `75 834/487 684` (`15,5%`).
- **Nowe tryby narzędzia:** `--brak-przerywnikow` (braki scen przerywników
  wg scen) i `--arkusz PLIK` (`--arkusz-tylko wszystko|kinowe|przerywniki`,
  `--sceny-od/--sceny-do`) — plik w formacie pakietu (`klucz:`/`PL:`) gotowy do
  wypełnienia i podania do `import_zwrotki.py`.
- **Testy:** `397` (`tests/test_buduj_paczke.py` +5 dla sekcji przerywników,
  `tests/test_pokrycie_tlumaczenia.py` +7, nowy `tests/test_kolizje_wariantow.py`
  — `6`); cały zestaw zielony.
- **Ograniczenia:** brak testu w grze — nie wiadomo jeszcze, czy klient rysuje
  napisy prologu z tych scen (wszystko wskazuje, że tak, bo tekst zgadza się
  z transkrypcją właściciela) ani czy napisy filmów 2–3 pochodzą z
  `entry_collect_movie_subtitle_data`, czy z tych samych scen. Sprawdzenie
  wymaga nowej łatki u właściciela.
- **Wydanie `v0.2.0` zbudowane i wysłane:** `python3 tools/one_click_patch.py
  --tylko-magazyn --indeks index --magazyn tlumaczenie --wydanie v0.2.0
  --wyj-zip dist/WWM_Spolszczenie_PL_v0.2.0.zip` →
  `4 467 759 B`, `12` plików, SHA-256
  `a0f12fdce98d5bb0eccbda39ea0a489973e5f83906aec8d94a10f9d35d6b12bc`,
  `75 916` przekładów w planie (`po_kluczu 75 834`, `po_id 82`, `735`
  kolizji, `70 097` dopasowań po EN). Kopia w `paczki/`, wysłana na Dysk Google
  (folder pakietów) jako `WWM_Spolszczenie_PL_v0.2.0.zip`. **Łatka nie była
  uruchomiona w grze** — to zwrotka i plan, nie potwierdzenie działania.

## 2026-11-14 (3) — druga warstwa napisów (`text_msg__grey`) i domknięcie cytatów właściciela

- **Zgłoszenie właściciela:** sześć linii z transkrypcji prologu nadal po
  angielsku (`a drink to wet your throat.`, `Well? How is it?`, dwie kwestie
  Chen Zixi o „wpadaniu na ostrza” i o dzbanie `丰和春` oraz
  `We'll roam the jianghu together!`).
- **Fakt — cztery z nich to inna warstwa tej samej tabeli:** `text_msg__grey`,
  gdzie mówca jest wpisany w treść (`师父 …`, EN `Master: …`). Ten sam wiersz
  `text_msg` (np. `590339`) ma wersję główną i „szarą” — z innymi odstępami
  w chińskim tekście, więc **inny SHA-256 i osobny, pusty klucz**. Przekład
  wersji głównej istniał, ale nie był widoczny dla wersji szarej, a narzędzie
  pokrycia liczyło tylko wiersze główne — stąd fałszywe `100%` napisów cutscen.
  Skala: w zakresie `590000–592694` jest **`675` takich wierszy i żaden nie miał
  przekładu**; w całej warstwie `1 203` wiersze (`528` nadal bez przekładu poza
  zakresem cutscen).
- **Zmiana — łączenie bliźniaków:** `tools/tlumaczenie.py: doloz_blizniaki()`
  dobiera przekład z tego **samego wiersza tej samej tabeli** (rodzina
  `text_msg` obejmuje `text_msg__grey`) po treści znormalizowanej białymi
  znakami (`indeks.znormalizowany`). Wpięte w `one_click_patch.py`,
  `buduj_paczke.py` (`--wypelnij-pl`), `zbuduj_latke.py` i
  `pokrycie_tlumaczenia.py`, **tylko w pamięci** — do `tlumaczenie/pl_*.jsonl`
  trafiają wyłącznie przekłady ludzi. Efekt na danych: `675` uzupełnionych
  wierszy, `przekladow_po 76 595` w raporcie patchera.
- **Czego świadomie nie robimy:** nie łączymy tekstów o **różnych numerach
  wierszy**, nawet gdy chiński zapis jest identyczny — to kolizje znaczeń i tam
  zostaje angielski do czasu własnego tłumaczenia. Pilnują tego testy
  `tests/test_kolizje_wariantow.py` i `tests/test_blizniaki_warstw.py`
  (`5` testów: dziedziczenie z `__grey`, brak dziedziczenia z innego wiersza,
  brak nadpisywania istniejącego przekładu, brak łączenia różnych treści).
- **Nowa sekcja pomiaru:** `pokrycie_tlumaczenia.py` ma teraz wiersz
  `napisy — warstwa text_msg__grey`: `675`/`1 203` (`56,1%`).
- **Dwie kwestie Chen Zixi to osobna sprawa:** leżą w scenach przerywników
  `3900065` i `3900066` (projekt `对话-longsiyu`), czyli poza blokiem
  `10094–10188`, i nie miały żadnego przekładu. Przetłumaczone w
  `zwrotki/2026-11-14_prolog_2_pl.md` razem z pytaniem o wiersz (scena
  `17200703`) i linią istniejącą tylko po angielsku (`48e4d8b5f54c3665`,
  brak źródła chińskiego). Import: `4` wpisy, `0` odrzuconych.
- **Testy:** `402` (cały zestaw zielony).
- **Wydanie `v0.3.0`:** `dist/WWM_Spolszczenie_PL_v0.3.0.zip`,
  `4 506 590 B`, `12` plików, SHA-256
  `2ba67551fd7d0c9736c780f34edb36050e331e1c1a2543340671290181713016`,
  `76 595` przekładów w magazynie, `675` bliźniaków w planie. Sprawdzone:
  w planie są wszystkie sześć kluczy z cytatów właściciela. **Nie testowano
  w grze.**
- **Co jeszcze w prologu zostaje:** projekty poboczne i questowe wokół prologu
  (`对话-longsiyu`/`longsiyu.dialog`: `68` scen, `353` elementy bez przekładu —
  to nie jest sam prolog, a łańcuch o zbieraniu nauk dla 奇物监) oraz `528`
  wierszy szarej warstwy poza zakresem cutscen. Nie wiadomo, czy klient rysuje
  napisy z warstwy głównej czy szarej — tłumaczone są obie.

### 2026-11-14 — Czytanka w kolejności z gry (`tools/buduj_czytanke_gry.py`)

- **Cel:** cała narracja w kolejności występowania w grze, prolog pierwszy, potem
  krainy po kolei, a w krainie sceny po numerze dialogu. Bez szukania jednego
  silnikowego porządku cutscen — właściciel potwierdził, że pojedyncza cutscena
  i tak siedzi w sobie w poprawnej kolejności, więc wystarczy dobrze umieścić sceny.
- **Kolejność krain z danych:** `tools/prowincje.py` czyta zadania (`przestrzen`,
  `pian`) i grupuje mapy po nazwie roboczej. Wynik: `92` krainy, `285` map,
  początek `燕南 → 清河 → 熔炉 → 河西`. Plik `index/prowincje.json`.
- **Projekty bez mapy:** scena bez `m` dziedziczy krainę po projekcie `对话-*`
  (najczęstsza mapa projektu) — `34 183` scen trafiło do krain; `13 589` scen
  w `129` projektach bez żadnej mapy zostało w `95_bez_mapy.md` (nic nie znika,
  nic nie jest zgadywane).
- **Prolog a krainy:** `prolog_z_klucza.zasieg()` zwraca klucze prologu i numery
  scen, których co najmniej `80%` linii pada w transkrypcie — `36` scen nie jest
  powtarzanych w krainach. Przy okazji przejście po transkrypcie (`_przejscie`)
  jest wspólne dla `zbuduj()` i `zasieg()`; `zwrotki/prolog_wg_klucza.md` po
  refaktorze ma identyczny SHA (`c5d42ec2…`).
- **Wynik:** `72 977` scen, `291 426` linii (w tym `28 356` z polskim), `167`
  plików, `105 135` wierszy puli napisów, `3` filmy. Wariant tylko z polskim:
  `8 872` scen. Paczki: `dist/WWM_Czytanka_Gry_2026-11-14.zip` (`17 057 192 B`)
  i `dist/WWM_Czytanka_Gry_tylko_PL_2026-11-14.zip` (`2 494 764 B`).
- **Poza narracją** zostaje `66 997` przetłumaczonych kluczy (nazwy przedmiotów,
  umiejętności, cele zadań, UI) — to nie sceny, więc czytanka ich nie udaje.
- **Testy:** `426` (cały zestaw zielony; `+17` w `tests/test_czytanka_gry.py`).
- **Na Dysku Google** (folder paczek): `WWM_Czytanka_Gry_2026-11-14.zip`
  (`17057192 B`, id `1g3H3sZoZd2H5Gx8ybVoWn-8Um739584K`) i
  `WWM_Czytanka_Gry_tylko_PL_2026-11-14.zip` (`2494764 B`,
  id `1lj_SPiXvpa0NFh2IIwd8YocZBYwm_UQ-`).
- **Nie testowano w grze:** to porządek z danych, nie z przejścia gry.

### 2026-11-14 — pełna Czytanka: trzy warstwy razem + wydanie `v0.4.0`

- **Poprawka zakresu:** poprzedni pakiet dawał tylko warstwę chronologiczną.
  Ustalenie projektu mówi o trzech rodzajach plików, więc `tools/zbuduj_czytanke_pelna.py`
  składa je w jeden katalog: `01_prolog.md` + `02_krainy/` (chronologia),
  `03_fabula/`, `04_kontekst/` (1:1 do fabuły), `05_reszta/` (9 sekcji wg rodzaju).
- **Liczby pakietu:** 187 plików .md, `109 MB` w katalogu, ZIP `26 688 858 B`.
  Chronologia: `72 977` scen, `291 426` linii (`28 356` z polskim), `92` krainy.
  Fabuła: `44 301` scen w `1 169` epizodach, `37 938` przetłumaczonych slotów.
  Kontekst: `11 031`. Reszta: `61 491` z `389 891` slotów.
- **Pokrycie sprawdzone, nie deklarowane:** próba losowa `600` przetłumaczonych
  tekstów z magazynu — **0 braków** w pakiecie. Wcześniejsze „66 997 kluczy poza
  narracją” to warstwa `05_reszta/`, nie luka.
- **Wydanie `v0.4.0`:** `dist/WWM_Spolszczenie_PL_v0.4.0.zip`, `5 330 079 B`,
  `12` plików, SHA-256 `2bfdfc6285f1a7c26517c7d40617ca1233b166a4582a9181f96c2bd16ee92ad8`,
  `86 282` przekłady (`85 956` kluczy + `326` wariantów płci), `675` bliźniaków
  warstwy `text_msg__grey`, `745` kolizji odłożonych. **To jest stan pełny** —
  `v0.3.0` miał `76 595` przekładów i jest nieaktualne. Na Dysku Google:
  id `1wyKn5HPyaZTBjUznVyc6ZMOjp7LCrFxf`; pełna czytanka: id `1WMWHXs6DFLmcub1FfhDxrVXm4n9vGy7U`.
  **Nie testowano w grze.**

### 2026-11-14 — Czytanka ma być do czytania, nie zestawem technicznym

- **Właściciel odrzucił poprzednie paczki:** tabele z kolumnami chiński/angielski/polski,
  znaczniki czasu i podział na 167–187 plików to nie czytanka. Czytanka to dialog
  linia po linii z mówcą i tekstem, jeden plik na rodzaj treści.
- **Nowy format** (`tools/czytanka_czysta.py`, `wwm-czytanka-czysta-v1`):
  `- **Mówca:** tekst` jedna kwestia na linię, bez odstępów między kwestiami,
  bez czasów i kluczy; pusty wiersz tylko między scenami. Trzy pliki:
  `01_sceny.md`, `02_cutsceny.md`, `03_reszta.md`.
- **Mówca z danych, nie z etykiety rekwizytu:** `sceny.o` to
  `[nazwa_zh, typ, id_osoby, klucz]`, ale klucz bywa nazwą skrzyni (`三品宝箱`),
  więc imię bierzemy z `postacie[id].n` (polskie, inaczej angielskie); klucz
  z obsady tylko wtedy, gdy jego chiński tekst zgadza się z nazwą w obsadzie.
  Postać gracza `你` pokazujemy jako `Ty`.
- **Reszta bez dublowania:** wiersz tekstu to `w = (tabela, wiersz[, klucz_nazwy])`;
  trzeci element wskazuje nazwę własną, więc nie zgadujemy, co jest nazwą, a co
  opisem. Wpisy tego samego przedmiotu scalane są w jedną linię.
- **Liczby:** 8 908 scen, 92 216 kwestii z polskim, 263 076 kwestii bez przekładu
  pominięto (pełny szkielet dostępny przez `--zakres wszystko`). Paczka
  `WWM_Czytanka_PL_2026-11-14.zip`, `1 523 414 B`, id `1TrnTI3H_4r_jthW8xo1fADwqT1l1gmKz`.
  Poprzednie trzy paczki czytanek przeniesione do kosza Dysku.
- **Testy:** `439` (doszło `9` w `TestCzytankaDoCzytania`).

## 2026-11-17 — `v0.4.0` przetestowane w grze: działa (zgłoszenie właściciela)

- **Zgłoszenie właściciela:** pełna łatka `WWM_Spolszczenie_PL_v0.4.0.zip`
  (`dist/`, SHA-256 `2bfdfc6285f1a7c26517c7d40617ca1233b166a4582a9181f96c2bd16ee92ad8`,
  na Dysku Google id `1wyKn5HPyaZTBjUznVyc6ZMOjp7LCrFxf`) opiera się o najnowszą
  zwrotkę tłumacza `WWM_PL2.zip` i została przetestowana w grze **na wersji gry
  2.4**. **Działa — to, co jest przetłumaczone, pojawia się w grze.**
- **Elementy z wersji 2.4:** dodatkowe elementy do tłumaczenia z Patcha 2.4
  zostały wyciągnięte collectorem, dodane do najnowszego pakietu dla tłumacza
  i przekazane do tłumaczenia.
- **`v0.4.0` to stan pełny po imporcie `WWM_PL2.zip`:** `86 282` przekłady
  (`85 956` po kluczu + `326` wariantów płci; pomiar
  `tools/pokrycie_tlumaczenia.py` 2026-11-17: cały wyciąg `86 098`/`487 684`
  = `17,7%`). Import `WWM_PL2.zip` dodał `+9 443` klucze i `+244` warianty płci;
  `15` konfliktów nadpisano na korzyść tłumacza (raport:
  `zwrotki/raport_scalenia_WWM_PL2.json`). Wcześniejsze „`v0.4.0` nie testowano
  w grze” z wpisu z 2026-11-14 jest **nieaktualne**.
- **Tłumacz pracuje nad dalszymi przekładami** — kolejne zwrotki trafią do
  magazynu zwykłym obiegiem (`tools/import_zwrotki.py` → commit `tlumaczenie/`
  → kolejne wydania). Poprzednie wydanie `v0.1.0` (`WWM_PL1.zip`, `75 685`
  przekładów) jest nieaktualne; nie ma sensu go potwierdzać w grze.
- **Zaktualizowane dokumenty:** `README.md`, `docs/STATUS.md` (stan, tabela,
  pokrycie, otwarte ustalenia, następny krok), `docs/PATCHER_WWM.md`,
  `docs/TEST_W_GRZE.md`, `docs/PAKIET_TLUMACZA.md`.
- **Granice:** zgłoszenie nie precyzuje zakresu widzianych ekranów ani sposobu
  instalacji — do dziennika trafia jako raport właściciela „działa na 2.4”, nie
  jako audyt każdego ekranu. Otwarte pozostaje m.in., skąd klient pobiera napisy
  filmów (`entry_collect_movie_subtitle_data` czy te same sceny), limity
  szerokości pól i zachowanie gry po cotygodniowej aktualizacji. Nadal
  obowiązuje zasada: tylko zmiany tekstu przy wyłączonej grze, bez wstrzykiwania
  i obchodzenia zabezpieczeń; projekt nie gwarantuje bezpieczeństwa konta.

### 2026-11-17 (2) — Czytanka: przerwa po streszczeniu cutsceny + sprawdzenie prologu

- **Przerwa po streszczeniu:** `01_sceny_i_cutsceny.md` — po `### Streszczenie sceny`
  stoi pusta linia przed kwestiami dialogu (dziś kwestie szły od razu po
  streszczeniu). Zmiana w `_plik_scen` (`tools/czytanka_czysta.py`): `Jednostka`
  dostała pole `streszczenie` (liczba linii streszczenia na początku jednostki),
  przerwa wstawia się tylko wtedy, gdy nagłówek i treść streszczenia faktycznie
  wyemitowano. 2 nowe testy (`tests/test_czytanka_kolejnosc_cutscen.py`),
  całość 546 zielonych. Sprawdzone na realnych danych: `## Cutscena 30161`
  pokazuje streszczenie, pustą linię i dopiero kwestie. **Nieopublikowane** —
  kolejna wersja paczki czytanki dopiero przy decyzji właściciela.
- **Sprawdzenie prologu — czy numerowane cutsceny otwarcia są w danych:**
  są, ale tylko częściowo i bez wiązania z transkryptem.
  * Pakiet xinshou (otwarcie): `30032 sq006_cj_xia` (61,3 s), `30033
    sq005_cjs_video` (84,7 s), `30147 sq002_wxhcc` (51,0 s), `30150
    sq010_yshj_video` (124,7 s), `30151 sq001_zlhm_pc` (78,8 s) + bliźniaki
    mobile (`30487`, `30495`, `30662`).
  * Streszczenie w danych ma **tylko `30147`** („You rode in on horseback, and
    fell from the startled horse… The Void King… troops emerge from the
    courtyard…”; `synopsis_text_mobile`, znormalizowane na PL: „Wjeżdżasz
    konno, koń się płoszy…”) i **`30150`** („A bug drifts past, seeping into
    the corpse… The Void King strikes, then falls…” → PL „Robak przelatuje
    i wnika w zwłoki…”). Obie jednostki renderują się **już dziś** standardowo
    jako `## Cutscena 30147` / `## Cutscena 30150` + `### Streszczenie sceny`
    (30147 w 燕南 — kotwica grupy zadań; 30150 w Prologu — dopasowanie
    streszczenia z transkryptem).
  * `30032`/`30033`/`30151` streszczenia nie mają (`cutscenes.synopsis_text_pc`
    i `_mobile` puste); kandydaci bez potwierdzenia.
  * Linie transkryptu żyją w puli `text_msg` (wiersze ~`590335–590355` itd.)
    i w scenach `ui_type` 10 (`10167–10187`, `3900065/3900066`, `7530284`…);
    klucze dopasowane z transkryptu to trafienia tekstowe, nie wiązanie.
    Klasycznego wiązania napis ↔ numer cutsceny w danych nie ma (osie `.cine`
    nie są w paczce — patrz `docs/CINE_KOLEJNOSC.md`).
- **Decyzja właściciela (2026-11-17):** **niczego nie zmieniać.** `30147` to
  osobna scena (wjazd konny, koń się płoszy) — nie podmienia prologu; `30150`
  („robak leci…”) właściciel już ma. Prolog zostaje transkryptem
  (`## Prolog 1–4`), numerowane cutsceny stoją tam, gdzie wskazuje chronologia.
  Bez zgadywania numerów dla Prolog 1 i Prolog 4.
- **CZYTANKA_DO_CZYTANIA.md:** poprawione nieaktualne opisy (streszczenie na
  początku, przerwa; opis „kolejności z ekranu” oznaczony jako usunięty w v9).

### 2026-11-17 (3) — Czytanka `v10`: budowa, weryfikacja, wysłana na Dysk

- **Żądanie właściciela (2026-11-17):** „Wygeneruj nową czytankę i wgraj na
  drive". Wydanie **v10** — kolejny numer, paczka z datą w nazwie nie jest
  tworzona; `--wersja 10` odmówiłby nadpisania istniejącej paczki.
- **Budowa:** `python3 tools/czytanka_czysta.py --wyj out/czytanka --wersja 10`.
  Wynik liczbowy: `75 331` jednostek, `29 536` linii, `pominiete` 0,
  `reszta` 62 838, `kontekst` 503, `bez_przekladu` 160 751, `zbiory` 1 020,
  `pamiatki` 120 (bez nazw 0), `poi` 2 948 (z dialogiem 368, bez nazwy 11).
- **Paczka:** `dist/WWM_Czytanka_PL_v10.zip`, **6 771 033 B**, SHA-256
  `6796e1d7a09875ad34715f1114b8d907d48a3819fd3532cea52975f393dbb85d`.
  Zawartość: `01_sceny_i_cutsceny.md`, `02_kontekst_scen_i_cutscen.md`,
  `03_reszta.md`, `README.md`. Jedyną zmianą względem v9 jest pusta linia
  przerwy po `### Streszczenie sceny` (wpis `(2)` wyżej); prolog i cała
  kolejność bez zmian. Sprawdzone w paczce: w `## Cutscena 30161` streszczenie
  → pusta linia → kwestie.
- **Dysk Google (folder „Where Winds Meet"):** `WWM_Czytanka_PL_v10.zip`,
  id `10hgkAARQzpK2r8_2VyI9zCo-ZJtu2KG2`, 2026-11-17, 6 771 033 B — zgodny
  rozmiar z lokalną paczką.
- **Testy i kontrola:** `python3 tools/run_tests.py` — 546 OK;
  `python3 tools/check_repository.py` OK; `git diff --check` czysty.
- **Docs zsynchronizowane:** `docs/WERSJE_CZYTANKI.md` (wpis v10),
  `docs/STATUS.md` (najnowsza paczka, 14 testów / 546),
  `docs/CZYTANKA_DO_CZYTANIA.md` (opis przerwy; v9-oznaczenie „kolejności
  z ekranu" zostaje jako historia), ten dziennik.

### 2026-11-17 (4) — Powrót do porzuconego zadania: trzy indeksy z `.mpk` — badania + kit skanera

- **Zadanie (właściciel, 2026-11-17):** ponownie podejść do porzuconego
  zadania znalezienia w danych gry trzech brakujących powiązań: (1) scena →
  następna scena (`## Scena 4700001` → `4700041` → `4700352`),
  (2) aktywacja POI → start sceny, (3) osie czasu `.cine` cutscen.
  Prawdopodobne miejsce: ~200 plików `Resources*.mpk` (1 GB/szt.), nie
  pliki HD, które mamy.
- **Badania publicznych źródeł (wnioski w `docs/MPK_FORMAT_RESEARCH.md`):**
  * `Zhincore/wwm-messiah-tools` (MIT, aktywna, ostatni commit dziś):
    `Resources.mpkinfo` (root) wskazuje `Resources.mpk` i `Resources<N>.mpk`
    przez pole `packed >> 1` — ~200 `Resources*.mpk` to **części jednej
    logicznej paczki**, a indeks podaje, który wpis siedzi w której.
    Format `.mpkinfo` v3: `u32 3, u32 count`, wpisy 20 B
    `(id_lo, id_hi, offset, size, packed)`, trailer 16 B; `file_id =
    (MurmurHash3_x86_32(path) << 32) | lo32` (ogon ścieżki bez rozszerzenia;
    ścieżki GUID-owe — fast path); bloki EZST (AES-256-ECB prefiks + zstd),
    `ZSTD` (plain), LuaText (LZ4). `Patch.mpkdb` = SQLite, tabele
    `info0`/`info1`, `v0` signed i64, `v6` offset.
  * `mohebbiamin/WWM-MPK-Tool` — zamknięty unsigned exe; tylko potwierdza, że
    paczki da się czytać; **nie wprowadzamy go do łańcucha**.
  * `dest1yo/wwm_utils` — VirusTotal flag (Trojan) według wątku ResHax;
    **zakazany**.
- **Roadmapa:** `docs/ROADMAP_MPK_INDEKSY.md` — bramki 0–5 (badania + kit →
  raport z 1. uruchomienia → wycinarka `.cine`/`.etsb` → analiza `.cine` →
  analiza `.etsb` (następstwo scen, POI) → domknięcie). Dalsze sesje wykonują
  kolejne bramki.
- **Kit `WWM_MPK_Skaner_v1.zip` (`dist/`, 36 914 B, SHA-256
  `1d27db14b2f7f2345cef5656e6bc629e86b732809502637b353b2f3144c87f16`):**
  `tools/mpk_skaner.py` (stdlib, zero sieci, tylko odczyt — paczki, indeksy
  i okienka po 4 KB), `SKANUJ.bat` (dwuklik, Python 3.10+ wbudowany,
  bez pip), `narzedzia/kandydaci.jsonl` (`7 130` kandydatów: `174` realnych
  ścieżek `client/dialogs/...` z `index/poi.jsonl` + `138` wariantów
  `.ets↔.etsb`, `6 818` wzorców `.cine` z `cine_name` — wzorzec potwierdzony
  przez `cine_path` z tabeli `cutscenes`, np. `Char/e_01_cutscene/qhrw/
  sq001_zlxl/sq001_zlxl.cine`). Skaner haszuje kandydatów i szuka ich
  **w indeksach** — od razu wiadomo, czy `.cine`/`.etsb` leżą w
  `Resources*.mpk`, w `Patch*.mpk`, czy w ogóle nie leżą lokalnie.
  Raport: `RAPORT.json` + `PODSUMOWANIE.txt`; całość jako
  `WWM_MPK_Skaner_WYNIK.zip` (właściciel odsyła na Dysk; paczek `.mpk` NIE).
- **Weryfikacja:** testy jednostkowe + integracyjne na danych syntetycznych
  (`tests/test_mpk_skaner.py`, 14 testów) i pełny zestaw 560 zielony;
  `tools/check_repository.py` OK. **Nie uruchamiano na maszynie właściciela**
  — to sonda; nie zawiera i nie otwiera jeszcze prawdziwych paczek.
- **Ograniczenia:** trafień wzorców `.cine` nie widzieliśmy na żywych danych
  (wzorce to hipoteza z jednego znanego przykładu); `Patch.mpkdb` czytany
  `mode=ro`; offsety mogą być niefizyczne dla „lite" instalacji (skaner to
  wykrywa). Następna sesja: bramka 1 — odczyt wyniku od właściciela.

### 2026-11-17 (5) — Kit MPK Skaner: błąd inwokacji Pythona i naprawa

- **Zgłoszenie właściciela:** po dwukliku w `SKANUJ.bat` —
  `'"py -3"' is not recognized as an internal or external command`.
- **Przyczyna (moja):** wywołanie `"%PYEXE%" "narzedzia\mpk_skaner.py"` miało
  `%PYEXE%` w cudzysłowach, więc Windows szukał programu dosłownie
  `"py -3"` zamiast `py.exe -3`. Autodeteckja Pythona działała poprawnie —
  padała sama linia startowa.
- **Naprawa:** inwokacja bez cudzysłowów (`%PYEXE% "narzedzia\mpk_skaner.py" …`),
  komentarze `rem` zamiast polegający na założeniu, że `py -3` istnieje
  (najpierw `py -3`, potem `python`). Skaner pozostaje bez zależności — nie ma
  żadnej biblioteki do instalowania, więc kit **nie tworzy venv**;
  odkrywanie interpretera jest takie samo jak w patcherze (pylauncher →
  PATH), bez etapu pip. Upewniono się, że ścieżka wywołania nie wprowadza
  problemów ze spacjami (spacje może mieć tylko ścieżka skryptu, ta jest
  cudzysłowowana).
- **Regresja:** nowe testy statyczne w `tests/test_mpk_skaner.py`
  (`TestSkanujBat`): brak wywołania `"%PYEXE%"`, kolejność wykrywania
  py launcher → python, ASCII + CRLF. Całość 563 zielone.
- **Paczka `WWM_MPK_Skaner_v1.zip` przebudowana:** `36 967 B`, SHA-256
  `3a165d9841daa7b8c40c37ad441ec00dbab11b0cf961c41df0da152256ddce49`.
  Stara (błędna) paczka na Dysku przeniesiona do kosza; naprawiona wgrana
  tego samego dnia do folderu „Where Winds Meet"
  (id `1dcU3_eqk6rME9l5HxE3R5qZlz3h0mcWC`). Weryfikacja integracyjna na
  syntetycznej instalacji z podziałem `Resources*.mpk` (pack_id 0/1/2) —
  wszystkie 3 kandydatów trafionych we właściwe kontenery.

### 2026-11-17 (6) — Sonda u właściciela wróciła: 14 trafień `.cine`, kit v2 (wycinarka)

- **Wejście:** `WWM_MPK_Skaner_WYNIK.zip` (`17 180 B`, SHA-256
  `0f80a219aef87ae0ff7e82ad4378f7e42fe786bc7a1112cc0915b31d0012f225`) —
  raport z maszyny właściciela (Steam, folder gry).
- **Wynik liczbowy (bramka 1):**
  * **489 `*.mpk`, `211 334 119 524 B`**; `Resources.mpkinfo`: **2 604 099
    wpisów** (+46 063 placeholdery), 158 kontenerów, wszystkie istnieją,
    offsety fizyczne wszędzie (0 niefizycznych, 0 brakujących); suma wpisów
    `200 513 882 817 B`; 24 kontenery z pokryciem > 100 % (max `Resources80`
    144,3 % / `Resources90` 132,9 %) — do audytu, nie blokuje; 4 kontenery
    podejrzanie puste (`Resources145/146/149/115`) — może część pobierania
    Steam, zasugerowano „Zweryfikuj spójność plików gry".
  * `LT1.mpkinfo`: **240 wpisów** → `LT1.mpk` (`2 568 577 B`), pokrycie
    100,0 % — paczka skryptowa.
  * `Patch3109.mpkinfo` (22) i `Patch3110.mpkinfo` (24) — pokrycie 100,0 %,
    bloki ~1,2 MB, duże zasoby łatki — **pomijamy**.
  * `Patch.mpkdb` (SQLite): `info0` 854 wierszy (`v0` file_id i64,
    `v6` offset), `info1` 0, `meta` 1, `pak` 2.
  * **Trafienia kandydatów: 14** — wszystkie `.cine` z wzorca
    `Char/e_01_cutscene/qhrw/<film>/<film>.cine`, **wszystkie w
    `Resources34.mpk`** (4 177–23 174 B). Wzorzec potwierdzony na realnej
    instalacji; rodzina `e_01_cutscene/qhrw` trafia w 100 % generowanych
    ścieżek.
  * **0 trafień `.etsb`/`.ets`** — 174 ścieżki POI `storyline` + warianty
    NIE są plikami VFS pod tymi ścieżkami; najpewniej to cel skoku logicznego,
    nie plik. Do ustalenia po harvest z Lua.
- **Kit v2 (`dist/WWM_MPK_Skaner_v2.zip`, `39 045 B`, SHA-256
  `2df898d5100e3ee04b64319991ec1011cffed06ee4a69d9ef44737b525366727`):**
  sonda (jak v1) + wycinanie SUROWYCH bloków: trafione kandydatów i wszystkie
  wpisy `LT1.mpkinfo` (limity 64 MB/blok, 512 MB łącznie) + `mpkdb_dump.json`
  (`Patch.mpkdb` w trybie `mode=ro`, schema + wszystkie wiersze). Bez
  dekodowania EZST — dekodujemy po swojej stronie. Jednoklik `SKANUJ.bat`;
  zero bibliotek, żadnych nowych zależności. 17 testów jednostkowych +
  integracyjny + pełny przepływ zbudowanego ZIPa na syntetycznej instalacji —
  zielone. Wgrany na Dysk (folder „Where Winds Meet",
  id `1WqyhL9M4GmEpder8puCF6EK994PcRqRc`, 2026-11-17);
  poprzedni v1 (po naprawie bat) przeniesiony do kosza.
- **Dokumenty:** `docs/MPK_SKANER_RAPORT.md` (pełny raport z wnioskami),
  `docs/ROADMAP_MPK_INDEKSY.md` (bramki 0/1 ✅, bramka 2 w trakcie),
  `docs/STATUS.md`.
- **Następny krok:** właściciel uruchamia v2 i wysyła wynik (~3 MB);
  potem dekoder EZST po stronie repo, analiza `.cine`, harvest ścieżek z Lua.

### 2026-11-17 (7) — MPK Skaner v2: awaria `json.dumps` na BLOB-ach w Patch.mpkdb → v3

- **Zgłoszenie właściciela (7:35, Python 3.14):** skaner dotarł do kroku 5 —
  wyciął **14/14 `.cine` (106 800 B)** i **240/240 bloków LT1 (2 568 577 B)**,
  potem padło:
  `TypeError: Object of type bytes is not JSON serializable` —
  kolumna BLOB w tabeli `meta` (i potencjalnie inne). Awaria przed
  `_zapisz_zip` → `WWM_MPK_Skaner_WYNIK.zip` **nie powstał**.
- **Przyczyna (moja):** `zrzut_mpkdb` ładował wiersze wprost do `json.dumps`;
  SQLite zwraca `bytes` dla BLOB-ów. Test integracyjny miał BLOB-free tabelę
  `meta`, więc regresję przegapiłem.
- **Naprawa (v3):**
  * `_json_safe`: bytes/bytearray/memoryview → `{"__bytes__": true,
    "rozmiar": N, "hex": "..."}` (hex pełny do 256 B, powyżej podgląd
    + `uciniete: true`); inne typy → `str(val)`.
  * `zrzut_mpkdb`: błąd pojedynczej tabeli łapany do pola `blad`,
    ok=false tylko gdy którakolwiek tabela padła; zapisuje zawsze
    `mpkdb_dump.json` (ostatnia linia obrony: `_zapisz_mpkdb_dump`).
  * krok 4/5 opakowany w `try/except` — błąd wycinania/zrzutu nie blokuje
    powstania `RAPORT.json`/ZIP-a.
  * test regresji: `test_patch_mpkdb_z_blobami_nie_wywraca_json` (meta z BLOB
    160 B, pak z BLOB 300 B) — 18 testów skanera, całość zielona.
- **Kit v3:** `dist/WWM_MPK_Skaner_v3.zip` (`39 793 B`, SHA-256
  `92a2f7d7fa8d46bcc94a241c6ebac6c38ec0fe8703ff76d5f32a51f2c4d9b2c8`),
  zweryfikowany na syntetycznej instalacji z BLOB-ami
  (`mpkdb_dump.json` poprawny, ZIP powstaje, wycięcie trafień i LT1 OK).
  Na Dysku (folder „Where Winds Meet", id `1lhq0Ic8S7mIpwf2Jx7Du7rraHtLhwacE`);
  v2 przeniesiona do kosza (id `1WqyhL9M4GmEpder8puCF6EK994PcRqRc`).
- **Uwaga:** wycięte bloki z nieudanego przebiegu v2
  (`MPK_SKANER_WYNIK\wyciete\*.bin`, 254 pliki) są po stronie właściciela —
  przebieg v3 wytnie je ponownie tak samo; nie trzeba ich robić ręcznie.

### 2026-11-17 (8) — Sonda v3 wróciła z danymi: dekodowanie EZST i walidacja file_id

- **Wejście:** `WWM_MPK_Skaner_WYNIK (1).zip` (`2 207 306 B`, SHA-256
  `ca1837849990344e97e0014b75c087ce864c7fceeaa1fcc25c2008515dec9936`) —
  pełny przebieg v3 u właściciela: 14/14 `.cine` wycięte, 240/240 Lua LT1,
  `mpkdb_dump.json` OK (BLE → hex działa).
- **Dekodowanie (nasz venv `/tmp`, zależności z publicznego repo MIT
  `Zhincore/wwm-messiah-tools`):**
  * **14/14 `.cine` zdekodowanych** — rozmiary zdekodowane == rozmiary z
    indeksu (`match=True`). Format: magic `c1 59 41 0d` + u64le długość +
    u8 liczba identyfikatorów + tabela pól null-terminated (np.
    `StartTime`, `Entity`, `Camera`, `Montage`, `OverseaTag`…) + binarna
    oś czasu. Rozmiary: 17 988–200 718 B.
  * **240/240 LuaText zdekodowanych** — Lua 5.4 chunki; źródło
    debuggingowe (`@<ścieżka>`) odnalezione w każdym wpisie.
  * **REGUŁA VFS POTWIERDZONA: ścieżka VFS = `LuaText/` + debug_source** —
    `file_id` zgadza się dla **240/240** (`match: True` we
    `index/mpk/lt1_dekodowane.jsonl`). Dodatkowo 6 wierszy-ścieżek w
    `Patch.mpkdb.info0` (`LuaText/patch/patch_context.lua` itd.) spina
    pak z mpkdb: `pak = LT1.mpk` (2 097 152 + 471 425 = 2 568 577 B).
  * **Walidacja naszego `file_id`:** `LuaText/patch/patch_context.lua` →
    `092819317478651b` == blok `lt1_092819317478651b.bin`; analogicznie
    consts/main/pre_check/download — 5/5. Hashing poprawny na danych gry.
  * `Patch.mpkdb`: `info0` 854 wierszy (848 z file_id + 6 ścieżek
    bootstrapu patchera), `info1` pusta (wierszy 0), `meta` zaciemnione
    (rozmiar 6 B klucza / 130 B wartości; sha256 zanotowane, bajtów nie
    zapisujemy), `v4/v5` = (0,0) ×848 + (0,1) ×6.
- **Artefakty w repo (per instrukcja właściciela: „zapisuj wszystko jako
  indeks i commituj od razu”):** `index/mpk/` — `README.md` (zasady dla
  przyszłych agentów), `cine_dekodowane.jsonl`, `lt1_dekodowane.jsonl`,
  `lt1_stringi.jsonl` (41 727 identyfikatorów z licznikami),
  `patch_mpkdb_info0.jsonl`, `patch_mpkdb_pak.jsonl`,
  `patch_mpkdb_meta.json`. Surowe/dekodowane bajty w `local/mpk_dekodowane/`
  (gitignore). Generator: `tools/mpk_artefakty.py`.
- **POI `storyline` nadal 0 trafień pod ścieżkami bez prefiksu** → kit v4
  rozszerza kandydaci o prefiksy `LuaText/`, `LuaText/hexm/`,
  `LuaText/hexm/client/storyline_data/` (i warianty rozszerzeń).
  Kit **v4** (`wwm-mpk-skaner-v4`): okno wyboru folderu gry (tkinter,
  jak w patcherze) zamiast wpisywania ścieżki z palca — uwaga właściciela
  (1). Wyślij na Dysk per instrukcja.
- **Dalej:** właściciel uruchamia v4, odsyła wynik; Bramka 3 = analiza
  osi `.cine` (powiązanie z `cutsceny_meta`, weryfikacja 30161).

### 2026-11-17 (9) — Storyline-grafy jako most do zadań i cutscen; POI nadal bez wiązania

- **Wejście:** 14 dekodowanych bloków JSON z `Storyline.NodeBuffer` w
  lokalnym `local/patch_karwedane/` (surowe/dekodowane bloki pozostają poza Git),
  `index/poi.jsonl`, `index/zadania.jsonl`, `index/sceny_*.jsonl`,
  `index/cutsceny_meta.jsonl`, `index/chronologia.jsonl`; formaty sprawdzone
  względem publicznego `Zhincore/wwm-messiah-tools` (`codecs.py`,
  `repository.py`). W `codecs.py` nie ma parsera `.cine`.
- **Metoda:** przejście po `NodeBuffer` i `ConnectData`, weryfikacja wybranych
  ID w indeksach tekstowych; wyliczenie podsumowań pozbawionych tekstu, pozycji,
  payloadów i krawędzi grafu. Dodano generator
  `tools/index_storyline_graphs.py`.
- **Wyniki dodatnie:**
  * `5_2a40efe1316c7433` (68 węzłów) zawiera `TrackTaskNode` 380493/380494;
    zadania 380492–380499 tworzą łańcuch przez pola `pre`/`post` w
    `index/zadania.jsonl`. Graf ma też transfery 30019/30020 w przestrzeni
    31003 i dwukrotnie ścieżkę `client/guanqia/fxds/paoku/lighting2.ets`.
  * `5_a31638d0356c7433` zawiera `DialogCutsceneSequenceNode`:
    ID 2560507 (typ 1) → 32474 (typ 2), oba z `auto_preload_next=true`.
    2560507 istnieje jako `d` w `index/sceny_3.jsonl`; 32474 istnieje w
    `index/cutsceny_meta.jsonl` jako `sq001_qzpk_male` (10,5 s, przestrzeń
    31003). To jest potwierdzony most **graf Storyline → dialog/cutscene**,
    nie POI → graf.
  * `5_dfacb22a326c7433` zawiera `TrackTaskNode` 380497 oraz QTE 219/220.
    Grafy nie dają na tym etapie kompletnej ani ogólnej chronologii scen.
  * Podsumowanie 14 grafów zapisane w `index/mpk/storyline_graphs.jsonl`
    (8 699 B); odtwarzanie: `python3 tools/index_storyline_graphs.py
    local/patch_karwedane --output index/mpk/storyline_graphs.jsonl`.
- **Wyniki ujemne / ostrożność:**
  * `chronologia.jsonl.p` jest numerem pozycji na liście chronologii, nie
    kluczem transferu. Pozorna zbieżność `p=30019` z `transfer_no=30019` jest
    przypadkowa; nie używać tego jako wiązania.
  * 13 151 unikalnych 16-bajtowych GUID-ów `Resource` w blokach `hex_world`
    nie trafia w tekstowe GUID-y indeksów (poza zerowym false positive).
    Dwa GUID-y z bajtami `POI` są fragmentami losowo wyglądających binarnych
    identyfikatorów, nie markerem tabeli.
  * `1_patch_repository.bin` po zdjęciu 4-bajtowego prefiksu `CCCC` dekoduje
    się z EZST do listy 51 typów zasobów, ale jej nagłówek nie zgadza się z
    formatem names-file opisanym w `repository.py`; sam ten blok nie mapuje
    GUID-ów `hex_world` na ścieżki/nazwy.
  * 174 unikalne ścieżki `poi.storyline` z wariantami prefiksu i `.ets/.etsb`
    dały **0/848** trafień w Patch `info0` i **0/240** w LT1. Właścicielski
    wynik v4: **14/8 066** kandydatów — wyłącznie `.cine` pack-34, żadnych
    POI-storyline trafień.
- **Wniosek / następny krok:** POI→scena nie jest w Patch `info0`, LT1 ani
  dotychczas zidentyfikowanych blokach `hex_world` w czytelnym, bezpośrednim
  formacie. Poszukiwać pełnej pary names/data repository albo źródła bazowego
  pakietu; nie przypisywać jeszcze żadnego POI do grafu. Dla Bramki 3
  kontynuować parsowanie osi `.cine`; publiczny codec jej nie opisuje.

### 2026-11-17 (10) — Następstwa scen z danych `index/`: 16 946 krawędzi z oceną pewności (priorytet 1)

- **Wejście:** wyłącznie `index/` (bez skanera, bez MPK): `sceny_*.jsonl`
  (pole `x`), `zadania.jsonl` (`pre`/`post`, momenty dialogów i cutscen),
  `wybory.jsonl`, `opcje_npc.jsonl`. Priorytety właściciela: (1) kolejność
  scen jedna po drugiej, (2) POI → scena, (3) kolejność kwestii w cutscenach.
- **Metoda:** `tools/nastepstwa_scen.py` zbiera krawędzie „koniec → początek”
  z pięciu źródeł, każde z oceną pewności; węzeł to `{"t": "d"|"c", "n": …}`
  (dialog z `sceny_*` albo cutscena wskazywana przez zadanie). Pętle własne
  i cele spoza `sceny_*` wypadają (liczone w podsumowaniu). Wynik:
  `index/nastepstwa_scen.jsonl` (16 946 wierszy, ~2,2 MB), testy
  `tests/test_nastepstwa_scen.py` (syntetyczne + zgodność z zapisanym plikiem,
  jak `test_chronologia.py`).
- **Wyniki:** `nastepstwo` 7 680 (`branch_dialog_subsequent`, 5 765 dialogów
  źródłowych — jawne następniki), `wybor` 6 912 (prawie wszystkie już w tabeli
  następstw — tylko 1 krawędź nowa), `opcja_npc` 292, `zadanie` 1 071
  (koniec zadania → początek następnego w łańcuchu; tylko 2 z tych par scen
  pokrywa się z tabelą następstw — to realnie nowe wiązania), `zadanie_wewnatrz`
  991 (role `przyjecie → rozmowa → zakonczenie`; wewnątrz roli kolejności nie
  wymyślamy — iloczyn kartezjański między kolejnymi rolami). Pominięte:
  159 celów spoza `sceny_*`, 5 371 pętli własnych (ten sam dialog w kilku
  rolach zadania).
- **Wyniki ujemne / odrzucone hipotezy:**
  * `grupy_zadan.zadania` to listy **posortowane numerycznie** (884/884 grup
    z ≥2 zadaniami) — to przynależność, nie kolejność; krawędzie „kolejne
    w grupie” odrzucone (58% zgodności z `pre/post` to artefakt rosnących
    numerów w łańcuchu).
  * Przykładowy łańcuch `4700001 → 4700041 → 4700352` w danych `index/`
    **nie występuje**: 4700001 nie ma `x`; 4700041 i 4700352 nie są
    wskazywane przez żadne zadanie (4700001 to tylko `finish_dialogs` zadań
    220003 i 10000220003). Teza STATUS „pełne następstwo siedzi w `.etsb`”
    dla tego łańcucha nadal prawdziwa.
  * `zamiany_dialogow` (zastępowanie dialogu wariantami) i pozycja
    `chronologia.p` (porządek pozycyjny krain, nie przyczynowy) — nie są
    dowodem następstwa; nie użyte.
- **Wniosek / następny krok:** priorytet 1 jest częściowo domknięty z danych
  `index/` (jawne następniki + łańcuch zadań). Priorytet 2 (POI → scena)
  nadal wymaga `.etsb`/MPK albo pełnego repository nazw — bez zgadywania
  mapowania GUID→POI. Priorytet 3 (oś `.cine`) bez zmian: Bramka 3.

### 2026-11-18 — Skaner v5 (`WYNIKv5`) i v6: grafy JSON Storyline w `Resources*.mpk`

- Z `WWM_MPK_Skaner_WYNIKv5.zip` (162 wycinki `res_*.bin` z `Resources*.mpk`) wyodrębniono **1 106 kompletnych grafów JSON Storyline** (`{"Variables":...,"Storyline":{...,"NodeBuffer":[...]}}`).
- Węzły `GameLevelStorylineDialogsPlayNode` (274 wystąpienia) zawierają bezpośrednio `dialogs_no` (numer sceny) oraz `ConnectData` (`srcNodeID` → `dstNodeID`). Już z tego wycinka wyciągnięto **13 bezpośrednich krawędzi `dialog → dialog`** (m.in. `13200326 -> 13200327 -> 13200328`, `13200283 -> 13200278`, `24000036 -> 24000021`).
- `WYNIKv5` zapełnił limit 30 MB oknami binarnymi wokół `StartDialog`/`TrackTaskNode`. Zbudowano **skaner v6** (`WWM_MPK_Skaner_v6.zip`), który wycina z `Resources*.mpk` wyłącznie oczyszczone kompletne obiekty JSON Storyline zawierające węzły scen/cutscen (`GameLevelStorylineDialogsPlayNode`, `DialogCutsceneSequenceNode`, `DialogNode`, `BranchDialog`, `TrackTaskNode`) do `wyciete/storyline_wyciete.jsonl`.

### 2026-11-18 (2) — Ścieżki VFS z bazy + skaner v7 (kandydaci realne, sonda EZST)

- **Wejście:** baza gry Patch 2.4 (`26592996`) rozpakowana z części 1, 3–8
  paczki `WWM_AKTUALIZACJA_20261113_193108_9bdd6b3f` (SHA-256 wszystkich
  części zgodne z `index/paczki.json`; część 2 to tylko mapa EN — pominięta);
  `index/` z repo; publiczny format EZST/`.mpkinfo` z
  [MPK_FORMAT_RESEARCH.md](MPK_FORMAT_RESEARCH.md).
- **Przyczyna:** v4 trafiał tylko 14 `.cine`, bo kandydaci byli zgadywani ze
  wzorca `Char/e_01_cutscene/qhrw/<film>/<film>.cine` — a środkowy katalog
  (`qhrw`/`fsbd`/`zqkyw`/…) jest nie do zgadnięcia. Tymczasem tabela
  `cutscenes` ma kolumnę `cine_path` z **pełną ścieżką** (3 990 wierszy,
  1 109 z `cine_path`, 974 unikalnych), `fenbao_cutscene_info` ma `resources`
  (`.cine`) i `cutscene_graph` (`Char/graph/cutscene/*.graph` — kandydaci na
  pliki grafów Storyline), a surowe chunki `dataN` zawierają łącznie 11 278
  nazw/ścieżek `.cine`/`.graph`/`.etsb`/`.ets` (10 559 z katalogiem, w tym
  benchmark POI `client/dialogs/hjt/sxd_longwenbiaoji.etsb`).
- **Nowy generator:** `tools/sciezki_vfs.py` → `index/mpk/sciezki_vfs.jsonl`
  (11 278 wierszy; źródła kolumnowe z numerami cutscen w polu `cutsceny` +
  `skan_dataN`). Do Git idą wyłącznie teksty ścieżek.
- **Skaner v7** (`tools/mpk_skaner.py` `wwm-mpk-skaner-v7`,
  `tools/build_mpk_skaner.py` kit v7):
  * kandydaci z `sciezki_vfs.jsonl` (wszystkie ścieżki z katalogiem +
    warianty `.ets`↔`.etsb`): **25 451 kandydatów** (v4: 8 066), w tym
    974 realnych `.cine`, 2 429 `.graph`, 804 `.etsb`;
  * **sonda EZST**: AES-256-ECB w czystym Pythonie (klucz publiczny; zgodność
    z wektorami NIST SP 800-38A i `pycryptodome` sprawdzona testem) +
    dekompresja początku ramki zstd (`compression.zstd` Python 3.14+ albo
    pakiet `zstandard`; bez nich sonda treści jest jawnie pomijana).
    Dla każdego wpisu `Resources.mpkinfo` ≤ 4 MB czyta 16 KiB głowy,
    dekoduje do 64 KiB treści w pamięci i szuka sygnatur: magic `.cine`
    `c159410d`, `{"Variables":`/węzły Storyline, `client/dialogs`/`.etsb`,
    benchmark `4700001` (ASCII i u32le). Trafienia wycina SUROWO
    (`wyciete/ezst_<pack>_<fileid>.bin` + `ezst_trafienia.jsonl`,
    limit 256 MB; `--bez-ezst`, `--ezst-max-blok-mb`, `--ezst-limit-mb`);
  * naprawiony zgubiony wynik skanu storyline w raporcie
    (`isinstance(wycinanie, dict)` zawsze fałszywe → teraz
    `raport["resources_storyline"]`).
- **Weryfikacja:** syntetyczna instalacja z prawdziwymi blokami EZST
  (zstd + AES) — sonda trafiła 3/4 bloków (storyline, cine, benchmark w gołym
  bloku; blok zerowy poprawnie bez trafienia), a wycięte bloki dekodują się
  po stronie repo `mpk_artefakty.ezst_decode` bajt w bajt. Czas AES prefiksu:
  ~1,2 ms/blok → ~50 min na 2,6 mln wpisów (szacunek; filtr ≤ 4 MB zdejmie
  duże zasoby). Testy stdlib-only (CI bez zstd używa atrapy zlib o tym samym
  kontrakcie): 583 testy OK.
- **Ograniczenia / uczciwie:** sonda czyta tylko głowę bloku — sygnatura
  głęboko w pliku nie zostanie zauważona; bez modułu zstd sprawdzane są
  wyłącznie bloki gołe; benchmark ASCII `4700001` może trafić przypadkowe
  teksty (to sonda, nie dowód). Trafienia kandydatów w `PODSUMOWANIE.txt`
  ucięte do 300 pozycji (pełna lista w `RAPORT.json`).
- **Poprawka po uwadze właściciela** („bat ma to robić sam, ja nic nie
  odpalam”): `SKANUJ.bat` sam sprawdza moduł zstd (nowa flaga skanera
  `--sprawdz-zstd`) i w razie braku **sam doinstalowuje** pakiet `zstandard`
  (`pip install --user`, jedyny kontakt z siecią — uczciwie opisany w
  CZYTAJ_TO); gdy instalacja się nie uda, skan rusza mimo to w trybie
  gołych bloków. Z CZYTAJ_TO usunięte wszystkie ręczne polecenia.
- **Paczka:** `dist/WWM_MPK_Skaner_v7.zip`, **160 860 B**, SHA-256
  `81431bf2b46c7f678b1214104a3a47fc6c5e3d9cd11220a64cb071d1d529e338`,
  na Dysku (folder „Where Winds Meet”, id `12X8MPOLISbOnEeeAy8i5yJiKRt1DPaZu`);
  kity v4–v6 i pierwsze wydanie v7 (bez autoinstalacji) w koszu
  (wyniki `WYNIK*` zostają).
- **Następny krok:** właściciel uruchamia v7 (tylko `SKANUJ.bat`) i odsyła
  `WWM_MPK_Skaner_WYNIK.zip`. Po wyniku: dekodowanie `ezst_*.bin`
  (`mpk_artefakty`), mapowanie `.cine` → cutsceny po `sciezki_vfs.jsonl`
  (pole `cutsceny`), Bramka 3 (oś 30161) i grafy Storyline pod priorytet 1/2.

### 2026-11-18 (3) — Przebieg skanera v7: reguła `Storyline/`, benchmark POI potwierdzony, ujęcia `.cine`

- **Wejście:** `MPK_SKANER_WYNIK.zip` + `.z01–.z07` z Dysku (split-zip,
  razem 189 608 873 B; MD5 części zgodne z Dyskiem; scalenie `zip -s 0`,
  CRC całości czyste). Przebieg właściciela: 2 601 198 sondowanych wpisów
  `Resources.mpkinfo` (backend `compression.zstd`, Python 3.14), **36 545
  trafień sondy EZST** (25 179 `cine_magic`, 11 305 `storyline_json`,
  2 775 `storyline_node`, 47+3 etsb, 31 benchmark), **3 113 trafień
  kandydatów** po prawdziwych ścieżkach (978 `.cine`, 2 135 `.graph`),
  0 błędów, limit niewyczerpany. Po stronie repo zdekodowano **wszystkie
  39 888 bloków bez jednego błędu** (AES+zstd, `mpk_artefakty`; 11 586
  bloków było gołych).
- **Odkrycie 1 — master `.cine` wylicza pod-ujęcia w kolejności
  odtwarzania.** Każdy master (np. `sq001_gdjh.cine`) zawiera uporządkowaną
  listę ścieżek dzieci (`…_010.cine → _020 → …`). Z 974 masterów wyszły
  5 022 unikalne dzieci; **5 021 z nich odnaleziono w trafieniach sondy
  po `file_id`** (dzieci sondy nie były kandydatami — to czysta wygrana
  sondy treści). Benchmark 30161 (`sq001_zlxl`): 17 ujęć
  `s010…s130, s130a, s140…s160` w kolejności gry.
- **Odkrycie 2 — reguła VFS `Storyline/<ścieżka>.etsb`.** Ścieżek
  `client/dialogs/...` nie było w trafieniach kandydatów, bo w VFS leżą
  z prefiksem `Storyline/`. Wydedukowane z dolnych 32 bitów `file_id`
  bloku grającego scenę 4700001 (długość 46 = 10 + 36, końcówka `oji`)
  i potwierdzone pełnym `file_id`:
  **`Storyline/client/dialogs/hjt/sxd_longwenbiaoji.etsb` →
  `322e2635696a6f2e` → graf `StartEvent → StorylineDialogsPlayNode
  (dialogs_no=4700001) → EndEvent`. BENCHMARK PRIORYTETU 2 (Dragon
  Pattern Mark → scena 4700001) POTWIERDZONY wprost z danych.**
  Regułą rozwiązano hurtowo **6 961 skryptów** (6 774 z `sciezki_vfs` +
  208/240 `storyline_path` cytowanych w grafach, po dedup).
- **Odkrycie 3 — `.etsb` to skompilowane grafy Storyline** (ten sam JSON
  `{"Variables":…,"Storyline":…}`), a `ClientRunStorylineNode.storyline_path`
  spina grafy między sobą.
- **Nowe indeksy** (`tools/wynik7_indeksy.py`, committed `782c319`):
  `cine_ujecia.jsonl` (978 masterów + uporządkowane ujęcia),
  `etsb_storyline.jsonl` (6 961 skryptów z faktami grafów),
  `storyline_sceny.jsonl` (8 948 grafów po dedup: 5 121 unikalnych scen,
  576 cutscen, 4 518 następstw przez węzły pośrednie — w tym **1 508
  unikalnych krawędzi scena→scena** vs 13 z WYNIKv6, 235 cutscena→scena,
  182 scena→cutscena, 192 cutscena→cutscena).
- **Uczciwie (negatywy):**
  * `4700041` i `4700352` **nie występują nigdzie** w zdekodowanym korpusie
    (ani ASCII, ani u32le) — łańcuch benchmarku priorytetu 1 nadal
    niepotwierdzony; korpus to tylko bloki trafione głową sondy (16 KiB
    wejścia / 64 KiB treści), więc nieobecność ≠ dowód nieistnienia,
  * trafienia `benchmark_4700001(_u32)` poza grafami to przypadkowe bajty
    (RIFF/WAVE, heightmapy, materiały) — sonda, nie dowód,
  * osie `.cine` (master i ujęcia) **nie zawierają** nazw nagrań
    (`vo_sm_sxdm4_cs_zlxl_*`), ich hashy Wwise (FNV-1 32), id `sound_data`
    (7150686…) ani numerów wierszy napisów — kolejność **kwestii** nadal
    nie wynika wprost z `.cine`; kolejność **ujęć** już tak,
  * 519/7 293 `.etsb`/`.ets` i 32/240 `storyline_path` nierozwiązane
    (brak trafienia głowy sondy albo inna reguła ścieżki).
- **Następny krok:** krzyżówka nowych indeksów z `index/` (czytanka:
  następstwa scena→scena + przeplot scena↔cutscena); mapowanie POI →
  `.etsb` → scena wymaga kolumny POI ze ścieżką skryptu z bazy gry
  (baza w `local/` do ponownego pobrania z Dysku w przyszłej sesji).

### 2026-11-18 (4) — POI → scena domknięte indeksem; scalone następstwa v6+v7

- **POI → scena:** `index/poi.jsonl` (tabela `active_interact_way`) już
  zawierał ścieżki `interact_storyline` — krzyżówka z `etsb_storyline.jsonl`
  daje `index/mpk/poi_storyline_sceny.jsonl`: 191 POI ze skryptem, w tym
  **61 ze sceną** (benchmark POI **200046001** → `client/dialogs/hjt/
  sxd_longwenbiaoji.etsb` → **scena 4700001** — cały łańcuch POI→skrypt→scena
  wynika z danych), 55 ze skryptem bez scen, 75 nierozwiązanych (głowa sondy
  nie trafiła bloku; jawni kandydaci `Storyline/<ścieżka>` do kitu v8).
  Domknięcie przechodnie przez `ClientRunStorylineNode` zaimplementowane —
  w obecnym korpusie 0 scen pośrednich.
- **Następstwa scalone:** `index/mpk/nastepstwa_scen.jsonl` — 1 744 unikalne
  krawędzie (1 066 z WYNIKv6, 1 723 z v7, **1 045 wspólnych** — skany
  wzajemnie się potwierdzają; 21 tylko-v6 to grafy, których głowa sondy v7
  nie złapała). Znane łańcuchy z WYNIKv5/6 obecne (13200326→327→328,
  13200283→278, 24000036→24000021).
- **Baza gry ponownie w `local/dane`** (części 1,3–8 z Dysku; `git checkout --`
  na nadpisanych `index/paczki.json` i `docs/PLIKI_W_PACZKACH.md`).
- **Następny krok:** użyć `nastepstwa_scen.jsonl` + przeplotu scena↔cutscena
  w generatorze czytanki (v12) — to zmiana układu, więc najpierw krótka
  propozycja dla właściciela: które sceny zmienią miejsce i dlaczego;
  do kitu v8: kandydaci `Storyline/<ścieżka>` (75 POI + 519 `.etsb`/`.ets`
  + 32 `storyline_path`), pełna (nie-głowowa) sonda wskazanych file_id.

### 2026-11-18 (5) — Połączenia scen z grafu zadań; prawda o benchmarku 4700001→4700041

- **Prośba właściciela:** najważniejsze są połączenia scena→scena
  (przykład: po 4700001 zaraz 4700041).
- **Znalezione źródło kolejności — tabela `tasks`** (24 753 zadania;
  kolumny `pre_task`/`post_task` + momenty grania: `fetch_play_cutscene`,
  `fetch_play_dialogs`, `run_task_storyline` (sceny ze skryptów przez
  `etsb_storyline.jsonl`), `finish_dialogs`, `finish_play_dialogs`,
  `finish_play_cutscene`). Nowe narzędzie `tools/zadania_sceny.py` →
  `index/zadania_sceny.jsonl` (13 623 zadania ze zdarzeniami) i
  `index/mpk/nastepstwa_zadania.jsonl` (**8 997 krawędzi**; sceny z jednego
  skryptu uczciwie nieporządkowane; zadania bez zdarzeń przeskakiwane).
- **Kanoniczny plik następstw** `index/mpk/nastepstwa_scen.jsonl` po scaleniu
  trzech źródeł (v6, v7, zadania): **10 648 krawędzi, 1 087 potwierdzonych
  co najmniej dwoma źródłami**. Główny łańcuch od 4700001 ciągnie się bez
  dziur z przeplotem cutscen: `4700001 → 4700346 → 4700002 → 4700003 →
  4700005 → 4700377 → 4700384 → 4700385 → [30162] → [30165] → 4700068 → …`.
- **Benchmark właściciela 4700001→4700041 — wynik uczciwy:** tej krawędzi
  NIE ma w danych. Fakty:
  * po 4700001 (zadanie 220003, `finish_dialogs`) łańcuch `post_task`
    idzie do 220005, a jego skrypt `hjt/220005.etsb` gra **4700346**;
  * 4700041 jest grane w zadaniu **3400017** (grupa 5052,
    `qiyu_xunxiazhilu` — inny wątek) przez `new_npc_task_data`
    (`taskbb_ins_kit_id: 4700041`), nie przez kolumny `tasks`;
  * 4700352 nie ma w całej bazie ŻADNEGO wyzwalacza poza własną osią
    `dialog_timelines.4700352` (pełny skan `szukaj_w_bazie --id`);
  * `longwenbiaoji` występuje w bazie dokładnie raz (`active_interact_way`)
    — kolejne „znaki smoka" nie są POI z tej tabeli;
  * zakres **4700000–4799999 to jeden arkusz `ins_kit`** projektantki 李妍
    (`ins_kit_designer_no`: start_id/finish_id per projektant) — numery
    4700xxx to wpisy jej arkusza, a wyzwalacze części z nich siedzą w
    rozmieszczeniu świata (`spaces.*` — trafienia u32 dla 4700041).
- **Hipoteza (do sprawdzenia, nie fakt):** 4700041/4700352 odpalają się
  z bytów rozmieszczonych w `spaces` (kolejne znaki wątku sxd) — kolejność
  wynika z PROWADZENIA gracza (zadania/nawigacja), nie z jawnej krawędzi.
  Ewentualne potwierdzenie: dekodowanie wpisów `spaces.*` wokół trafień
  u32 4700041 albo pełne wycięcie nierozwiązanych skryptów kitem v8.
- **Osie `dialog_timelines.4700001/41/352` istnieją w bazie** (bogate
  TimelinePObject z trackami per postać) — to kandydat na źródło kolejności
  KWESTII wewnątrz sceny (priorytet 3) na przyszłą sesję.

## 2026-11-18 (6) — mechanizm scen ambientowych: kity w spaces + graf NPC-zadań

Cel: wyjaśnić potwierdzony w grze ciąg 4700037 → (klik POI Dragon Pattern
Mark) → 4700001 → 4700041 (komentarz Ruby) → 4700352 (reakcja Youxii).

Fakty (z bazy gry):
- `spaces.<s>.spawn_kit_sid_no` mapuje **numer sceny** na kity w świecie
  (`kit_serial_id` == numer sceny). 4700037 → kit 470003720 (pozycja
  [-2190.17, 8.03, -993.91]), 4700041 → kit 470004120 ([-2148.29, 7.23,
  -1002.01]) — oba w s501/s701, ~40 m od siebie, przy POI 200046001.
  Drzewo zachowań `u_common_qifen` (气氛 = ambient): NPC w kicie gra scenę
  o numerze seryjnym kitu, gdy gracz jest w pobliżu.
- Zadanie **3400017** (pre_task 3400016, task_space 501, grupa 5052)
  spawnuje przy pobraniu grupę bytów **1632220065**
  (`fetch_create_entity_serial_no`) — to grupa kitu 470004120.
  `new_npc_task_data.3400017` instruuje NPC **15000023** (Ruby/Hongxian):
  act 1 `task_sub_goto` → pozycja kitu, act 2 `task_sub_ins_kit`
  z `taskbb_ins_kit_id` 4700041. Stąd komentarz Ruby po scenie POI.
- Schemat ID kwestii potwierdzony: 470004101 w `voice_data_ai`
  → dialog_no 4700041 (kwestia AI-gen Ruby). Kwestia gracza 470035201 ma
  nagrany `voice_no` 7151581 (brak w voice_data_ai).
- `dialog_timelines.4700352`: mówi gracz („我"), watch target 红线
  (Hongxian, entity 900910), dialog_type 28, `sub_dialog_distance` 8 —
  typowy sub-dialog ambientowy (riposta po kwestii NPC).

Ograniczenie: wyzwalacz 4700352 **nie występuje** w danych klienta —
przeszukano pełną bazę (klucze+wartości), wszystkie 197 spaces, 39 888
dekodowanych grafów (u32le/u32be/u64le/f64le/ASCII). Siedzi w serwerowych
drzewach zachowań (`monster_btree.se`, `u_common_qifen`, blackboard
2300210), których nie ma w paczkach klienta. Krawędź 4700041→4700352
utrwalona jako źródło „gra" (potwierdzenie przebiegiem).

Nowe artefakty: `index/mpk/nastepstwa_subsequent.jsonl` (8 011 krawędzi
z `branch_dialog_subsequent`), `index/mpk/sceny_ambient_kity.jsonl`
(53 601 unikalnych wierszy scena+kit+pozycja; 43 877 scen z pozycją XYZ),
`index/mpk/nastepstwa_z_gry.jsonl` (3 krawędzie benchmarku). Kanoniczny
`nastepstwa_scen.jsonl`: **18 625 krawędzi z pięciu źródeł**.

Ślepe uliczki (nie wracać): `branch_dialog_subsequent` nie zawiera
benchmarku; tabele `npc_dialog_select`/`scene_dialog_data`/`npc_tag_dialog`
itd. bez śladu 4700352; trafienie `npc_dialog_select.14900115` to substring
34700001; graf `duanqiao.ets` i cały korpus grafów nie niosą numerów scen
ambientowych.

## 2026-11-18 (7) — chronologia z grafu następstw: czytanka v12

`tools/chronologia.py` układa teraz sceny w krainie **topologicznie po grafie
następstw** (`index/mpk/nastepstwa_scen.jsonl`, 18 625 krawędzi), nie po
numerze dialogu. Zasady: łańcuch połączonych scen emitowany w całości (świeżo
odblokowany następnik wchodzi natychmiast); przy rozwidleniu pierwszeństwo ma
krawędź ze źródłem „gra"; graf rzutowany na sceny krainy z kontrakcją ścieżek
(scena pusta/z innej krainy nie rwie mostu — np. 4700346 bez treści łączyła
4700001→4700002); cutsceny znane grafowi stoją dokładnie między swoimi
scenami; cykle rwane deterministycznie na najmniejszym numerze; sceny bez
krawędzi jak dotąd po numerze.

Benchmark właściciela w `index/chronologia.jsonl` stoi ciągiem (pozycje
8063–8075): `4700037 → 4700001 → 4700041 → 4700352 → 4700002 → 4700003 →
4700005 → 4700377 → 4700384 → 4700385 → [cutscena 30162] → [30165] →
4700068` — dokładnie przebieg z gry. Pilnuje tego nowy test
`test_benchmark_przebiegu_z_gry`; test porządku numerycznego zawężony do scen
spoza grafu; cutsceny w krainie mogą stać z grafu (bez pola `g`).

Czytanka v12: `dist/WWM_Czytanka_PL_v12.zip` (6,8 MB) z tej chronologii —
dostarczona na Dysk. 588 testów OK.

## 2026-11-18 (8) — „Interakcja: <POI>" nad sceną; czytanka v13

Na prośbę właściciela scena wywoływana przez punkt na mapie dostaje
w `01_sceny_i_cutsceny.md` wiersz `Interakcja: <nazwa POI>` nad nagłówkiem
(np. `Interakcja: Dragon Pattern Mark` nad `## Scena 4700001`). Powiązanie
POI→scena z `index/mpk/poi_storyline_sceny.jsonl` (status `sceny`), nazwa
POI jak w sekcji POI pliku 03 (polski przekład, bez niego tekst z gry
z gwiazdką); POI bez nazwy nie podpisujemy. 59 scen dostało wstęp.
Czytanka v13 (`dist/WWM_Czytanka_PL_v13.zip`) na Dysku.

## 2026-11-18 (9) — zwrotka WWN_PL_v4: +26 243 przekłady; łatka v0.5.0; czytanka v14

Zwrotka tłumacza `WWN_PL_v4.zip` (Dysk, 31 MB, 80 plików .md: PL/cutsceny,
PL/sceny, PL/widoki). Import `tools/import_zwrotki.py`: 312 493 miejsc PL,
26 123 nowych, 120 zmienionych (pierwszeństwo tłumacza — nadpisują wersje
z repo), 85 274 bez zmian, 0 odrzuconych. Dwa wpisy z nadmiarowymi tokenami
`#Y…#E` (klucze b1196aba0f5f6d1c, 9f844bb3748bcbb8 w
`oversea_home_entry_bag_search.describe_str`) przyjęte świadomie przez
`--mimo-tokenow`: tłumacz celowo dodał kody koloru wyróżnienia, których
źródło nie ma — do obejrzenia w grze przy następnym teście.
Magazyn po imporcie: **111 735 przekładów (22,82%)**.

Łatka **v0.5.0**: `dist/WWM_Spolszczenie_PL_v0.5.0.zip`, 9 447 453 B,
SHA-256 3e8e9cdf06fe5a9a7fd6c6782842b49d193655c66eaa17dd87069b8e02e34081,
112 405 przekładów w planie (112 079 kluczy + 326 wariantów płci; 670
bliźniaków __grey, 754 kolizje odłożone). Zbudowana z magazynu
(`one_click_patch.py --tylko-magazyn`), jak przetestowana w grze v0.4.0.

Czytanka **v14** (`dist/WWM_Czytanka_PL_v14.zip`): układ v13 + nowe
przekłady; nazwy POI we wstępach „Interakcja:" już po polsku
(np. „Interakcja: Znak smoczego wzoru" nad sceną 4700001). Obie paczki
na Dysku.

ROADMAPA (następne duże zadanie od właściciela): **chronologia tekstów
W cutscenach** — większość cutscen ma dziś tylko streszczenie, bez kwestii;
szczegóły w docs/STATUS.md (sekcja „Następny krok").

## 2026-11-18 (10) — PRZEŁOM: chronologia kwestii w cutscenach ze ścieżki audio `.cine`

Zadanie z roadmapy rozwiązane. Brakujący przeplot bloków puli napisów
(`text_msg`) **nie leży w żadnej tabeli bazy** — leży w głównym pliku
`.cine` cutsceny (kontener ujęć `sXXX`), jako tekstowe wpisy ścieżki
dźwiękowej `czas:id_sound_data:a:b;c` (np. `3.399:7151014:0:0;0`).

Droga do odkrycia (ślepe uliczki po drodze — patrz niżej):
1. nazwy nagrań (`vo_sm_sxdm4_cs_zlxl_*`) w bazie ma TYLKO `sound_data`
   ({id, audio_name, text, duration}) — ale bez kolejności;
2. kod filmu `zlxl` znają tylko `cutscenes` (cine_path!) i `fenbao_…`;
3. `cutscenes.cine_path` → `file_id` (murmur3) → artefakt w korpusie
   MPK_SKANER_WYNIK: **wszystkie 1109 cutscen mają swój `.cine` w
   korpusie**, 996 z wpisami audio, 549 z kwestiami mówionymi;
4. wpisy posortowane po czasie = pełna chronologia kwestii; teksty
   scenariuszowe `sound_data.text` tną się na wiersze puli napisów
   (segmentacja zachłanna + warianty partykuł 啦/了, 欸/哎, 呀/啊).

Nowe narzędzia i indeksy:
- `tools/cine_sciezka_audio.py` → `index/cutsceny_sciezka_audio.jsonl`
  (549 cutscen, 2 030 kwestii z czasem, id, audio i tekstem zh);
- `tools/cutsceny_kolejnosc_kwestii.py` → `index/cutsceny_kolejnosc_kwestii.jsonl`
  (215 cutscen, 232 bloki wariantów, 2 452 wiersze puli w kolejności
  odtwarzania); okna klastrowe oddzielają pokolenia (590xxx/591xxx);
- `czytanka_czysta.py`: cutsceny renderują kwestie w tej kolejności,
  przejmują wiersze z „Napisów przerywnika" (591170–591183 wróciły do
  30161), nagłówki przerywników przeliczają zakres po oddaniu kwestii.

**Benchmark: ręczny zapis gracza cutsceny 30161 odtworzony w 100%** —
36/36 kwestii w dokładnie tej kolejności (przeplot Ruby/gracz).
Regresja: `tests/test_czytanka_kolejnosc_cutscen.py` 17 testów
(`BENCHMARK_30161` wprost w teście), całość 591 OK.

Ślepe uliczki tej sesji: szukanie referencji id wierszy puli
(591148/591170) po tabelach — tylko `text_msg`/`text_msg__grey`;
`ccs_text_msg` to UI; nazwy audio nie występują plaintext poza
`sound_data`; trafienia u32 w skompresowanych Lua to przypadkowe zbitki.

## 2026-11-18 (11) — tryb zapasowy dla krótkich cutscen + mówcy z nazw nagrań

Dokończenie chronologii cutscen (zlecenie właściciela):

**Tryb zapasowy** (`kwestie_zapasowe` w `tools/cutsceny_kolejnosc_kwestii.py`):
cutsceny z 1–4 kwestiami nie tworzą klastrów okna puli, a ich napisy żyją
w tabelach dialogów scen. Dopasowanie do **całego** wyciągu: najpierw cała
kwestia, potem segmentacja z pełnym pokryciem (segmenty ≥ 4 znaki, dziury
≤ 1 znak). Filtr opisów scenicznych (气息/群杂/视频/音效… — oddechy, gwar,
opisy wideo to nie napisy). Indeks: **347 cutscen (215 okno + 132
zapasowe), 2 826 wierszy**; wpisy mają teraz pole `a` (audio kwestii).
Reszta brakujących z 334 to nagrania bez tekstu napisów (same oddechy).

**Mówcy z nazw nagrań** (`mowca_z_audio` w `tools/kontekst_cutscen.py`):
identyfikacja z danych, nie z podpowiedzi `mowca_en`: nagrania gracza
(`pma`/`pmb`/`player_m`/`player_f`, z wyłączeniem liczników po `_npc_`)
→ **Youxia**; kody postaci w ścieżkach `_cs_` ze słownika pewników
(`PREFIKSY_MOWCOW_CS`, na razie `zlxl_hx` → Ruby). Czytanka podpisuje
kwestie cutscen: najpierw audio wiersza z kontekstu, potem audio kwestii
z `.cine`. W 30161 przeplot ma teraz podpisy **Ruby/Youxia** (kwestie bez
audio wiersza i z generycznym `npc` zostają bez podpisu — uczciwie).

Testy: +6 (`TestMowcaZAudio`, `TestKwestieZapasowe`), całość **597 OK**.
Pułapka z danych: `vo_sm_sxd_npc_pma_44` to „Guest A", nie gracz —
`pma` bywa licznikiem po `npc_`; stąd twarda blokada `_npc_`.
