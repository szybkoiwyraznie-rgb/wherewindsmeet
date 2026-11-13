# Stan projektu

Aktualizacja: **2026-11-13**. Punkt wejścia dla kolejnej sesji. Cel i kryteria
akceptacji: [CEL.md](CEL.md). Historia prób: [dziennik](EXPERIMENT_LOG.md).

## Gdzie jesteśmy

**Wyciąg `index/` w repozytorium jest już zaktualizowany do Patcha 2.4
(`build 26592996`, dane z `2026-11-13`), do `tlumaczenie/` zaimportowano pierwszą
zwrotkę tłumacza (`WWM_PL1.zip`: `75 685` przekładów = `15,46%` gry), a na Dysk
Google wysłano zregenerowany pakiet `v4`** (`paczka_dla_tlumacza_wwm_v4.zip`,
`422 248` miejsc `PL:`, w tym `75 683` przeniesionych jako aktywne `PL: tekst`,
`346 565` pustych `PL:` — albo `253 693` po pominięciu tabel UI/meta — oraz
dodatkowe listy `rewizje_en.jsonl` [`899` pozycji] i `usuniete_klucze.jsonl`
[`566` pozycji]). Cały obieg — wyciąg z plików gry, pakiet (także `--wypelnij-pl`
i `--dodatek`), Czytanki `v2`, import zwrotki, łatka map tekstów (także
standalone `patcher_wwm.py`), audyt aktualizacji i pakiet uzupełniający —
działa i jest przetestowany na prawdziwych plikach Patcha 2.4 **w piaskownicy**.
Opis i polecenia: [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md).

Przygotowano również **tryb cotygodniowej aktualizacji w zbieraczu `1.3.0`**
(`collector/URUCHOM_AKTUALIZACJE.bat` + dzielenie dużych paczek w `spakuj_dane.ps1`
— przetestowane na 8-częściowej paczce 516 MB z Patcha 2.4), **bezpieczny
instalator Windows z kopią zapasową i przywracaniem** (`patcher_wwm.py` w trybie
standalone oraz `instalator/` w trybie binarnym) oraz **plan małej próby UI
i polskich znaków** ([TEST_W_GRZE.md](TEST_W_GRZE.md), `tools/latka_testowa.py`).

**W grze zweryfikowano dotąd pierwszy mały test na poprzednim buildzie `25906190`
(`tools/latka_testowa.py` w trybie binarnym):** klient Steam (Windows) przyjął
przepisane mapy `translate_words_map_en*` w menu głównym, ustawieniach oraz
napisach otwierającego prologu, a czcionki gry wyświetliły poprawnie wszystkie
polskie znaki diakrytyczne (`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`).
**Nie sprawdzono jeszcze w oknie gry:** zachowania klienta na nowym Patchu 2.4
(`26592996`), nowego samowystarczalnego wrappera `patcher_wwm.py` uruchomionego
bezpośrednio na komputerze z grą (na kopii plików `26592996` w piaskownicy
przeszedł pełny cykl `instaluj → stan → przywroc` z dokładnym odtworzeniem
SHA-256) oraz rozbudowanej łatki z zaimportowanej zwrotki `WWM_PL1.zip`
(`75 685` przekładów w `tlumaczenie/`).

## Co wiadomo

- **Baza gry odczytana w całości** ([BAZA_GRY.md](BAZA_GRY.md)): `MANIFEST` →
  `indexN` → `dataN`, z warstwą aktualizacji (`index1001`/`1200`). W Patchu 2.4
  (`26592996`) `114 904` z `114 925` tabel czyta się bez błędu (0 nieznanych
  tagów), a `21` pustych tabel `spaces.*` (`0x00`, bez tekstów) zapisuje się w
  `manifest.json`. Narzędzie: `tools/baza_gry.py`.
- **Mapy tekstów z warstwami `_diff`** ([LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)):
  `LocalData/Patch/HD/oversea/locale/*_diff` liczy się od zera względem
  bazy `Package/` i **zastępuje** starszą warstwę `Package/.../_diff` tego
  samego języka (`wybierz_warstwy_gry` w `tools/mapa_tekstow.py`; w Patchu 2.4
  ujawniły się 34 starsze klucze z `Package/_diff`, które patch wycofał).
  Patcher nadpisuje na dysku oba pliki docelowe niezależnie.
- **Wyciąg `index/` (`wwm-indeks-v2`, Patch 2.4 `26592996`)** w repozytorium:
  487 684 unikalnych tekstów (chiński + angielski), 75 007 dialogów ze 186 288
  kwestiami — każda w grupie mówcy — 24 753 zadania, wybory, postacie z opisami,
  encyklopedia, miejsca. 93,58% identyfikatorów mapy angielskiej ma wskazane
  źródło (tabelę albo scenę).
- **Poprzedni indeks (`wwm-indeks-v1`) był błędny** i został usunięty 2026-11-12:
  stary parser przypisywał scenie numer i projekt sceny następnej („5 859
  brakujących dialogów” było artefaktem).
- **Pakiety `v1`/`v3`/`v4` i magazyn `tlumaczenie/`**: wysłany `v1` miał
  `485 047` miejsc `PL:`, wysłany `v3` (`--tylko-z-en`, build `25906190`)
  `418 773` miejsc `PL:`. Z pierwszej zwrotki (`WWM_PL1.zip`) zaimportowano
  **`75 685` przekładów** (`82` warianty płci + `75 603` po kluczu = `15,46%`
  tekstów gry) do `tlumaczenie/`. Po aktualizacji `index/` do Patcha 2.4
  wysłano zregenerowany pełny pakiet **`v4`** (`--wypelnij-pl`): `422 248` miejsc
  `PL:` (`75 683` przeniesionych jako aktywne `PL: tekst`, `346 565` pustych
  `PL:` lub **`253 693` po odjęciu tabel UI/meta**), uzupełniony o
  `rewizje_en.jsonl` (`899`) i `usuniete_klucze.jsonl` (`566`). Pakiet
  uzupełniający różnicy `25906190 → 26592996` ma `4 010` miejsc `PL:` (`677`
  bez UI/meta). Każdy tekst ma dokładnie jedno `PL:`.
- **Kolejność scen** pochodzi z danych (dla `index/` Patcha 2.4 w pełnym `v4`):
  34 491 scen uporządkowanych w zadaniach (w tym 25 434 „według numeracji” za
  taką sceną — oznaczone w nagłówku jako kolejność z numeracji, nie powiązanie),
  12 341 według projektu i 26 562 rozmów tła według miejsca.
- **Płeć bohatera**: 1 860 kwestii ma osobne identyfikatory dla bohatera
  i bohaterki; w pakiecie mają osobne `PL:`.
- **Aktualizacja przyrostowa sprawdzona na danych**: najpierw między paczką
  gry a jej `LocalData/Patch` w `25906190` (`387` nowych tekstów), a następnie
  między `25906190` i Patch 2.4 `26592996` (`+4 171` nowych tekstów z EN,
  `-566` usuniętych, `57` nowych scen, `4 010` miejsc `PL:` w pakiecie
  uzupełniającym).
- Decyzje właściciela: język źródłowy chiński, angielski pomocniczo;
  **zakres tłumaczenia wyznacza obecność wersji angielskiej (`EN`)** — wpisy
  wyłącznie chińskie czekają do momentu wydania w wersji globalnej jako
  „patch tłumaczenia” (`--tylko-z-en` w `buduj_paczke.py` i
  `audyt_aktualizacji.py`); własny przekład, bez cudzych polonizacji; tylko
  zmiany tekstu przy wyłączonej grze, bez wstrzykiwania i obchodzenia
  zabezpieczeń; teksty i indeksy w Git, poza Git tylko binarne pliki gry
  ([DATA_POLICY.md](DATA_POLICY.md)). Instalacja odniesienia: Steam, Windows,
  App ID `3564740`, bieżący wyciąg z buildu `26592996` (poprzednio `25906190`,
  [STEAM_REFERENCE.md](STEAM_REFERENCE.md)).
  Warunków wydawcy nie potwierdziliśmy niezależnie; nie obiecujemy bezpieczeństwa
  konta.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | Ponad 352 testy (Linux + Windows CI); `check_repository.py` i `git diff --check` czyste; CI na Ubuntu i Windows × Python 3.11/3.12. |
| Odczyt plików gry | Baza tabel, dialogi, mapy tekstów z warstwami (z obsługą zastępowania `Package/.../_diff` przez `LocalData/Patch/.../_diff`) — sprawdzone na Patchu 2.4 (`26592996`). |
| Wyciąg i powiązania | `index/` w Git (`wwm-indeks-v2`, Patch 2.4 `26592996`), deterministyczny, ze stałym podziałem plików. |
| Pakiet tłumacza i Czytanki | Pakiety (`--tylko-z-en`, w tym paczki uzupełniające `--tylko-sloty`) i trzyplikowe Czytanki `wwm-czytanki-v2` (`epizody.md`, `kontekst_scen.md`, `dodatkowe.md` pod limitem `<5 MB/część`, 100% pokrycia) budują się **100% standalone z `index/`** (zero binarek gry). |
| Import zwrotki | Gotowy i zweryfikowany produkcyjnie na `WWM_PL1.zip` (`tools/import_zwrotki.py`: `75 685` zaimportowanych przekładów w `tlumaczenie/`, `0` błędów formatu/tokenów, `21` kluczy odrzuconych z powodu usunięcia w Patchu 2.4). |
| Łatka i instalator Windows | **Domyślnie standalone (`tools/one_click_patch.py`, `tools/latka_testowa.py` → `tools/build_standalone_patcher.py` + `tools/patcher_wwm.py`):** buduje `WWM_LATKA_PL.zip` wyłącznie z `index/` i `tlumaczenie/` (czysty `plan_latki.json` + lokalny patcher z kopią oryginałów, zero binarek gry). Opcjonalny tryb binarny (`instalator/`) zachowany dla jawnych flag `--dane-gry`/`--mapa`. Mała łatka testowa (`latka_testowa.py` na `25906190`) **zweryfikowana w uruchomionej grze Steam**; pełna łatka fabularna i test `patcher_wwm.py` na Patchu 2.4 (`26592996`) w realnym oknie gry czekają na sprawdzenie. |
| Aktualizacje gry | `collector/URUCHOM_AKTUALIZACJE.bat` (format `wwm-collection-v2`, przetestowany 8-częściowy zrzut 516 MB z Patcha 2.4), dzielenie paczek w `spakuj_dane.ps1`, `audyt_aktualizacji.py` i pakiet uzupełniający działają. |
| Starsze prototypy | `translation_bundle`, `audit_translation_*`, modele przywracania i skaner plików ([TRANSLATION_BUNDLE.md](TRANSLATION_BUNDLE.md), [UPDATES_AND_RESTORE.md](UPDATES_AND_RESTORE.md), [TWO_APPLICATIONS.md](TWO_APPLICATIONS.md)) działają tylko na wymyślonych danych i **nie są częścią obiegu** opisanego wyżej. |

## Otwarte ustalenia

1. **Test w grze na Patchu 2.4 (`26592996`), `patcher_wwm.py` i pełnej łatki** —
   mała łatka UI + prolog (`latka_testowa.py`) potwierdziła już na buildzie
   `25906190` przyjmowanie przepisanych map `translate_words_map_en*` i poprawne
   wyświetlanie wszystkich polskich znaków (`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`).
   Nadal czekają na test w oknie gry: powtórzenie próby na Patchu 2.4 (`26592996`)
   z nowym wrapperem `patcher_wwm.py` oraz pełna fabuła po zwrotce tłumacza.
2. **Który język klienta zastępujemy.** Łatka przepisuje pliki podane
   w `--cel`; dotąd sprawdzono mapę angielską.
3. **Chronologia** nie była sprawdzana w grze. 12 341 scen bez wpisu zadania
   i 25 434 ułożonych według numeru czeka na lepsze źródło (skrypty `*.ets`
   zadań nie leżą w odczytanych tabelach).
4. **Teksty bez źródła w mapie EN** — ~18 tys. wpisów jest w mapie, nie
   wskazuje ich żadna odczytana tabela (prawdopodobnie interfejs zaszyty
   w skryptach klienta).
5. **Limity pól** — nieznane; pakiet podaje długości wersji angielskiej.
6. **Zakres `EN` vs `ZH`:** w Patchu 2.4 mapa chińska ma `1 832 734` ID wobec
   `1 136 704` ID w angielskiej (`37,98%` różnicy); `702 513` niewskazanych ID
   odcięto w `index/`, a wśród pozostałych `1 294` tekstów bez `EN` ponad 70%
   to etykiety testowe, zaślepki i wpisy wycofane (`测试`, `废弃`, `占坑`).
   Zakres tłumaczenia wyznacza `--tylko-z-en` (patrz [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md)).
7. `21` pustych tabel rozmieszczeń `spaces.*` z Patcha 2.4 (`0x00`) jest bez
   tekstów i trafia do rejestru błędów w `index/manifest.json`.
8. Licencja własnego kodu i przekładu — nie wybrana, brak `LICENSE`.

## Następny krok

1. Po testach w grze albo przygotowaniu kolejnej partii: zbudować aktualną
   samowystarczalną łatkę `WWM_LATKA_PL.zip` (`python3 tools/one_click_patch.py
   --tylko-magazyn --wyj-zip dist/WWM_LATKA_PL.zip`, ~`4,3 MB`) z bieżącego
   magazynu `tlumaczenie/` (`75 685` przekładów) i potwierdzić w oknie gry
   (Patch 2.4 `26592996`, [TEST_W_GRZE.md](TEST_W_GRZE.md)).
2. Oczekiwać na zwrotki ze zregenerowanego pakietu `v4` (`paczka_dla_tlumacza_wwm_v4.zip`)
   → `tools/import_zwrotki.py` → commit `tlumaczenie/` → kolejne wydania
   Czytanek (`tools/buduj_czytanki.py`) i łatki `WWM_LATKA_PL.zip`.
3. Po każdym kolejnym patchu gry: właściciel klika
   `collector/URUCHOM_AKTUALIZACJE.bat`, następnie obieg z [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md).
