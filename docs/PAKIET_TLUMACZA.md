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
        │  tools/buduj_paczke.py               (ok. 25 s)
        ▼
README.md + sceny.zip + widoki.zip      → tłumacz (Dysk właściciela)
        │  zwrotka: te same pliki .md z wypełnionym PL:
        ▼  tools/import_zwrotki.py
tlumaczenie/  (Git)                     klucz tekstu → przekład
        │  tools/zbuduj_latke.py + mapy z gry
        ▼
przepisane mapy tekstów                 → instalacja u właściciela (jeszcze nie sprawdzona w grze)

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
  --baza local/oversea_oversea local/oversea_oversea2 local/oversea_oversea3 \
         local/idx/index local/idx/index2 local/patch/oversea \
  --zh google_drive/translate_words_map_zh_cn local/zbieracz/pliki/000007_translate_words_map_zh_cn_diff \
  --en local/zbieracz/pliki/000001_translate_words_map_en \
       local/zbieracz/pliki/000003_translate_words_map_en_diff \
       local/zbieracz/pliki/000002_translate_words_map_en_diff \
  --opis "Steam 3564740, build 25906190, pliki z 2026-11-11" --wyj index
```

Kolejność katalogów `--baza` i plików map: późniejszy przykrywa wcześniejszy
(paczka → `LocalData/Patch`). Katalog z `MANIFEST` z patcha musi być ostatni.
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

### Liczby (build 25906190, pliki z 2026-11-11)

| miara | wartość |
|---|---:|
| identyfikatorów w mapie chińskiej / angielskiej | 1 818 900 / 1 124 787 |
| identyfikatorów w zakresie pakietu | 1 128 714 |
| **unikalnych tekstów w zakresie** | **483 190** |
| w tym bez wersji chińskiej (źródłem angielski) | 5 824 |
| identyfikatorów tylko chińskich, których nic nie wskazuje (pominięte) | 700 766 |
| dialogów (scen) / bez żadnego tekstu | 74 950 / 1 577 |
| kwestii / elementów scen razem | 186 025 / 187 330 |
| kwestii zależnych od płci bohatera | 1 860 |
| kwestii bez grupy mówcy | **0** |
| zadań / grup zadań / pytań z wyborami | 24 733 / 1 077 / 15 027 |
| identyfikatorów angielskich ze wskazanym źródłem (tabela lub scena) | 1 052 649 (93,59%) |

**Zakres.** Identyfikator jest „w grze”, jeśli ma wersję angielską albo
wskazuje go odczytana tabela lub dialog. 700 766 identyfikatorów istnieje tylko
w mapie chińskiej i nie wskazuje ich nic — klient zachodni nie ma dla nich
żadnego tekstu. To **hipoteza robocza** (teksty chińskiego wydania), nie
sprawdzona w grze; liczba jest w manifeście, żeby dało się do niej wrócić.

**Mówcy.** Kwestia leży w torze `EntityTextTrack` wewnątrz grupy
`EntityTrackGroup`, więc mówca wynika z budowy danych. Nazwa mówcy:
111 398 kwestii ma nazwę z gry (pole sceny albo tabliczka bytu), 37 407 to
gracz, 37 168 ma tylko roboczą etykietę twórców (`entity_tag`), 52 nic.

## Pakiet (`wwm-paczka-v1`)

```sh
python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_wwm_v1 --wersja 1 --data 2026-11-12
```

Wynik: `README.md`, `sceny/`, `widoki/`, `sceny.zip`, `widoki.zip`,
`paczka_dla_tlumacza_wwm_v1.zip` (trzy poprzednie w jednym pliku) i `paczka.json`
(manifest z liczbami, listą plików i wynikiem kontroli). Archiwa są
powtarzalne: ta sama zawartość daje ten sam SHA-256. Kopia `README.md`
i `paczka.json` każdej wysłanej wersji leży w `paczki/`.

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
python3 tools/zbuduj_latke.py --indeks index --magazyn tlumaczenie \
  --zh translate_words_map_zh_cn translate_words_map_zh_cn_diff \
  --cel translate_words_map_en --cel translate_words_map_en_diff \
  --wyj dist/latka
```

Gra nie ma języka polskiego, więc przekład **zastępuje teksty jednego
z języków klienta** — plików podanych w `--cel` (mapa podstawowa i każda
warstwa `_diff` osobno, bo klient nakłada je po kolei). Każdy plik jest po
zapisie czytany z powrotem i porównywany wpis po wpisie. Oryginały nie są
zmieniane, narzędzie niczego nie instaluje.

Próba na prawdziwych mapach w piaskownicy (sztuczne „przekłady” z prefiksem,
nie zapisane w repozytorium): 19 630 przekładów → 95 471 zmienionych wpisów
mapy angielskiej, 847 i 1 060 w dwóch warstwach `_diff`; po złożeniu warstw
zmienionych 96 019 z 1 124 787, zbiór identyfikatorów bez zmian; 23 s.

**Nie sprawdzono w grze:** czy klient przyjmie zmienione mapy (możliwa kontrola
plików przy starcie albo aktualizacji), czy czcionki mają polskie znaki, ile
tekstu mieszczą pola. Podmiana plików w instalacji wymaga osobnego planu, kopii
oryginałów i sprawdzonego przywracania ([AGENTS.md](../AGENTS.md)); nie ma
jeszcze skryptu instalacyjnego. Nie obiecujemy bezpieczeństwa konta.

## Aktualizacja gry — co robić krok po kroku

1. **Właściciel** po patchu gry wrzuca na Dysk katalog
   `LocalData/Patch/HD/oversea` (tak jak `patch.zip`: `MANIFEST`, `data1001`,
   `data1200`, `index1001`, `index1200`, `locale/*_diff`). Po dużej aktualizacji
   klienta także zmienione pliki z `Package/HD/oversea` (`MANIFEST`, `data*`,
   `index*`, `locale/translate_words_map_{zh_cn,en}` i ich `_diff`).
2. **Agent** pobiera pliki do `google_drive/`, wypakowuje do `local/`
   i przebudowuje wyciąg w katalogu roboczym (`tools/wyciag.py`, jak wyżej).
3. Audyt względem ostatniego commita:

   ```sh
   python3 tools/audyt_aktualizacji.py --stary-git HEAD --nowy index \
     --wyj dist/audyt --tlumaczenie tlumaczenie
   ```

   `AUDYT.md` mówi, ile jest nowych i usuniętych tekstów, które sceny są nowe
   albo zmienione i ile po aktualizacji brakuje przekładów.
4. Pakiet uzupełniający — tylko nowe teksty, w kontekście:

   ```sh
   python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_wwm_v2 --wersja 2 \
     --data RRRR-MM-DD --tylko-sloty dist/audyt/nowe_sloty.txt --tlumaczenie tlumaczenie
   ```

   Sceny z nową kwestią są pokazane w całości; stare kwestie mają
   `PL (już jest): …` albo znacznik „z wcześniejszego pakietu”.
5. Commit nowego `index/` (zmieniają się tylko wiersze, które się zmieniły —
   podział plików jest stały) i kopii `README.md` + `paczka.json` w `paczki/`.
6. Po zwrotce: import (jak wyżej), commit `tlumaczenie/`, nowa łatka na
   aktualnych mapach.

Sprawdzone na prawdziwych danych: wyciąg z samej paczki gry (bez
`LocalData/Patch`) porównany z pełnym — 387 nowych tekstów, 64 usunięte,
0 zmienionych scen; audyt 9 s; pakiet uzupełniający z 387 miejscami `PL:`.

## Co jest hipotezą, a co faktem

| twierdzenie | status |
|---|---|
| numer dialogu, mówca, kolejność kwestii w scenie | fakt z budowy danych, sprawdzony na wszystkich 74 950 dialogach |
| powiązanie sceny z zadaniem przez pola tabel zadań i wyborów | fakt z danych |
| kolejność zadań w grupie | łańcuch z danych; nie sprawdzona w grze |
| scena „według numeru” należy do sąsiedniego zadania | **hipoteza**, tak oznaczona w pakiecie |
| `valid_for_specific_type` + `entity_type` 1/2 toru = wariant bohatera/bohaterki | odczyt z danych (tory animacji `…_male` / `…_female`, różne teksty zwrotów); nie sprawdzony w grze |
| pominięte identyfikatory tylko chińskie nie są wyświetlane w kliencie zachodnim | **hipoteza** |
| tabele `__grey` to druga wersja tej samej tabeli | **hipoteza** z nazwy; ich teksty są w pakiecie |
| łatka działa w grze, polskie znaki się wyświetlają | **nie sprawdzono** |
