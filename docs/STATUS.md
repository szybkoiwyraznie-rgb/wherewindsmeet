# Stan projektu

Aktualizacja: **2026-11-18**. Punkt wejścia dla kolejnej sesji. Cel i kryteria
akceptacji: [CEL.md](CEL.md). Historia prób: [dziennik](EXPERIMENT_LOG.md).

**Najnowsze (v20, wpis 16 w dzienniku):** sekcja „Zadania i wątki” ma
nagłówki chronologii wyższego rzędu: `## Wątek główny — Rozdział pierwszy ·
Nieśmiertelni nie przypłyną` … `czwarty · Zwiastun żaru` oraz `## Wątek
poboczny — <nazwa łańcucha>` (236 nazwanych łańcuchów). `kolejnosc_zadan.plan()`
emituje bloki per grupa; `_sekcja_zadan` wciąga pod nagłówki też zadania bez
opisów (parametr `luzne`). Magazyn `pl_nazwy_hasel.jsonl`: **2 378 wpisów**
(+297 nazw grup/rozdziałów, +49 nazw zadań głównych). Testy: **614 OK**.

**Dane z gry na Dysku Google:** 8 części `WWM_AKTUALIZACJA_20261113_193108_9bdd6b3f_czesc1..8.zip`
(60 plików, `536 MB` po rozpakowaniu). Spis „co leży w której części” jest
w repozytorium: [PLIKI_W_PACZKACH.md](PLIKI_W_PACZKACH.md) + `index/paczki.json`
(generuje `tools/spis_paczek.py`). Pobieranie: narzędzie `google_drive`
`download_file` **zapisuje plik na dysk sandboxa** (`google_drive/…`, nie wkleja
treści do rozmowy) — innej drogi nie ma, bo sandbox nie ma sieci do Dysku
(`curl https://drive.google.com` → `000`, GitHub → `200`). Rozpakowanie:
`python3 tools/spis_paczek.py --rozpakuj local/dane` odtwarza ścieżki gry.

**Pamiątki (przedmioty z historią) są w czytance.** Gra trzyma je w tabelach
`curio_config` / `curio_owner` / `curio_theme` (+ `equip_items` na nazwę
i opis). `tools/pamiatki_z_bazy.py` zapisuje z nich **same liczby** do
`index/pamiatki.jsonl` (120 wierszy), a `czytanka_czysta._pamiatki()` dokłada
sekcję `# Pamiątki — przedmioty z historią` do `03`: **98 pamiątek** z tytułem
„właściciel — przedmiot” i całą opowieścią (przekład, a bez przekładu tekst
z gry z gwiazdką). 22 pamiątki nie mają w wyciągu nazwy przedmiotu — nie
wchodzą, licznik `pamiatki_bez_nazwy` w README czytanki mówi ile. Opowieści
pamiątek nie są przetłumaczone (0 ze 120), więc wszystkie idą z gwiazdką.

**Nazwy w grze są liczbami.** `equip_items.name`, `active_interact_way.button_name`,
`curio_owner.owner_name` to **identyfikatory tekstów**; treść leży w mapach języka
(`locale/translate_words_map_*`), a klucz przekładu to SHA-256 z tekstu źródłowego.
`tools/nazwy_z_map.py` zapisuje `index/nazwy.jsonl` (10 557 wpisów) — tylko
identyfikatory używane przez czytankę, z treścią i kluczem. To odblokowało nazwy.

**Pamiątki (przedmioty z historią).** Tabele `curio_config` / `curio_owner` /
`curio_theme` / `equip_items`; `tools/pamiatki_z_bazy.py` →
`index/pamiatki.jsonl`, sekcja `# Pamiątki — przedmioty z historią` w `03`:
**120 pamiątek, 0 bez nazwy**, tytuł „właściciel — przedmiot”
(„Jiang Wulang — Stara włócznia”) i cała opowieść. Opowieści nie są
przetłumaczone (0 ze 120), więc wszystkie idą z gwiazdką.

**Punkty na mapie (POI).** `tools/poi_z_bazy.py` → `index/poi.jsonl` (10 368
wierszy, 1 368 z numerem sceny), sekcja `# Punkty na mapie (POI)` w `03`:
**2 948 haseł**, z tego **368** z potwierdzonym numerem sceny, **11** bez nazwy
w mapach języka. „Dragon Pattern Mark” jest w `03` z gwiazdką (brak przekładu
klucza `b86a976ba200e189`) i bez numeru sceny — wiersz POI ma tylko ścieżkę
`client/dialogs/hjt/sxd_longwenbiaoji.etsb`.

**Kolejność kwestii w cutscenach: z danych gry, bez dyktowania (v9, 2026-11-14).**
Wersja v8 niosła kolejność przepisaną przez właściciela z ekranu
(`index/cutsceny_ekran.jsonl`) — właściciel ją odrzucił: dopisywanie listy do każdej
cutsceny zaprzecza idei czytanek. Plik usunięty, a porządek liczy się z samych danych;
w tym celu przeczytana została **baza gry** (`tools/baza_gry.py`, MANIFEST + `indexN` +
`dataN`, części 1, 4, 6, 7, 8 paczki): `text_msg` ma 126 538 wierszy w `data10`
i bliźniaczą tabelę `text_msg__grey` (126 541 wierszy w `data212`), a napisy cutscen
mają wyłącznie kolumny `content` i `id` — **żadnej osi czasu, żadnego numeru sceny**
i żadnego pola mówcy. Wiersze puli nie są też nigdzie indziej w bazie odwoływane
(przeszukane wszystkie chunki wszystkich `dataN`, jakie mamy: `591148` występuje tylko
w `text_msg` i `text_msg__grey`). Wniosek: kolejność da się odczytać tylko z układu
samej puli.
Reguła v9: bloki po odstępie numerów wierszy, **grany jest blok o najwyższych numerach**
(nowsza redakcja tej samej sceny — w 30161 591148–591169 przed 590153–590179); w bloku
głównym dialog to kwestie z bliźniakiem w innym bloku, a ciąg bez bliźniaka przed
pierwszym bliźniakiem (do 3 kwestii) należy jeszcze do dialogu. Efekt w 30161:
„Szefie! Szefie!”, „Wodzu, obudź się!”, „Miałaś iść ze mną do Kaplicy Generała!”,
„Jak można tak zasnąć?” — zgodnie z tym, co właściciel słyszał; recytacja poematu
o Ośmiu Wspaniałych stoi niżej, pod nagłówkiem wariantu. **To nadal nie jest kolejność
z ekranu** i wiadomo już, dlaczego: numer wiersza puli nie jest osią czasu gry. „Stój!” ma
numer 591170, czyli leży *po* całej rozmowie, choć w grze jest trzecią kwestią; nagrania
w `sound_data` mają numery tylko w obrębie mówcy (`…_zlxl_hx_01…17` Ruby,
`…_zlxl_pma_01…06` gracza) i nie mówią, jak serie się przeplatają. Osie czasu
przerywników są w plikach `.cine`, których paczka aktualizacji nie zawiera — dowody
i plan: `docs/CINE_KOLEJNOSC.md`.
**Streszczenie sceny stoi teraz na początku**, zaraz pod nagłówkiem (`### Streszczenie
sceny`). **Podpisy mówców tylko pewne:** podpowiedzi `mowca_en` z `text_msg` nie są już
używane (tak powstawało „Handlebar Hu” przy „Ech!” w Prologu 4), nazwy samych ról
(„审查士兵” → „Inspection Soldier”) i same okrzyki nie dostają podpisu.
Regresja: `tests/test_czytanka_kolejnosc_cutscen.py` (14 testów), całość 546 OK.
Paczki: `dist/WWM_Czytanka_PL_v9.zip`, **6 771 018 B**, SHA-256 `e0b4125e1f3d81f78c6592e2ae72896c6bd0eeea91f1fb042ebee00a4d31e84a`,
leży na Dysku (id `18y2NtKvl0Auv9HzjWlGJ1X8ET_Ez7QsI`); `v10` (2026-11-17,
**6 771 033 B**, SHA-256 `6796e1d7a09875ad34715f1114b8d907d48a3819fd3532cea52975f393dbb85d`,
id `10hgkAARQzpK2r8_2VyI9zCo-ZJtu2KG2`) to najnowsza — nowość względem v9: pusta
linia przerwy po `### Streszczenie sceny` (szczegóły w
[WERSJE_CZYTANKI.md](WERSJE_CZYTANKI.md)).

**Baza gry jest kompletna — wyłącznie na potrzeby inwestygacji (2026-11-14).**
Właściciel wgrał na Dysk brakujące binarki z `HD/oversea` i `patch/HD/oversea`
(`binarki/`: `data1`, `data204`–`data210`, `index*`, `MANIFEST`); leżą
w ignorowanym `google_drive/` i **nie są wejściem żadnego budowania**. Czytanka,
paczka dla tłumacza, łatka i instalator stoją wyłącznie na plikach z repo
(`index/`, `tlumaczenie/`, `zwrotki/`) — pilnuje tego
`tests/test_budowanie_standalone.py`, a zasadę zapisano w `ENVIRONMENT.md`.
Baza służy tylko narzędziom inwestygacyjnym (`tools/szukaj_w_bazie.py`,
`cutsceny_z_bazy.py`, `pamiatki_z_bazy.py`, `poi_z_bazy.py`).
Dzięki kompletnej bazie sprawdzenie „czy kolejność kwestii przerywnika jest
w danych” jest **pełne** i wynik jest negatywny: wiersz napisu `591148` stoi
tylko w `text_msg` i `text_msg__grey`, nagranie `7150686` tylko w `sound_data`,
żadna z **75 007** osi `dialog_timelines.*` nie dotyczy tego przerywnika, a żadna
tabela nie jest kluczowana numerem przerywnika. Kolejność jest w pliku osi
`.cine`, którego paczka nie zawiera — dowody i plan: `docs/CINE_KOLEJNOSC.md`,
narzędzie: `tools/szukaj_w_bazie.py`.

**E — decyzja właściciela (2026-11-14): dokładnej kolejności z ekranu nie
odtwarzamy.** Po domknięciu bazy (wyżej) sprawdzenie wyszło negatywnie, a wyjęcie
osi `.cine` z paczek `.mpk` (1 GB) uznajemy za nieopłacalne. Dlatego w v9 kwestie
przerywnika idą w kolejności **najnowszej redakcji napisów z danych** (nowszy blok
wierszy puli, grany przed starszym), a nie w kolejności z ekranu — i tak to jest
opisane, bez udawania. Dwie rzeczy z tej rozmowy są w v9 zrobione: **streszczenie
sceny stoi na górze**, zaraz pod numerem (`### Streszczenie sceny` — 2 267 cutscen,
sprawdzone wszystkie), a **niepewnych mówców nie drukujemy** (żadnych nazw ról,
samych okrzyków, żadnych podpowiedzi `mowca_en`; w całych cutscenach zostały
2 podpisy).

**D — decyzja właściciela (2026-11-14): zostawiamy, powiąże sceny sam.**
W repo został `collector/sniffer_mpk.ps1` (+ `SNIFFER_MPK.bat`, opis
`docs/SNIFFER_MPK.md`) jako opcja na później: sondowanie paczek `.mpk`
bez rozpakowywania i bez dotykania procesu gry (nagłówek i ogon, entropia,
magia kompresji, szukanie nazw ścieżek, okienka bajtów). Nie jest do niczego
wymagany — czytanka v6 stoi bez niego.

**Następstwo scen (D): częściowe, z danych `index/`.** Jawne następniki dialogów
(`branch_dialog_subsequent`, pole `x` sceny) istnieją dla 5 765 dialogów
(7 680 krawędzi); do tego wybory gracza, opcje NPC, koniec zadania → początek
następnego w łańcuchu `pre/post` oraz porządek ról wewnątrz zadania — razem
**16 946 krawędzi z oceną pewności** w `index/nastepstwa_scen.jsonl`
(generator `tools/nastepstwa_scen.py`, testy `tests/test_nastepstwa_scen.py`).
Ale przykładowy łańcuch `4700001 → 4700041 → 4700352` w tych danych **nie
występuje**: 4700001 nie ma `x`, a 4700041/4700352 nie są wskazywane przez
żadne zadanie (4700001 jest tylko `finish_dialogs` zadań 220003 i 10000220003).
Pełne następstwo nadal siedzi w plikach klienta `.etsb`, których nie zbieramy,
a POI → scena pozostaje otwarte (priorytet 2).

**Kwestie gracza z wariantem płci były po angielsku** w czytankach, choć przekład
jest w `tlumaczenie/pl_warianty.jsonl` — czytanka nie łączyła `id` wariantu
z kluczem tekstu (`index/warianty.jsonl`). Naprawione 2026-11-14 w
`tools/tlumaczenie.py` (`wczytaj(..., warianty=...)`); czytamy wariant bohatera.

Pięć braków zgłoszonych przez właściciela (angielskie kwestie w scenach,
brakujące przedmioty, brak POI, brak powiązań scena → scena, alfabetyczny
porządek questów w 03) ma plan i kolejność w
[ROADMAP_CZYTANKA_V6.md](ROADMAP_CZYTANKA_V6.md).

## Gdzie jesteśmy

**Wyciąg `index/` w repozytorium jest już zaktualizowany do Patcha 2.4
(`build 26592996`, dane z `2026-11-13`), do `tlumaczenie/` zaimportowano dwie
zwrotki tłumacza (`WWM_PL1.zip`: `75 685` przekładów = `15,46%` gry;
`WWM_PL2.zip`: `+9 443` klucze i `+244` warianty płci, magazyn `86 282` przekłady
= `17,7%` gry), a na Dysk
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

**W grze zweryfikowano dwie rzeczy:** (1) pierwszy mały test na poprzednim
buildzie `25906190` (`tools/latka_testowa.py` w trybie binarnym) — klient Steam
(Windows) przyjął przepisane mapy `translate_words_map_en*` w menu głównym,
ustawieniach oraz napisach otwierającego prologu, a czcionki gry wyświetliły
poprawnie wszystkie polskie znaki diakrytyczne (`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`);
(2) **pełną łatkę `WWM_Spolszczenie_PL_v0.4.0.zip` (opartą na najnowszej zwrotce
`WWM_PL2.zip`, `86 282` przekłady) — przetestowaną w grze na wersji gry 2.4;
działa: co jest przetłumaczone, pojawia się w grze** (zgłoszenie właściciela,
2026-11-17). **Dodatkowe elementy do tłumaczenia z wersji 2.4 zostały
wyciągnięte collectorem, dodane do najnowszego pakietu dla tłumacza i
przekazane do tłumaczenia.** Tłumacz pracuje nad dalszymi przekładami.

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
  tekstów gry) do `tlumaczenie/`. Z drugiej, najnowszej zwrotki (`WWM_PL2.zip`)
  zaimportowano **`+9 443` klucze i `+244` warianty płci** (`15` konfliktów
  nadpisanych na korzyść tłumacza; raport: `zwrotki/raport_scalenia_WWM_PL2.json`)
  — magazyn liczy **`86 282` przekłady** (`85 956` po kluczu + `326` wariantów
  płci = `17,7%` tekstów gry; pomiar `tools/pokrycie_tlumaczenia.py`,
  2026-11-17). Po aktualizacji `index/` do Patcha 2.4
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
- **Pokrycie przekładu (2026-11-17, po imporcie `WWM_PL2.zip`;
  `tools/pokrycie_tlumaczenia.py`):** magazyn ma `86 282` przekłady
  (`85 956` po kluczu + `326` warianty płci): napisy cutscen
  `text_msg 590000–592694` — `2 688`/`2 688` (`100%`), intro `9`/`9`, napisy
  filmowe `47`/`47` (w tym film 2 `钗头凤` `13`/`13` i film 3 `中渡桥之战`
  `21`/`21`), blok prologu `10094–10188` bez braków, sceny przerywników
  `2 225`/`11 678` (`19,1%`), zwykłe dialogi scen
  `25 627`/`187 598` (`13,7%`), cały wyciąg `86 098`/`487 684` (`17,7%`).
  Druga warstwa napisów
  (`text_msg__grey`, mówca wpisany w treść) ma `675`/`1 203` (`56,1%`) — brakujące wiersze
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
| Import zwrotki | Gotowy i zweryfikowany produkcyjnie na `WWM_PL1.zip` i `WWM_PL2.zip` (`tools/import_zwrotki.py`: `75 685` + `+9 443` klucze i `+244` warianty płci = magazyn `86 282` przekłady, `0` błędów formatu/tokenów, `21` kluczy odrzuconych z powodu usunięcia w Patchu 2.4). |
| Łatka i instalator Windows | **Domyślnie standalone (`tools/one_click_patch.py`, `tools/latka_testowa.py` → `tools/build_standalone_patcher.py` + `tools/patcher_wwm.py`):** buduje `WWM_LATKA_PL.zip` wyłącznie z `index/` i `tlumaczenie/` (czysty `plan_latki.json` + lokalny patcher z kopią oryginałów, zero binarek gry). Opcjonalny tryb binarny (`instalator/`) zachowany dla jawnych flag `--dane-gry`/`--mapa`. Mała łatka testowa (`latka_testowa.py` na `25906190`) **zweryfikowana w uruchomionej grze Steam**; **pełna łatka fabularna `WWM_Spolszczenie_PL_v0.4.0.zip` (zwrotka `WWM_PL2.zip`, `86 282` przekłady) przetestowana w grze — działa, przetłumaczone treści pojawiają się w grze** (zgłoszenie właściciela, 2026-11-17). |
| Aktualizacje gry | `collector/URUCHOM_AKTUALIZACJE.bat` (format `wwm-collection-v2`, przetestowany 8-częściowy zrzut 516 MB z Patcha 2.4), dzielenie paczek w `spakuj_dane.ps1`, `audyt_aktualizacji.py` i pakiet uzupełniający działają. |
| Pokrycie przekładu | `tools/pokrycie_tlumaczenia.py` mierzy z `index/` i `tlumaczenie/`, co w grze zostanie po angielsku: napisy cutscen `100%`, intro `100%`, napisy filmowe `100%` (film 2 i 3 też), prolog `100%`, sceny przerywników `19,1%`, zwykłe sceny `13,7%`, cały wyciąg `17,7%` (2026-11-17, po `WWM_PL2.zip`). Tryby `--brak`, `--brak-przerywnikow`, `--arkusz`, `--szukaj`; testy w `tests/test_pokrycie_tlumaczenia.py`; pomiar bez plików gry. |
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

1. ~~**Test w grze na Patchu 2.4 (`26592996`) i pełnej łatki**~~ — **zamknięte
   2026-11-17:** pełna łatka `WWM_Spolszczenie_PL_v0.4.0.zip` (najnowsza zwrotka
   `WWM_PL2.zip`, `86 282` przekłady) została przetestowana w grze i działa —
   przetłumaczone treści pojawiają się w grze (zgłoszenie właściciela). Wcześniej
   mała łatka UI + prolog (`latka_testowa.py`) potwierdziła na buildzie
   `25906190` przyjmowanie przepisanych map `translate_words_map_en*` i poprawne
   wyświetlanie wszystkich polskich znaków (`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`).
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
7. **Napisy kinowe — po teście `v0.4.0` w grze (2026-11-17): co jest przetłumaczone, pojawia się w grze.** Prolog
   (`10094–10188`), napisy `text_msg` i filmy 2–3 mają przekład po stronie
   `tlumaczenie/` i potwierdzono działanie pełnej łatki w grze (zgłoszenie
   właściciela). Nadal nie wiadomo, czy napisy filmów idą
   z `entry_collect_movie_subtitle_data`, czy z tych samych scen. Poza
   prologiem nadal `9 453` wierszy scen przerywników i `161 971` zwykłych
   kwestii czeka na przekład (`tools/pokrycie_tlumaczenia.py --arkusz`,
   pomiar 2026-11-17).
8. `21` pustych tabel rozmieszczeń `spaces.*` z Patcha 2.4 (`0x00`) jest bez
   tekstów i trafia do rejestru błędów w `index/manifest.json`.
9. Licencja własnego kodu i przekładu — nie wybrana, brak `LICENSE`.

## Następny krok

**ROADMAPA WYKONANA (2026-11-18, wpis 10 w EXPERIMENT_LOG): chronologia
tekstów W cutscenach — ZNALEZIONA.** Nośnik kolejności to ścieżka audio
głównego pliku `.cine` cutsceny (wpisy `czas:id_sound_data`), czytana przez
`tools/cine_sciezka_audio.py` z korpusu MPK_SKANER_WYNIK i tłumaczona na
wiersze puli `text_msg` przez `tools/cutsceny_kolejnosc_kwestii.py`
(benchmark 30161 — ręczny zapis gracza — odtworzony w 100%, 36/36 kwestii).
Czytanka od v15 renderuje cutsceny w tej kolejności (215 cutscen z pełnym
przeplotem). Czytanka od 2026-11-18 (wpis 13) ma dwa pliki treści: 01 sceny i cutsceny
+ 03 reszta (komplet informacji dodatkowych); plik 02 kontekst zlikwidowany
na życzenie właściciela. Dokończone 2026-11-18 (wpisy 11–12): tryb zapasowy pokrył 132 krótkie
cutsceny (indeks: 347 cutscen, 2 826 kwestii); czytanka podpisuje mówców
z nazw nagrań (gracz → Youxia, kody `_cs_`) z propagacją po plikach
nagrań w obrębie cutsceny (30161 podpisana w 100 %), a bloki puli bez
pokrycia treścią dostają nagłówek „Napisy sąsiadujące" zamiast „Inny
wariant".


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
   goły tekst. **Paczki numerujemy, nie datujemy:** najnowsza
   `dist/WWM_Czytanka_PL_v10.zip`
   (`6 771 033 B`, SHA-256
   `6796e1d7a09875ad34715f1114b8d907d48a3819fd3532cea52975f393dbb85d`),
   Dysk Google id `10hgkAARQzpK2r8_2VyI9zCo-ZJtu2KG2`, wgrana 2026-11-17 do
   folderu „Where Winds Meet” (wcześniejsza `v4`,
   id `1WzykudtneN3nrsjVMVxVxpU7vB-C2xT4`, pozostaje; v3 w koszu;
   wszystkie paczki z datą
   w nazwie są nieaktualne i leżą w koszu). Spis wersji:
   [WERSJE_CZYTANKI.md](WERSJE_CZYTANKI.md); `--wersja N` odmawia nadpisania
   istniejącej paczki. Opis formatu:
   [CZYTANKA_DO_CZYTANIA.md](CZYTANKA_DO_CZYTANIA.md).
   **Od 2026-11-17 (v10, na Dysku):** po `### Streszczenie sceny`
   stoi pusta linia przerwy przed kwestiami dialogu (`Jednostka.streszczenie`
   w `tools/czytanka_czysta.py`; 2 nowe testy, `tests/test_czytanka_kolejnosc_cutscen.py`).
   Sprawdzone przy okazji: otwierające cutsceny istnieją w danych jako numerowane
   cutsceny paczki xinshou — ze streszczeniem **tylko** 30147 (zasadzka na
   dziedzińcu; w 燕南) i 30150 (Król Bez Oblicza; w Prologu) — oba renderują się
   standardowo; 30032/30033/30151 nie mają streszczenia, a wiązania między
   transkryptem prologu a numerami cutscen w danych nie ma. **Decyzja
   właściciela: niczego nie zmieniamy** — prolog zostaje transkryptem
   (`## Prolog 1–4`), numerowane cutsceny stoją tam, gdzie wskazuje chronologia.
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
2. ~~Uruchomić w grze łatkę `v0.4.0` i sprawdzić prolog.~~ **Zrobione
   (2026-11-17):** pełna łatka `WWM_Spolszczenie_PL_v0.4.0.zip` (najnowsza
   zwrotka `WWM_PL2.zip`, `86 282` przekłady) została przetestowana w grze na
   wersji gry 2.4 i działa — przetłumaczone treści pojawiają się w grze
   (zgłoszenie właściciela). Przed każdą diagnozą „coś jest po angielsku” uruchomić
   `python3 tools/pokrycie_tlumaczenia.py` (`--brak`, `--brak-przerywnikow`,
   `--szukaj "<fragment zdania>"`).
3. Oczekiwać na kolejne zwrotki od tłumacza (pracuje nad dalszymi przekładami)
   → `tools/import_zwrotki.py` → commit `tlumaczenie/` → kolejne wydania
   Czytanek (`tools/buduj_czytanki.py`) i kolejne wydania `WWM_Spolszczenie_PL_v*.zip`.
4. Po każdym kolejnym patchu gry: właściciel klika
   `collector/URUCHOM_AKTUALIZACJE.bat`, następnie obieg z [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md).
5. **Odzyskanie trzech brakujących indeksów z `.mpk` (scena→scena, POI→scena,
   osie `.cine`) — bramki 0–1 wykonane 2026-11-17; kit v2 (wycinarka) na Dysku.**
   [ROADMAP_MPK_INDEKSY.md](ROADMAP_MPK_INDEKSY.md) /
   [MPK_SKANER_RAPORT.md](MPK_SKANER_RAPORT.md) /
   [MPK_FORMAT_RESEARCH.md](MPK_FORMAT_RESEARCH.md).
   Z raportu właściciela: **489 `*.mpk` (211 GB); `Resources.mpkinfo` =
   2 604 099 wpisów, offsety fizyczne wszędzie; trafień 14 × `.cine`
   (`e_01_cutscene/qhrw/...`) w `Resources34.mpk`; 0 trafień `.etsb`;
   `LT1.mpk` to paczka skryptowa; `Patch.mpkdb` = pełny spis łatki 2.4
   (854 wpisy)**. Z pierwszego przebiegu v2: wycięcie **14/14 `.cine`
   (106 800 B)** i **240/240 bloków LT1 (2 568 577 B)** zakończone OK; zrzut
   `Patch.mpkdb` padł na kolumnach BLOB (fix: hex). **Kit v3** na Dysku
   (folder „Where Winds Meet”, id `1lhq0Ic8S7mIpwf2Jx7Du7rraHtLhwacE`,
   SHA-256 `92a2f7d7fa8d46bcc94a241c6ebac6c38ec0fe8703ff76d5f32a51f2c4d9b2c8`):
   sonda + wycinanie surowych bloków + `mpkdb_dump.json` (BLOB→hex), tylko
   odczyt, zero sieci, bez instalowania bibliotek; v2 w koszu. Wynik u
   właściciela kompletny (14/14 `.cine`, 240/240 Lua LT1; SHA-256
   `ca183784…`). **Dekodowane po naszej stronie** (publiczny algorytm
   MIT): format `.cine` opisany; **reguła VFS `LuaText/` + debug_source
   potwierdzona 240/240**; nasz `file_id` zwalidowany na danych gry.
   Artefakty pochodne w `index/mpk/` (z opisem dla przyszłych agentów),
   surowe bajty poza Git. **Kit v4** na Dysku; wynik właściciela: 8 066
   kandydatów, 14 trafień wyłącznie `.cine` pack-34, 0 trafień POI-storyline.
   W Bramce 2.5 sprawdzono też 14 grafów Storyline: znaleziono most graf →
   dialog/cutscene ID oraz kotwice do łańcuchów zadań, ale nie POI → graf.
   Pochodne podsumowanie: `index/mpk/storyline_graphs.jsonl`; log:
   [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md), wpis (9). Bramka 3 (oś `.cine`,
   weryfikacja 30161) nadal otwarta.

## Handoff — WYNIK v7 przerobiony: reguła `Storyline/`, benchmark POI potwierdzony (2026-11-18)

- **Przebieg v7 właściciela odebrany i przetworzony** (8 części na Dysku,
  189,6 MB; 36 545 trafień sondy EZST + 3 113 trafień kandydatów, 0 błędów;
  wszystkie 39 888 bloków zdekodowane po stronie repo bez błędu).
- **Priorytet 2 — benchmark POTWIERDZONY:** odkryta reguła VFS
  `Storyline/<ścieżka>.etsb`; `Storyline/client/dialogs/hjt/
  sxd_longwenbiaoji.etsb` → graf grający `dialogs_no 4700001`
  (Dragon Pattern Mark → scena, wprost z danych). Rozwiązano 6 961
  skryptów → `index/mpk/etsb_storyline.jsonl`. Do pełnego POI→scena
  brakuje tylko kolumny POI→ścieżka skryptu z bazy gry (baza do
  ponownego pobrania do `local/` — sandbox ją czyści).
- **Priorytet 1 — duży skok:** `index/mpk/storyline_sceny.jsonl` — 8 948
  grafów, 5 121 unikalnych scen, **1 508 unikalnych krawędzi scena→scena**
  (było 13 z WYNIKv6) + przeplot 235 cutscena→scena / 182 scena→cutscena.
  Uczciwie: `4700041`/`4700352` nie występują w korpusie — łańcuch
  benchmarku nadal niepotwierdzony (korpus = tylko głowy bloków).
- **Priorytet 3 — połowa drogi:** `index/mpk/cine_ujecia.jsonl` — 978
  masterów `.cine` z uporządkowanymi 5 022 pod-ujęciami (benchmark 30161:
  17 ujęć w kolejności gry). Uczciwie: osie `.cine` NIE zawierają nazw
  nagrań ani napisów — kolejność kwestii nadal nie wynika wprost.
- **Dokończone w tej samej sesji (wpis 2026-11-18 (4)):**
  `poi_storyline_sceny.jsonl` — POI→scena przez skrypty (61 POI ze sceną,
  benchmark 200046001→4700001 w całości z danych; 75 nierozwiązanych →
  kandydaci do kitu v8) oraz `nastepstwa_scen.jsonl` — scalone krawędzie
  v6+v7 (1 744; 1 045 potwierdzonych oboma skanami).
- **Priorytet właściciela (2026-11-18): połączenia scen — DOWIEZIONE
  z grafu zadań** (wpis (5) w dzienniku): `tools/zadania_sceny.py` →
  `index/mpk/nastepstwa_zadania.jsonl` (8 997 krawędzi z tabeli `tasks`);
  kanoniczny `nastepstwa_scen.jsonl` ma po wpisie (6) **18 625 krawędzi
  z pięciu źródeł** (v6, v7, graf zadań, `branch_dialog_subsequent` —
  8 011 krawędzi, przebieg z gry — 3). Główny łańcuch od 4700001 bez
  dziur: `4700001 → 4700346 → 4700002 → 4700003 → 4700005 → … → [30162] →
  [30165] → 4700068`.
- **Mechanizm scen ambientowych rozpracowany (wpis (6)):** potwierdzony
  w grze ciąg `4700037 → (klik POI) → 4700001 → 4700041 → 4700352` ma
  wyjaśnienie w danych: sceny 4700037/4700041 to kity w świecie
  (`spaces.*.spawn_kit_sid_no`, kit_serial_id == numer sceny, drzewo
  `u_common_qifen`) przy POI 200046001; zadanie 3400017 spawnuje grupę
  1632220065 i (`new_npc_task_data`) wysyła NPC 15000023 (Ruby) do kitu
  4700041. Wyzwalacz riposty gracza 4700352 siedzi po stronie serwera
  (brak w danych klienta) — krawędź utrwalona jako źródło „gra".
  Nowy indeks `index/mpk/sceny_ambient_kity.jsonl` (53 601 wierszy): 43 877 scen
  ambientowych z pozycją XYZ — do grupowania czytanki wg miejsc.
- **Czytanka v12 DOWIEZIONA (wpis (7)):** chronologia liczona topologicznie
  z grafu następstw (łańcuchy scen w całości, cutsceny między swoimi scenami,
  pierwszeństwo krawędzi „gra"); benchmark właściciela stoi ciągiem;
  `dist/WWM_Czytanka_PL_v12.zip` na Dysku; v13 dodaje wiersz
  `Interakcja: <nazwa POI>` nad scenami wywoływanymi przez punkty na mapie
  (59 scen, wpis (8)).
- **Następny krok:** (a) uwagi właściciela do układu v12; (b) kolejność KWESTII wewnątrz sceny: osie
  `dialog_timelines.<scena>` istnieją w bazie (TimelinePObject z trackami
  per postać) — do przebadania; (c) kit v8: jawni kandydaci
  `Storyline/<ścieżka>` (75 POI + 519 `.etsb`/`.ets` + 32 `storyline_path`)
  + wyzwalacze 4700041/4700352 w `spaces.*`.
  Szczegóły: [dziennik](EXPERIMENT_LOG.md), wpisy 2026-11-18 (3)–(5).

## Handoff (nieaktualny) — skaner v7 na Dysku, czekał na przebieg właściciela (2026-11-18)

- **Priorytet 1 (scena → scena)**: `WYNIKv6` wyciągnął 1 066 krawędzi z nieskompresowanych grafów JSON w `Resources*.mpk` (`index/mpk/storyline_nastepstwa.jsonl`), ale **benchmark `4700001 → 4700041 → 4700352` ma w nich 0 trafień** — w czytankach `WWM_Czytanka_PL_v11.zip` układ dla tych scen nadal idzie po numerach.
- **Priorytet 2 (POI → scena)**: `index/mpk/poi_sceny.jsonl` ma 1 307 bezpośrednich powiązań z `poi.dialog`, ale **benchmark `Dragon Pattern Mark → 4700001` (`client/dialogs/hjt/sxd_longwenbiaoji.etsb`) ma 0 trafień** w `lt1_stringi.jsonl` i w `WYNIKv6`.
- **Priorytet 3 (kolejność kwestii w cutscenach)**: `index/mpk/cine_dekodowane.jsonl` ma tylko 14 sztuk z sondy `Resources34` (w grze jest ich kilkaset).
- **Przyczyna**: brakujące grafy, skrypty `.etsb` i osie `.cine` leżą w `Resources*.mpk` w blokach skompresowanych/zaszyfrowanych (`EZST`) oraz pod sygnaturą `.cine` (`c159410d`), których nieskompresowane wyszukiwanie JSON-ów nie widzi.
- **Zrobione w tej sesji (2026-11-18, druga część):** (a) `tools/sciezki_vfs.py`
  → `index/mpk/sciezki_vfs.jsonl` — **11 278 prawdziwych ścieżek VFS z bazy**
  (974 pełnych `.cine` z `cutscenes.cine_path` — wzorzec `qhrw` trafiał tylko 14,
  2 429 hashowalnych `.graph`, w tym `Char/graph/cutscene/*` z
  `fenbao_cutscene_info.cutscene_graph`, 804 `.etsb` z benchmarkiem
  `sxd_longwenbiaoji.etsb`); (b) **skaner v7** (`WWM_MPK_Skaner_v7.zip`,
  160 860 B, SHA-256 `81431bf2b46c7f678b1214104a3a47fc6c5e3d9cd11220a64cb071d1d529e338`,
  Dysk id `12X8MPOLISbOnEeeAy8i5yJiKRt1DPaZu`; kity v4–v6 w koszu):
  25 451 kandydatów z realnych ścieżek + **sonda zawartości bloków EZST**
  (AES-ECB prefiks w czystym Pythonie + początek ramki zstd, sygnatury
  `c159410d`/Storyline/`client/dialogs`/`4700001`; brakujący moduł zstd
  `SKANUJ.bat` doinstalowuje SAM — właściciel nie uruchamia nic ręcznie;
  bez niego sonda treści jest jawnie pomijana). Szczegóły i ograniczenia:
  [dziennik](EXPERIMENT_LOG.md), wpis 2026-11-18 (2).
- **Następny krok**: właściciel uruchamia `WWM_MPK_Skaner_v7.zip`
  (tylko dwuklik na `SKANUJ.bat`; skan może potrwać do ~1 h) i odsyła
  `WWM_MPK_Skaner_WYNIK.zip` na Dysk. Po wyniku:
  dekodowanie `ezst_*.bin` (`tools/mpk_artefakty.py`), mapowanie `.cine` →
  cutsceny po `sciezki_vfs.jsonl` (pole `cutsceny`), Bramka 3 (weryfikacja
  osi 30161) i grafy Storyline pod priorytety 1–2.
