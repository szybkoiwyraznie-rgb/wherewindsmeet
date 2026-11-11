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
