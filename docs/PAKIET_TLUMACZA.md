# Pakiet dla tłumacza i potok aktualizacji

Stan na **2026-11-12**. Ten dokument opisuje cały obieg: pliki gry → wyciąg
`index/` → pakiet dla tłumacza → zwrotka → magazyn przekładów → łatka, oraz to
samo przyrostowo po aktualizacji gry. Cel i kryteria: [CEL.md](CEL.md). Format
plików gry: [BAZA_GRY.md](BAZA_GRY.md), [LOCALE_CONTAINER.md](LOCALE_CONTAINER.md).

Zastępuje usunięte `TRANSLATOR_PACKAGE_WWM.md`, `format_tlumacza.md`,
`SCENY_WWM.md` i `ANALIZA_KORPUSU.md` (opisywały poprzedni parser, który
przypisywał scenie numer sceny następnej).

## Obieg w jednym obrazie

```text
pliki gry (prywatne, poza Git)
  MANIFEST + indexN + dataN            baza tabel i dialogów
  translate_words_map_zh_cn[_diff]     tekst źródłowy
  translate_words_map_en[_diff]        tekst pomocniczy i cel łatki
        │  tools/wyciag.py                     (ok. 3,5 min)
        ▼
index/  (Git)                           teksty raz na tekst + sceny + powiązania
        │  tools/buduj_paczke.py               (ok. 30 s)
        ▼
README.md + sceny.zip + cutsceny.zip + widoki.zip → tłumacz (Dysk właściciela)
        │  zwrotka: te same pliki .md z wypełnionym PL:
        ▼  tools/import_zwrotki.py
tlumaczenie/  (Git)                     klucz tekstu → przekład
        │  tools/one_click_patch.py (standalone z index/) albo zbuduj_latke.py
        ▼
plan_latki.json + patcher / mapy        → próba UI+prolog potwierdzona w grze; pełna łatka czeka na zwrotkę

po patchu gry:  nowy wyciąg → tools/audyt_aktualizacji.py → nowe_sloty.txt
                → tools/buduj_paczke.py --tylko-sloty → pakiet uzupełniający
```

## Klucz tekstu — na czym wszystko wisi

Gra trzyma tekst pod 64-bitowym identyfikatorem, osobno w mapie każdego języka.
Jeden chiński tekst ma często wiele identyfikatorów (średnio 2,3).

- **Klucz tekstu** = pierwsze 16 znaków szesnastkowych SHA-256 **tekstu
  źródłowego** (`tools/mapa_tekstow.klucz`). Źródłem jest tekst chiński, a gdy
  identyfikator ma tylko wersję angielską — angielski.
- Przekład jest przypisany do klucza, nie do identyfikatora. Skutki:
  - jedno `PL:` obsługuje wszystkie miejsca w grze z tym samym tekstem źródłowym;
  - po aktualizacji gry tekst pod nowym identyfikatorem jest już przetłumaczony,
    a zmieniony tekst pod starym identyfikatorem ma nowy klucz, więc wraca do
    tłumacza jako nowy;
  - poprawka samej wersji angielskiej (częsta w patchach) niczego nie zmienia.
- Wyjątek: **kwestie zależne od płci bohatera**. Gra ma dla nich osobne
  identyfikatory nawet przy jednakowym tekście chińskim, więc w pakiecie mają
  klucz `@` + identyfikator i przekład przypisany do identyfikatora. Wariant
  zostawiony pusty dziedziczy po drugim wariancie tego samego tekstu, a w
  ostateczności po kluczu.

## Wyciąg `index/` (`wwm-indeks-v2`)

Zapis: `tools/wyciag.py`, odczyt: `tools/indeks.py`, kontrola spójności:
`python3 tools/indeks.py index --sprawdz` i `tests/test_indeks_repo.py`.

```sh
python3 tools/wyciag.py \
  --baza local/patch24/Package/HD/oversea local/patch24/LocalData/Patch/HD/oversea \
  --zh local/patch24/Package/HD/oversea/locale/translate_words_map_zh_cn \
       local/patch24/Package/HD/oversea/locale/translate_words_map_zh_cn_diff \
  --en local/patch24/Package/HD/oversea/locale/translate_words_map_en \
       local/patch24/Package/HD/oversea/locale/translate_words_map_en_diff \
       local/patch24/LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff \
  --opis "Steam 3564740, build 26592996, Patch 2.4, pliki z 2026-11-13" --wyj index
```

Kolejność katalogów `--baza` i plików map: późniejszy przykrywa wcześniejszy
(paczka → `LocalData/Patch`). Katalog z `MANIFEST` z patcha musi być ostatni.
Dla warstw `_diff` tego samego języka funkcja `tools/mapa_tekstow.wybierz_warstwy_gry`
(wywoływana automatycznie również przez `wyciag.py` oraz `patcher_wwm.py`)
odrzuca starsze `Package/.../_diff`, jeśli istnieje odpowiadający im plik
`LocalData/Patch/.../_diff` — tak aby składanie dokładnie odpowiadało regule klienta
z Patcha 2.4 ([LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)).
Wynik jest deterministyczny: te same wejścia dają bajt w bajt te same pliki.

| plik | zawartość |
|---|---|
| `manifest.json` | liczby, pokrycie, SHA-256 wejść, lista plików z SHA-256 |
| `teksty_0…f.jsonl` | jeden wiersz na unikalny tekst źródłowy: `zh`, `en` (najczęstsza wersja angielska), `n` (liczba identyfikatorów), `w` = [numer źródła, wiersz tabeli, klucz nazwy wiersza]; plik = pierwszy znak klucza |
| `zrodla.json` | lista źródeł `[tabela, pole, liczba wystąpień]` |
| `sceny_0…7.jsonl` | dialog: `d` numer, `p` projekt, `o` obsada `[etykieta, typ, byt, klucz nazwy, klucz tytułu, klucz opisu]`, `e` elementy `[rodzaj, mówca, klucz, wariant, id, klucz podmienionej nazwy]`, `r` odwołania, `m` przestrzenie, `x` następstwa; plik = numer modulo 8 |
| `warianty.jsonl` | kwestie zależne od płci: id tekstu, klucz, wariant, wersja angielska tego id |
| `pola_dialogow.json` | pola tabel, które wskazują numery dialogów (z liczbą trafień) |
| `zadania.jsonl`, `grupy_zadan.jsonl`, `typy_zadan.jsonl`, `streszczenia.jsonl` | zadania z łańcuchem `pre`/`post`, dialogami i przerywnikami; rozdziały |
| `wybory.jsonl`, `opcje_npc.jsonl` | pytania z wyborami gracza i opcje rozmowy |
| `postacie.jsonl`, `encyklopedia.jsonl` | byt → nazwa, tytuł, opis; osoby z encyklopedii gry |
| `miejsca.jsonl`, `przerywniki.jsonl`, `zamiany_dialogow.jsonl` | przestrzenie, plansze przerywników, podmiany dialogów |

### Liczby (Patch 2.4, build 26592996, pliki z 2026-11-13)

| miara | wartość |
|---|---:|
| identyfikatorów w mapie chińskiej / angielskiej | 1 832 734 / 1 136 704 |
| identyfikatorów w zakresie pakietu | 1 140 673 |
| **unikalnych tekstów w zakresie** | **487 684** |
| w tym bez wersji chińskiej (źródłem angielski) | 5 754 |
| identyfikatorów tylko chińskich, których nic nie wskazuje (pominięte) | 702 513 |
| dialogów (scen) / bez żadnego tekstu | 75 007 / 1 577 |
| kwestii / elementów scen razem | 186 288 / 187 598 |
| kwestii zależnych od płci bohatera | 1 860 |
| kwestii bez grupy mówcy | **0** |
| zadań / grup zadań / pytań z wyborami | 24 753 / 1 077 / 15 036 |
| identyfikatorów angielskich ze wskazanym źródłem (tabela lub scena) | 1 063 774 (93,58%) |

**Zakres i zasada źródeł.** W danych buildu `26592996` (Patch 2.4) mapa `zh_cn` ma
`1 832 734` identyfikatorów, a `en` — `1 136 704` (czyli **37,98%**
identyfikatorów z `zh_cn` nie ma w mapie angielskiej).

- `702 513` identyfikatorów wyłącznie chińskich bez wskazania z tabel ani
  scen zostało już pominiętych przy budowie `index/`.
- Z pozostałych `1 140 673` identyfikatorów w `index/` (`487 684` unikalnych
  tekstów):
  - `480 636` ma i `ZH`, i `EN` (`1 126 127` ID),
  - `5 754` ma tylko `EN` (`10 577` ID — źródłem jest angielski),
  - `1 294` ma tylko `ZH` (`3 969` ID — w `paczka v1` weszły do pakietu, ale
    ponad 70% to etykiety testowe, zaślepki i wpisy wycofane typu `测试`,
    `废弃`, `占坑`, a reszta to treści niewydane w wersji globalnej).
- **Przyjęta zasada zakresu:** tłumaczeniu w wersji polskiej podlegają wyłącznie
  wpisy mające odpowiednik angielski w kliencie globalnym (`EN` wyznacza
  zakres „co jest wydane w grze”, a `ZH` pozostaje głównym tekstem źródłowym,
  z `EN` jako odniesieniem; dla `5 754` wpisów wyłącznie EN źródłem jest `EN`).
  Wiersze wyłącznie chińskie czekają, aż trafią do globalnego wydania — wtedy
  kolejny audyt wyłapie je jako aktualizację („patch tłumaczenia”). Od strony
  narzędzi obsługuje to flaga `--tylko-z-en` w `tools/buduj_paczke.py` (na
  bieżącym `index/` ogranicza pakiet z `423 197` do `422 248` miejsc `PL:`,
  a w całym słowniku `index/` z `487 684` do `486 390` tekstów) oraz w
  `tools/audyt_aktualizacji.py`.

**Mówcy.** Kwestia leży w torze `EntityTextTrack` wewnątrz grupy
`EntityTrackGroup`, więc mówca wynika z budowy danych. Nazwa mówcy:
111 975 kwestii ma nazwę z gry (pole sceny albo tabliczka bytu), 37 458 to
gracz, 36 803 ma tylko roboczą etykietę twórców (`entity_tag`), 52 nic.

## Pakiet (`wwm-paczka-v1`, wysłana wersja `v3` + gotowy wyciąg pod `v4` / `patch24`)

```sh
python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_wwm_v4 --wersja 4 --data 2026-11-13 --tylko-z-en
```

Wynik: `README.md`, `sceny/`, `cutsceny/`, `widoki/`, `sceny.zip`,
`cutsceny.zip`, `widoki.zip`, `paczka_dla_tlumacza_wwm_v4.zip` (cztery
poprzednie w jednym pliku) i `paczka.json` (manifest z liczbami, listą plików
i wynikiem kontroli). Archiwa są powtarzalne: ta sama zawartość daje ten sam
SHA-256. Kopia `README.md` i `paczka.json` każdej **wysłanej** wersji leży w
`paczki/`.

Kontekst cutscen i mówców między `tools/buduj_paczke.py` i
`tools/buduj_czytanki.py` jest współdzielony w module
`tools/kontekst_cutscen.py`. W wysłanej wersji `v3` (`25906190`, `--tylko-z-en`)
pakiet zawierał **418 773** miejsc `PL:`; po aktualizacji `index/` do Patcha 2.4
(`26592996`) pełny `v4` ma **422 248** miejsc `PL:` (`168 191` w `sceny.zip`,
`4 116` w `cutsceny.zip`, `249 941` w `widoki.zip`), `0` powtórzonych i `0`
brakujących, a pakiet uzupełniający różnicy `25906190 → 26592996` ma **4 010**
miejsc `PL:` (`42` w `sceny.zip`, `6` w `cutsceny.zip`, `3 962` w `widoki.zip`).
Postać gracza w przebraniu oznaczana jest jako `gracz (przebranie/rola: …)`,
a zadania z powiązaną powtórką w dzienniku dostają w nagłówku wpis `- powiązana cutscena
w dzienniku: #…`.

Element (pełny opis dla tłumacza jest w `README.md` pakietu):

```text
14. [Kwestia — 红线 (Ruby)] 哇，这是什么暗号吗？
   klucz: 693cf29aef2cf70a
   tokeny: zachowaj dokładnie: #Y, #E        ← tylko gdy tekst ma kody gry
   EN: Whoa, what symbol is that?
   PL:
```

Zasady składania:

- **Jeden tekst — jedno `PL:` w całym pakiecie**: pierwsze wystąpienie
  w kolejności sceny → widoki. Dalsze wystąpienia mają wskazanie miejsca
  z przekładem. Kontrola po zbudowaniu czyta pliki tak jak import i sprawdza,
  że miejsca `PL:` pokrywają dokładnie wszystkie teksty (wersja 1: 485 047
  miejsc, 0 powtórzonych, 0 brakujących).
- Tekst stoi w jednej linii; nowa linia to `\n`, tabulator `\t`, prawdziwy
  ukośnik `\\` (`tools/format_paczki.py`).
- Kody gry (`#Y…#E`, `{0}`, `%s`, `$T(2001)`, `<nazwa|780|#C|15>`, `<LINK …>`,
  `[[…]]`) wylicza linia `tokeny:`; import odrzuca przekład, w którym się nie
  zgadzają.
- Limity: w danych gry nie ma długości pól. Widoki podają długość najdłuższego
  tekstu angielskiego w tym samym polu; sceny nie mają `limit:`.

### `sceny.zip` — kolejność (`tools/uklad_scen.py`)

Scena = jeden dialog = jedna tabela `dialog_timelines.<numer>`; granice są więc
dane. Kolejność składa się z danych gry, od najmocniejszych:

| sposób | scen (wersja 1) | co to znaczy |
|---|---:|---|
| wpis w tabeli zadań (przyjęcie, rozmowa, zakończenie, pytanie z wyborem) | 8 971 | fakt z danych |
| następstwo wyboru albo poprzedniego dialogu | 89 | fakt z danych |
| sąsiedztwo numerów w tym samym projekcie (odstęp ≤ 5) | 25 456 | **kolejność z numeracji, nie powiązanie**; napisane w nagłówku sceny |
| brak wpisu — według projektu i numeru (`80_…`) | 12 303 | numeracja gry |
| rozmowy tła — według miejsca (`90_…`) | 26 554 | dialogi wskazywane tylko przez rozmieszczenie i reakcje NPC |

Zadania: typ (wątek główny pierwszy, dalej według kolejności typów z gry) →
grupa (rozdziały według `group_sort`) → części rozdziału `pian` rosnąco →
łańcuch `pre_task`/`post_task` w głąb, z dociąganiem brakujących poprzedników
tuż przed zadanie, które ich wymaga. W wątku głównym żadne zadanie nie stoi
przed swoim poprzednikiem; w całej grze łańcuch 36 razy zamykał się w cykl
i został przerwany.

**Chronologia nie była sprawdzana w grze.** Zgodnie z kryterium z
[CEL.md](CEL.md) zastępuje ją kolejność z danych. Wątek główny ma w plikach
zadań 2 445 scen; część scen fabularnych wywołują skrypty (`*.ets`), których
w odczytanych tabelach nie ma — te sceny są w wierszach „numeracja” i „projekt”.

Nagłówek sceny: projekt, zadanie z celem, miejsce (nazwa przestrzeni),
wywołanie w danych, uczestnicy z tytułem i opisem postaci z gry
(`entity_attr.introduction`) oraz oznaczeniem postaci z encyklopedii, obecni
bez kwestii. Pod zadaniem stoją też plansze i streszczenia przerywników,
a po scenie — wybory gracza z dialogami, do których prowadzą.

### `widoki.zip`

Teksty spoza scen, przy tabeli i polu, z którego pochodzą
(`[tabela · pole · wiersz]`, `dotyczy:` = nazwa wiersza, `limit:`). Podział na
11 serii wynika z nazw tabel (`REGULY` w `tools/buduj_paczke.py`): postacie,
zadania, wybory i rozmowy, przedmioty, walka, świat, encyklopedia i księgi,
komunikaty, interfejs, pozostałe (1 030 małych tabel) i teksty bez źródła
(18 157 tekstów, których nie wskazuje żadna tabela ani scena).

Tabela `debate_guider_dialog_data` powtarza kwestie scen (66 357 z 66 372 jej
wierszy to teksty obecne w dialogach), więc w widokach ma tylko teksty,
których w scenach nie ma.

**Gdzie jest otwierający prolog vs Rozdział 1.** Pierwsza cutscenka z początku
gry (m.in. kwestie Jiang Yana i Chen Zixiego: `Even at the end of the road,` /
`a drink to wet your throat.`, pościg o Nefryt Zhenguan) nie leży w tabelach
`dialog_timelines`, lecz w napisach przerywnikowych `text_msg` (wiersze
`590291–590390`). Od pakietu `v2`/`v3` jest wydzielona w **`cutsceny.zip`** →
**`01_napisy_cutscen_01.md`** (w `v3` w logicznym segmencie `### Prolog — nocna podróż powozem: Jiang Yan (Jiang Wulang) i Chen Zixi`, wraz z rozpoznanymi mówcami, wskazaniem kolizji `sound_data` oraz linkami do powtórek w dzienniku). W starym pakiecie `v1` leżała rozbita w `widoki.zip` między `07_komunikaty_04.md` i `07_komunikaty_12.md`. Bezpośrednio po obudzeniu bohatera fabuła przechodzi już do **`sceny.zip`** → **`01_watek-glowny_rozdzial-1_01.md`** (zadania `220001`–`220003`, dialog `4700001`).

### `cutsceny.zip`

Wydzielona sekcja cutscen (4 532 elementów, 4 116 `PL:` w `v3`):
- `01_napisy_cutscen_01.md` — napisy `text_msg` `590000–592694` podzielone po
  lukach ID i domenach audio (`sound_data`) na 91 pod-scen fabularnych
  (w `v3`), z przypisaniem mówców z prefiksów ZH, `sound_data`, `mowca_en`
  (bez fałszywych trafień `_npc_pma_` na gracza), wygładzonych cytatów
  `world_view_person_voice`, adnotacjami o kolizjach `sound_data` oraz
  linkami do powtórek `task_cutscene_replay`;
- `02_intro_i_filmy_01.md` — sekwencja wprowadzająca *One Day in the Imperial
  Service* (`wds_oneday_intro_cutscene_data`, z mówcami `gracz: You Xia` /
  `Gwardia Cesarska`) i napisy filmowe (`entry_collect_movie_subtitle_data`);
- `03_plansze_i_streszczenia_01.md` — powtórki w dzienniku
  (`task_cutscene_replay`, w tym ich tytuły, rozdziały i streszczenia) oraz
  pozostałe plansze `cutscenes` z powiązaniem klonów mobilnych (`>= 10 000 000`),
  zadań i wątków.

## Zwrotka → magazyn przekładów

```sh
python3 tools/import_zwrotki.py ZWROTKA --indeks index --magazyn tlumaczenie --raport dist/import.json
```

`ZWROTKA` to katalog, plik `.md` albo zip (także zip z `sceny.zip`
i `widoki.zip`). Liczą się tylko linie `klucz:` i `PL:`, więc tłumacz może
odsyłać części, partiami i wielokrotnie. Kontrole: klucz znany wyciągowi,
przekład w jednej linii, kody gry zgodne z tekstem źródłowym albo angielskim,
brak dwóch różnych przekładów tego samego klucza. Wpis z problemem nie wchodzi
do magazynu i trafia do raportu z plikiem i numerem linii (bez treści).

Magazyn (`tools/tlumaczenie.py`): `tlumaczenie/pl_0…f.jsonl`
(`{"k": klucz, "pl": przekład}`) i `tlumaczenie/pl_warianty.jsonl`
(`{"id": identyfikator, "pl": przekład}`). Katalog powstanie przy pierwszej
zwrotce i jest wersjonowany — to jest właściwy dorobek projektu.

## Łatka

```sh
# Domyślnie (standalone — zero binarek gry, wyłącznie z repozytorium index/ + tlumaczenie/):
python3 tools/one_click_patch.py --tylko-magazyn --wyj-zip dist/WWM_LATKA_PL.zip

# Albo bezpośrednio ze zwrotki:
python3 tools/one_click_patch.py --zwrotka ZWROTKA.zip --wyj-zip dist/WWM_LATKA_PL.zip
```

Pliki binarne gry z Dysku Google są potrzebne **wyłącznie na etapie eksploracji
i przy aktualizowaniu wyciągu `index/`**. Budowanie Czytanek
(`tools/buduj_czytanki.py`), budowanie pakietów (`tools/buduj_paczke.py`),
audyt aktualizacji (`tools/audyt_aktualizacji.py`) oraz **generowanie łatki**
(`tools/one_click_patch.py`, `tools/latka_testowa.py`) działają w 100%
samowystarczalnie na danych z repozytorium.

Gra nie ma języka polskiego, więc przekład **zastępuje teksty jednego
z języków klienta** (domyślnie angielskiego `translate_words_map_en*`, na każdej
warstwie `_diff` z osobna). W trybie standalone `WWM_LATKA_PL.zip` niesie
wyłącznie czysty plan tekstowy (`plan_latki.json`) oraz lokalny patcher
(`tools/patcher_wwm.py`), który dopiero na komputerze gracza zabezpiecza oryginały
poza katalogiem gry i przepisuje je lokalnie. (Do pracy w piaskownicy na
wskazanych plikach binarnych dostępne jest również niskopoziomowe
`tools/zbuduj_latke.py` lub opcje `--dane-gry` / `--zh` + `--mapa`.)

Przed pełną łatką warto przy każdym nowym trybie instalatora sprawdzić małą próbę UI i prologu opisaną
w [TEST_W_GRZE.md](TEST_W_GRZE.md) (`python3 tools/latka_testowa.py --wyj-zip dist/WWM_LATKA_TEST_PL.zip`).

**Stan w grze:** mała łatka testowa (`latka_testowa.py` na mapie angielskiej —
UI i otwierający prolog) została już uruchomiona w kliencie Steam i potwierdziła,
że gra przyjmuje przepisane mapy oraz wyświetla komplet polskich znaków
(`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`). **Nie sprawdzono jeszcze w grze**
pełnej łatki fabularnej (czeka na zwrotkę tłumacza), limitów szerokości pól
oraz nowego samowystarczalnego instalatora `patcher_wwm.py` bezpośrednio w
oknie gry. Nie obiecujemy bezpieczeństwa konta.

## Aktualizacja gry — co robić krok po kroku

1. **Właściciel** po patchu gry uruchamia `URUCHOM_AKTUALIZACJE.bat`
   z zestawu `collector/` (jednym kliknięciem pakuje `LocalData/Patch/HD/oversea/*`,
   `Package/HD/oversea/{MANIFEST,data1001,data1200,index1001,index1200}`,
   wszystkie warstwy `*_diff` oraz `translate_words_map_zh_cn` do ZIP-a < 90 MiB;
   przy większej aktualizacji klienta `spakuj_dane.ps1` dzieli wynik na części
   <= 85 MiB) i wrzuca archiwum na Dysk.
2. **Agent** pobiera pliki do `google_drive/`, wypakowuje do `local/`
   i przebudowuje wyciąg w katalogu roboczym (`tools/wyciag.py`, jak wyżej).
3. Audyt względem ostatniego commita (flaga `--tylko-z-en` wyłapuje również
   wcześniejsze wpisy wyłącznie chińskie, które właśnie dostały wydanie EN):

   ```sh
   python3 tools/audyt_aktualizacji.py --stary-git HEAD --nowy index \
     --wyj dist/audyt --tlumaczenie tlumaczenie --tylko-z-en
   ```

   `AUDYT.md` mówi, ile jest nowych i usuniętych tekstów, które sceny są nowe
   albo zmienione i ile po aktualizacji brakuje przekładów.
4. Pakiet uzupełniający — tylko nowe teksty, w kontekście:

   ```sh
   python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_wwm_v2 --wersja 2 \
     --data RRRR-MM-DD --tylko-sloty dist/audyt/nowe_sloty.txt --tlumaczenie tlumaczenie --tylko-z-en
   ```

   Sceny z nową kwestią są pokazane w całości; stare kwestie mają
   `PL (już jest): …` albo znacznik „z wcześniejszego pakietu”.
5. Commit nowego `index/` (zmieniają się tylko wiersze, które się zmieniły —
   podział plików jest stały) i kopii `README.md` + `paczka.json` w `paczki/`.
6. Po zwrotce: import (jak wyżej), commit `tlumaczenie/`, nowa samowystarczalna łatka
   przez `tools/one_click_patch.py` (z samego repozytorium, bez pobierania map z Dysku).

Sprawdzone na prawdziwych danych aktualizacji:
- wcześniejszy skok między paczką bazową a `LocalData/Patch` w buildzie `25906190`:
  `387` nowych tekstów, `64` usunięte, `0` zmienionych scen;
- aktualizacja do Patcha 2.4 (`25906190 → 26592996`, `2026-11-13`): `+4 171` nowych
  tekstów w zakresie `--tylko-z-en`, `566` usuniętych, `57` nowych i `21` zmienionych
  scen (`49` nowych tekstów w scenach); pakiet uzupełniający ma `4 010` miejsc `PL:`
  (`42` w `sceny.zip`, `6` w `cutsceny.zip`, `3 962` w `widoki.zip`, ZIP `364 KB`).

## Co jest hipotezą, a co faktem

| twierdzenie | status |
|---|---|
| numer dialogu, mówca, kolejność kwestii w scenie | fakt z budowy danych, sprawdzony na wszystkich 75 007 dialogach |
| powiązanie sceny z zadaniem przez pola tabel zadań i wyborów | fakt z danych |
| kolejność zadań w grupie | łańcuch z danych; nie sprawdzona w grze |
| scena „według numeru” należy do sąsiedniego zadania | **hipoteza**, tak oznaczona w pakiecie |
| `valid_for_specific_type` + `entity_type` 1/2 toru = wariant bohatera/bohaterki | odczyt z danych (tory animacji `…_male` / `…_female`, różne teksty zwrotów); nie sprawdzony w grze |
| pominięte identyfikatory tylko chińskie nie są wyświetlane w kliencie zachodnim | **hipoteza** |
| tabele `__grey` to druga wersja tej samej tabeli | **hipoteza** z nazwy; ich teksty są w pakiecie |
| mała łatka (`latka_testowa.py` UI + prolog) przyjmowana przez grę, polskie znaki się wyświetlają | **fakt — potwierdzone w uruchomionej grze Steam (Windows)** |
| pełne tłumaczenie fabularne i wrapper `patcher_wwm.py` w oknie gry | **jeszcze nie sprawdzone w grze** (czeka na zwrotkę tłumacza; format map identyczny) |
