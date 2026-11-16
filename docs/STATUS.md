# Stan projektu

Aktualizacja: **2026-11-14**. Punkt wejścia dla kolejnej sesji. Cel i kryteria
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
- **Napisy prologu to sceny przerywników, nie tabela napisów.** Otwarcie gry
  (od pierwszej scenki do kreacji postaci) rysują sceny z `ui_type` 10 —
  w całym wyciągu `5 995` scen / `11 677` elementów. W pakiecie mają od
  2026-11-14 własną sekcję `cutsceny/04_sceny_cinematiczne_NN.md` (wcześniej
  mieszały się z `186` tys. zwykłych kwestii w `sceny/`), a w scenach został
  odsyłacz „tłumaczysz raz”. Szczegóły i liczby: [dziennik](EXPERIMENT_LOG.md).
- **Pokrycie przekładu (2026-11-14, po imporcie zwrotki prologu;
  `tools/pokrycie_tlumaczenia.py`):** magazyn ma `75 916` przekładów
  (`75 834` po kluczu + `82` warianty płci): napisy cutscen
  `text_msg 590000–592694` — `2 688`/`2 688` (`100%`), intro `9`/`9`, napisy
  filmowe `47`/`47` (w tym film 2 `钗头凤` `13`/`13` i film 3 `中渡桥之战`
  `21`/`21`), **blok prologu `10094–10188` bez braków**, sceny przerywników
  `1 382`/`11 678` (`11,8%`), zwykłe dialogi scen `13 880`/`187 598` (`7,4%`),
  cały wyciąg `75 834`/`487 684` (`15,5%`). Druga warstwa napisów
  (`text_msg__grey`, mówca wpisany w treść) ma `675`/`1 203` — brakujące wiersze
  cutscen dziedziczą przekład z wiersza głównego o tym samym numerze
  (`tlumaczenie.doloz_blizniaki`, tylko w pamięci). Wcześniejsze napisy po angielsku
  wynikały **z braków w magazynie, nie z podmiany pliku przez łatkę**; hipotezę
  „kolizje wariantów” sprawdzono i odrzucono (`0` przypadków w danych — patrz
  dziennik).
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
| Repozytorium i workflow | Ponad 397 testów (Linux + Windows CI); `check_repository.py` i `git diff --check` czyste; CI na Ubuntu i Windows × Python 3.11/3.12. |
| Odczyt plików gry | Baza tabel, dialogi, mapy tekstów z warstwami (z obsługą zastępowania `Package/.../_diff` przez `LocalData/Patch/.../_diff`) — sprawdzone na Patchu 2.4 (`26592996`). |
| Wyciąg i powiązania | `index/` w Git (`wwm-indeks-v2`, Patch 2.4 `26592996`), deterministyczny, ze stałym podziałem plików. |
| Pakiet tłumacza i Czytanki | Pakiety (`--tylko-z-en`; od `v5` z osobną sekcją scen przerywników `cutsceny/04_sceny_cinematiczne_*`), w tym paczki uzupełniające `--tylko-sloty`) i trzyplikowe Czytanki `wwm-czytanki-v2` (`epizody.md`, `kontekst_scen.md`, `dodatkowe.md` pod limitem `<5 MB/część`, 100% pokrycia) budują się **100% standalone z `index/`** (zero binarek gry). |
| Import zwrotki | Gotowy i zweryfikowany produkcyjnie na `WWM_PL1.zip` (`tools/import_zwrotki.py`: `75 685` zaimportowanych przekładów w `tlumaczenie/`, `0` błędów formatu/tokenów, `21` kluczy odrzuconych z powodu usunięcia w Patchu 2.4). |
| Łatka i instalator Windows | **Domyślnie standalone (`tools/one_click_patch.py`, `tools/latka_testowa.py` → `tools/build_standalone_patcher.py` + `tools/patcher_wwm.py`):** buduje `WWM_LATKA_PL.zip` wyłącznie z `index/` i `tlumaczenie/` (czysty `plan_latki.json` + lokalny patcher z kopią oryginałów, zero binarek gry). Opcjonalny tryb binarny (`instalator/`) zachowany dla jawnych flag `--dane-gry`/`--mapa`. Mała łatka testowa (`latka_testowa.py` na `25906190`) **zweryfikowana w uruchomionej grze Steam**; pełna łatka fabularna i test `patcher_wwm.py` na Patchu 2.4 (`26592996`) w realnym oknie gry czekają na sprawdzenie. |
| Aktualizacje gry | `collector/URUCHOM_AKTUALIZACJE.bat` (format `wwm-collection-v2`, przetestowany 8-częściowy zrzut 516 MB z Patcha 2.4), dzielenie paczek w `spakuj_dane.ps1`, `audyt_aktualizacji.py` i pakiet uzupełniający działają. |
| Pokrycie przekładu | `tools/pokrycie_tlumaczenia.py` mierzy z `index/` i `tlumaczenie/`, co w grze zostanie po angielsku: napisy cutscen `100%`, intro `100%`, napisy filmowe `100%` (film 2 i 3 też), prolog `100%`, sceny przerywników `11,8%`, zwykłe sceny `7,4%`, cały wyciąg `15,5%`. Tryby `--brak`, `--brak-przerywnikow`, `--arkusz`, `--szukaj`; testy w `tests/test_pokrycie_tlumaczenia.py`; pomiar bez plików gry. |
| Starsze prototypy | `translation_bundle`, `audit_translation_*`, modele przywracania i skaner plików ([TRANSLATION_BUNDLE.md](TRANSLATION_BUNDLE.md), [UPDATES_AND_RESTORE.md](UPDATES_AND_RESTORE.md), [TWO_APPLICATIONS.md](TWO_APPLICATIONS.md)) działają tylko na wymyślonych danych i **nie są częścią obiegu** opisanego wyżej. |

### Baza gry o cutscenach: co ma, a czego nie ma (pakiet aktualizacji 2026-11-13)

Pakiet `WWM_AKTUALIZACJA_20261113_193108_9bdd6b3f` (8 ZIP-ów, 54 pliki:
`data*`, `index*`, `MANIFEST`, mapy `translate_words_map_zh_cn`/`_en` i `_diff`)
rozpakowany do `local/dane` daje **114 925 tabel** i 10,2 mln wierszy. Sprawdzone
narzędziem `tools/cutsceny_z_bazy.py`:

- **osie czasu cutscen nie istnieją w tym pakiecie** — rodziny z osią czasu to
  tylko `dialog_timelines.*` (75 007 tabel, po 4 wiersze: `timeline`,
  `used_sound_bnk`, `dialog_config`) i `AL.*` (biblioteka animacji umiejętności);
- `dialog_timelines.<dialog_no>` to osie czasu **dialogów** — każdy
  `EntityTextSpan` ma `time`, `duration`, `source_id`, `text` i `formatted_text`
  (gotowy chiński tekst), ale **napisy puli `text_msg` 590000–592694 nie
  występują tam wcale** (0 trafień na 6 844 914 liczb w osiach; tekstowo pokrywa
  się tylko 392 z 2 588 linii, rozsianych po 360 dialogach, najwyżej 8 w jednym);
- **żadna tabela nie wskazuje wierszy puli ani ich hashy** `text_msg.content`
  (0 trafień po hashu w całej bazie; trafienia po samym numerze wiersza są
  przypadkowe — inne tabele mają własne identyfikatory w tym samym zakresie);
- co jest: `sound_data` (tekst → nazwa nagrania; nagrania cutscen mają w nazwie
  kod filmu `cs_<kod>_`, zgodny z `cutscenes.cine_name` = `sq001_<kod>`),
  `cutscenes` (3 990 wierszy: `cine_name`, `cine_path`, `cine_duration`,
  `cutscene_space_no`, `montage_num`, `mobile_replace`) i
  `fenbao_cutscene_info` (224 wiersze z pakietem i plikiem `.cine`).

Skutek w Czytance: `index/cutsceny_napisy.jsonl` ma 5 napisów z twardym śladem
(4 w `## Cutscena 30161`, 1 w `## Cutscena 30707`), a `index/cutsceny_meta.jsonl`
— przestrzeń i czas trwania 1 343 cutscen, z czego 1 310 ma przestrzeń; dzięki
niej 100 z 101 cutscen wyszło z „Scen bez przypisanej mapy” do swoich krain.
`--audyt` przelicza dowody negatywne i zapisuje `out/audyt_cutscen.json`.
Żeby przypiąć resztę puli (2 683 napisy), trzeba **osie czasu cutscen** — pliki
`.cine` albo tabelę, której ten pakiet nie zawiera. 487 testów zielonych.

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
7. **Napisy kinowe są przetłumaczone w magazynie, ale nie w grze.** Prolog
   (`10094–10188`), napisy `text_msg` i filmy 2–3 mają przekład po stronie
   `tlumaczenie/`; czy klient pokaże je po polsku, rozstrzygnie dopiero łatka
   u właściciela — nie wiadomo też, czy napisy filmów idą
   z `entry_collect_movie_subtitle_data`, czy z tych samych scen. Poza
   prologiem nadal `10 296` wierszy scen przerywników i `173 718` zwykłych
   kwestii czeka na przekład (`tools/pokrycie_tlumaczenia.py --arkusz`).
8. `21` pustych tabel rozmieszczeń `spaces.*` z Patcha 2.4 (`0x00`) jest bez
   tekstów i trafia do rejestru błędów w `index/manifest.json`.
9. Licencja własnego kodu i przekładu — nie wybrana, brak `LICENSE`.

## Następny krok

0. **Czytanka do czytania w nowym układzie — zbudowana, do wysłania.** Trzy pliki
   według ustaleń właściciela: `01_sceny_i_cutsceny.md` (filmy, prolog, krainy po
   kolei — sceny **i** cutsceny przemieszane w kolejności występowania w grze),
   `02_kontekst_scen_i_cutscen.md` (kontekst w tej samej kolejności),
   `03_reszta.md` (co nie trafiło do 01 ani 02, według rodzaju). Kolejność nie
   jest już liczona przy każdym budowaniu: leży w `index/chronologia.jsonl`
   (75 704 jednostki, 4,1 MB), generowana przez `tools/chronologia.py`
   i pilnowana testem `tests/test_chronologia.py`. Liczby: 8 910 scen,
   1 597 cutscen; gracz zawsze jako `Youxia`; kwestie bez przekładu idą
   z gwiazdką (160 262 linie), prolog jest przetłumaczony w całości;
   kontekst w pliku 02 obejmuje 73 296 jednostek; 9 319 kwestii ma jeszcze
   chińską etykietę mówcy — schodzą ze słownikiem `index/nazwy_mowcow.json`.
   Pieśni i filmy stoją na końcu (w grze nie ma ich na starcie), a **wszystkie
   trzy pliki są bez punktora**: `**Mówca:** tekst`, `**Nazwa:** opis`, bez mówcy
   goły tekst. **Paczki numerujemy, nie datujemy:** `dist/WWM_Czytanka_PL_v4.zip`
   (`6 609 291 B`, SHA-256
   `0fe0461f28e7d89a1b53b0f6e6b2e502965b79380a716d42f4a7d5daa6afd85c`),
   Dysk Google id `1WzykudtneN3nrsjVMVxVxpU7vB-C2xT4` (v3 w koszu;
   wszystkie paczki z datą
   w nazwie są nieaktualne i leżą w koszu). Spis wersji:
   [WERSJE_CZYTANKI.md](WERSJE_CZYTANKI.md); `--wersja N` odmawia nadpisania
   istniejącej paczki. Opis formatu:
   [CZYTANKA_DO_CZYTANIA.md](CZYTANKA_DO_CZYTANIA.md).
   **Stan po decyzjach właściciela z 2026-11-15:** (a) do pliku 02 wchodzą tylko
   hasła, które gra naprawdę opisuje — 8 891 jednostek ma kontekst, 65 351
   pozycji bez opisu przeniesiono do 03 (m.in. `江晏`/Jiang Yan, `镇冠珏`/Nefryt
   Zhenguan, `丰厚醇`/Hojna Wiosna, `燕北旧盟`/Dawne Przymierze Yanbei — gra nie
   daje im żadnego opisu); (b) karty bez opisu zniknęły też z list haseł, razem
   z 28 tys. śmieciowych wpisów (`玩家`, `0`, `Entity轨道组`) i 747 duplikatami;
   (c) 4 713 chińskich etykiet mówców przeszło na łacinkę (`大祭师` → `Da Ji Shi`)
   przez tabelę `index/pinyin_znakow.json` (3 156 znaków, `tools/pinyin_slownik.py`),
   więc w czytance nie ma już ani jednej chińskiej etykiety mówcy ani samego
   numeru postaci. **Sprawdzone, dlaczego transliteracja jest w ogóle potrzebna:**
   w danych gry 59 884 wpisy obsady mają klucz nazwy i wszystkie mają angielską
   wersję (0 braków), ale 53 184 wpisy mają tylko chińską etykietę roboczą —
   tabliczkę z nazwą ma zaledwie 32% bytów, więc dla 4 713 etykiet (5% kwestii)
   gra nie ma angielskiego tekstu do pokazania. Doszła też ścieżka
   „byt → `spaces.*.entity.N.name`”, która odzyskuje z danych 66 angielskich
   nazw. **02 po decyzji z tej samej sesji:** opis hasła = definicja z danych gry
   (`describe*`, `introduction*`, `description`, `npc_desc`, `job_info`),
   a przy postaciach sama tożsamość z encyklopedii (`tozsamosc`); rozdziały
   fabularne encyklopedii (`historie`) i karty z samą nazwą są wycięte.
   Zostało 501 jednostek z kontekstem i 178 kart (każda raz). **Streszczenie
   cutsceny z prologu** (`cutscenes.synopsis_text_mobile`) wchodzi teraz jako
   jednostka `## Cutscena 30150` dokładnie tam, gdzie stoi w transkrypcie —
   między Prolog 3 i Prolog 4 — i nie powtarza się w „Scenach bez przypisanej
   mapy”; tabliczka krainy (`cutscene_text_oversea`) nie udaje już kwestii
   prologu. **Napisy przerywników** (pula `text_msg`, 2 688 wierszy) wyszły
   z alfabetycznej reszty: blok rozpoznany po kotwicy scen albo po nazwie nagrania
   dostaje numer cutsceny i stoi w niej (`## Cutscena 30161` ma pełną scenę
   „Wodzu, obudź się!” z Ruby), a pozostałe 44 bloki stoją w sekcji
   `# Napisy przerywników` w kolejności wierszy z pliku gry. W danych gry napis
   **nie ma numeru cutsceny** — numer siedzi w osi czasu cutsceny, której wyciąg
   z `index/` nie obejmuje, więc 2 349 z 2 688 wierszy nie da się przypisać
   do konkretnej cutsceny. **Rozdział pierwszy wrócił do krainy:** kotwicą grupy
   jest pierwsza scena z mapą (wcześniej `luwenxin.dialog` bez map wysyłał całą
   grupę do „Scen bez przypisanej mapy”), a cutsceny w grupie stoją w kolejności
   zadań — `## Cutscena 30161` z Ruby jest teraz w krainie 燕南. Do przypięcia
   pozostałych napisów doszło narzędzie `tools/cutsceny_z_bazy.py` (szuka w bazie
   tabeli wiążącej napis z cutsceną; czyta też sam spis schematów z
   `spakuj_dane.ps1 -Zakres schematy`) i zakres `schematy` w zbieraczu.
   482 testy zielone (520 podtestów).
   **Poprzedni układ (`01_sceny.md` / `02_cutsceny.md` / `03_reszta.md`,
   `WWM_Czytanka_PL_2026-11-14.zip`) jest nieaktualny** — sceny i cutsceny były
   rozdzielone, czego właściciel nie chce.
1. **Czytanka w kolejności z gry — warstwa chronologiczna.** `tools/buduj_czytanke_gry.py`
   buduje ją z `index/prowincje.json`: prolog → krainy w kolejności odwiedzania
   (`燕南 → 清河 → 熔炉 → 河西 → …`) → sceny po numerze dialogu. Opis i granice:
   [CZYTANKA_KOLEJNOSC_GRY.md](CZYTANKA_KOLEJNOSC_GRY.md). Paczki na Dysku
   Google: `WWM_Czytanka_Gry_2026-11-14.zip` i `WWM_Czytanka_Gry_tylko_PL_2026-11-14.zip`.
   Właściciel czyta
   i zgłasza punkty, w których gra pokazuje treść inaczej — poprawiamy je punktowo
   (np. powrót na zwiedzoną mapę), nie przez przestawianie całości.
2. **Uruchomić w grze gotową łatkę `v0.4.0` i sprawdzić prolog.** Wysłana na
   Dysk Google `WWM_Spolszczenie_PL_v0.4.0.zip` (`5 330 079 B`, SHA-256
   `2bfdfc62…2ad8`, `86 282` przekłady) zawiera napisy
   prologu z obu zwrotek (`zwrotki/2026-11-14_prolog_pl.md`, `232` klucze;
   `zwrotki/2026-11-14_prolog_2_pl.md`, `4` klucze) oraz `675` wierszy warstwy
   `text_msg__grey` przejętych z wierszy głównych.
   Jedno uruchomienie gry — najlepiej od nowej postaci do kreacji — powie, czy
   prolog jest polski i czy napisy filmów 2–3 idą z tej samej treści.
   **Do tego czasu nie twierdzimy, że cinematic jest już polski w grze.**
   Przed każdą diagnozą „coś jest po angielsku” uruchomić
   `python3 tools/pokrycie_tlumaczenia.py` (`--brak`, `--brak-przerywnikow`,
   `--szukaj "<fragment zdania>"`).
3. Potwierdzić w oknie gry (Patch 2.4 `26592996`) opublikowane na Dysku Google
   pierwsze wydanie samowystarczalnego spolszczenia **`WWM_Spolszczenie_PL_v0.1.0.zip`**
   (`75 685` przekładów z `tlumaczenie/`, ok. `4,3 MB`, `tools/one_click_patch.py
   --tylko-magazyn --wydanie v0.1.0 --wyj-zip dist/WWM_Spolszczenie_PL_v0.1.0.zip`).
4. Oczekiwać na zwrotki ze zregenerowanego pakietu `v4` (`paczka_dla_tlumacza_wwm_v4.zip`)
   → `tools/import_zwrotki.py` → commit `tlumaczenie/` → kolejne wydania
   Czytanek (`tools/buduj_czytanki.py`) i kolejne wydania `WWM_Spolszczenie_PL_v*.zip`.
5. Po każdym kolejnym patchu gry: właściciel klika
   `collector/URUCHOM_AKTUALIZACJE.bat`, następnie obieg z [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md).
