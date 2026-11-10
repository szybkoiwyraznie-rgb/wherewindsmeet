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
