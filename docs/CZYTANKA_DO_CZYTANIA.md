# Czytanka do czytania (`tools/czytanka_czysta.py`)

Trzy pliki, po jednym na rodzaj treści — bez czasów mówienia, kluczy, tabel
i pustych linii między kwestiami. Kolejność bierze się z **jednego stałego pliku
w repo** (`index/chronologia.jsonl`), a nie z układania od nowa przy każdym
uruchomieniu.

| plik | zawartość | wiersze |
|---|---|---|
| `01_sceny_i_cutsceny.md` | prolog, potem krainy po kolei — sceny **i** cutsceny przemieszane w kolejności występowania w grze; napisy przerywników i pieśni na końcu | 189 566 kwestii |
| `02_kontekst_scen_i_cutscen.md` | kontekst do tych samych jednostek w **tej samej** kolejności: kto mówi, postacie z encyklopedii, frakcje, miejsca, przedmioty, sztuki walki | 601 pozycji w 502 jednostkach |
| `03_reszta.md` | wszystko, czego nie ma w 01 ani w 02, pogrupowane według rodzaju danych | 59 624 |

## Chronologia (`tools/chronologia.py` → `index/chronologia.jsonl`)

Kolejność jest **raz policzona i zapisana w gicie**; czytanka tylko ją czyta.
Regeneruje się ją jedną komendą, a test `tests/test_chronologia.py` pilnuje,
żeby zapisany plik zgadzał się z danymi z `index/`:

```bash
python3 tools/chronologia.py            # zapisz index/chronologia.jsonl
python3 tools/chronologia.py --sprawdz  # porównaj zapisane z danymi (kod 1 = trzeba przegenerować)
```

Zasady kolejności:

1. **pieśni i filmy** (1–3) — na **końcu**, bo w grze nie ma ich na początku,
2. **prolog** w kolejności transkryptu właściciela (sekcje numerowane
   `Prolog 1…4`; komentarze z transkryptu to notatki dla nas, nie nazwy scen)
   (`zwrotki/prolog_transkrypt_z_gry.txt`, w repo) — napisy i dialogi przemieszane,
3. **krainy** w kolejności odwiedzania (`index/prowincje.json`); w krainie **sceny
   w porządku grafu następstw** (`index/mpk/nastepstwa_scen.jsonl` — POI→scena,
   graf zadań, `branch_dialog_subsequent`, przebieg z gry): łańcuch połączonych
   scen stoi w całości, scena po scenie, tak jak widzi go gracz (benchmark:
   `4700037 → 4700001 → 4700041 → 4700352 → 4700002 → …`); sceny bez krawędzi
   stoją między łańcuchami po numerze dialogu; cutsceny znane grafowi stoją
   **dokładnie między swoimi scenami** (`4700385 → cutscena 30162 → 30165 →
   4700068`), a kotwica grupy zadań działa dopiero dla pozostałych,
4. **cutsceny przypisane do grupy zadań** stoją przy scenie, od której ich grupa
   się zaczyna (tabela powtórek daje `no` przerywnika → `grupa`, a grupa ma
   zakres numerów dialogów). Kotwicą jest **pierwsza scena grupy z przypisaną
   mapą** — pierwsze sceny rozdziału pierwszego pochodzą z `luwenxin.dialog`,
   który w wyciągu nie ma map, i wcześniej cała grupa trafiała do sekcji
   „Sceny bez przypisanej mapy”. W obrębie kotwicy cutsceny stoją w kolejności
   **zadań** (`index/zadania.jsonl`, pole `przerywniki`, pozycja w grupie),
   a nie w kolejności własnych numerów,
5. **cutsceny bez grupy** stoją na końcu, w kolejności własnych numerów, w sekcji
   `# Cutsceny bez grupy zadań` — nie udajemy, że znamy ich miejsce,
6. **napisy przerywników** (pula `text_msg`, 2 688 wierszy) nie leżą już w 03.
   Napis w danych gry **nie ma numeru cutsceny** — ma tylko identyfikator wiersza
   i czasem nazwę nagrania (`vo_sm_sxdm4_cs_zlxl_hx_07`). Sprawdzone na pakiecie
   aktualizacji z 2026-11-13: osie czasu cutscen nie są w nim w ogóle, a osie
   czasu dialogów (`dialog_timelines.*`) nie zawierają ani jednego napisu puli.
   Dlatego:
   * napis, którego nagranie niesie **kod filmu** (`cs_zlxl_` ↔ `cutscenes.cine_name`
     `sq001_zlxl`), dostaje numer cutsceny i stoi w niej (pole `kn`, przed
     streszczeniem); takich napisów jest 5 — 4 w `## Cutscena 30161` (scena
     przebudzenia z Ruby, „Wodzu, obudź się!”), 1 w `## Cutscena 30707`
     (`index/cutsceny_napisy.jsonl`, dowód w polu `dowod`),
   * blok rozpoznany po sprawdzonej kotwicy (`kontekst_cutscen.KOTWICE_SCEN_TM`)
     albo po prefiksie nagrania (`VO_DOMENY`) trafia do cutsceny tak jak dotąd,
   * pozostałe bloki stoją w sekcji `# Napisy przerywników — kolejność z pliku gry`,
     w kolejności wierszy, a nie alfabetycznie.
   * **kolejność kwestii w cutscenie bierze się z numeru wiersza puli `text_msg`**
     (`index/cutsceny_kontekst.jsonl`, wiersze typu `napis`), a nie z pola `kn`
     w chronologii — to pole miesza napisy przypisane wprost z tabeli gry i bloki
     puli, więc kwestie stawały w kolejności losowej (w `## Cutscena 30161`
     „Jaki człowiek w czerni?” stało przed „Wstawaj! Wstawaj no!”).
   * gdy w plikach gry leżą **dwa zestawy napisów tej samej cutsceny** (np. wiersze
     590153–590179 i 591125–591169 w cutscenie 30161, ta sama scena w dwóch
     wersjach), pierwszy zestaw jest treścią sceny, a pozostałe stoją pod
     `### Inny wariant napisów tej cutsceny (wiersze …)`; kwestie powtórzone
     w obu wariantach wypadają, więc nic nie czyta się dwa razy.
   * **streszczenie sceny** stoi zawsze na początku cutsceny, zaraz pod jej
     nagłówkiem — a po nim **pusta linia przerwy** przed kwestiami dialogu
     (od 2026-11-17; wcześniej kwestie szły od razu po streszczeniu).
   * **kolejność z ekranu gry** nie jest odtwarzana: pliki gry nie mają osi czasu
     cutscen (sprawdzone w `tools/cutsceny_z_bazy.py` — osie `.cine` nie są
     w pakiecie, a `dialog_timelines.*` nie zawierają ani jednego napisu puli).
     `index/cutsceny_ekran.jsonl` (przepisaną z ekranu kolejność) **usunięto**
     decyzją właściciela 2026-11-14 — sceną rządzi najnowsza redakcja napisów
     z danych (patrz `docs/WERSJE_CZYTANKI.md`, v9).
7. **kraina cutsceny** bierze się najpierw ze sceny-kotwicy, a gdy ta nie ma mapy —
   z **własnej przestrzeni cutsceny** (`cutscenes.cutscene_space_no` →
   `index/cutsceny_meta.jsonl` → `index/prowincje.json`). Dzięki temu 100 z 101
   cutscen wcześniej odłożonych do „Scen bez przypisanej mapy” stoi w swojej
   krainie (燕南 194 → 218, 河西 16 → 55, 不见 6 → 20 i mniejsze).

8. **zadania w 03 idą kolejnością gry, nie alfabetem** — sekcja `# Zadania i wątki`
   dzieli się na `## Wątek główny`, `## Wątki poboczne (łańcuchy)`, bloki
   `## Zadania pojedyncze — <kraina>` i na końcu `## Pozostałe zadania i wątki`.
   Kolejność liczy `tools/kolejnosc_zadan.py` z tego samego układu, który dostaje
   pakiet dla tłumacza (`tools/uklad_scen.py`): typ zadania (wątek główny
   pierwszy), grupa rozdziału po `kolejnosc` z `index/grupy_zadan.jsonl`,
   a w grupie łańcuch `pre`/`post` z tabeli zadań. Pojedyncze zadania bez
   łańcucha stoją osobno, pogrupowane krainą w kolejności odwiedzania
   (`index/prowincje.json`). Hasła z tej sekcji, których nie da się przypisać do
   żadnego zadania (np. kwestie z `debate_guider_dialog_data`), zostają na końcu
   sekcji, alfabetycznie — nic nie wypada, ale nie udają questów.

9. **zbiory i pamiątki** mają w 03 własne sekcje (`# Zbiory i pamiątki —
   zasłyszane historie`, `# Zbiory i pamiątki — karty przeciwników`): para
   „tytuł + pełny tekst” z jednego wiersza gry, także bez przekładu (wtedy
   z gwiazdką). Wcześniej wchodził sam tekst bez tytułu, a bez przekładu — wcale.
   Pamiątki (przedmioty z historią) stoją w sekcji `# Pamiątki — przedmioty
   z historią`: tytuł „właściciel — przedmiot” (`**Jiang Wulang — Stara
   włócznia**`) i cała opowieść z gry pod spodem. Właściciel bez przekładu idzie
   z identyfikatora ikony z danych gry (`head_npc_…_jiangwulang`), nie
   z domysłu; pamiątka bez nazwy przedmiotu nie wchodzi i jest policzona
   w README (`pamiatki_bez_nazwy`). Nazwy biorą się z `index/nazwy.jsonl`
   (identyfikator tekstu → treść i klucz przekładu), a nie z domysłu po
   identyfikatorze wiersza.
10. **punkty na mapie (POI)** mają w 03 sekcję `# Punkty na mapie (POI)`:
   `**Nazwa** — scena N` **tylko wtedy**, gdy gra zapisała numer sceny
   w wierszu POI (`play_dialog_no` / `result_play_dialog`). Sama ścieżka
   scenariusza (`interact_storyline`, np. `…/sxd_longwenbiaoji.etsb`) nie jest
   powiązaniem — POI stoi wtedy bez numeru. POI bez nazwy w wyciągu nie wchodzi,
   a licznik `poi_bez_nazwy` w README mówi, ile ich było.
11. **kwestie zależne od płci bohatera** mają przekład pod osobnym
   identyfikatorem (`@id`), a nie pod kluczem tekstu. Czytanka czyta
   **wariant bohatera** (mężczyzna — decyzja właściciela), a gdy rodzina go nie
   ma, bierze drugi dostępny wariant. Bez tego cała kwestia gracza z wariantem
   wychodziła po angielsku mimo gotowego przekładu.

Plik ma po jednym JSON-ie na linię: `{"p": pozycja, "t": rodzaj, "n": numer,
"s": sekcja, "k": [klucze tekstów], "g": grupa}`. 75 748 jednostek, 4,2 MB.

## Format

```markdown
# 燕南 — Mapa Yannan

## Scena 10094
**The Shimmer of South:** O niebiosa bez litości, czemu nie dacie mi umrzeć razem z tobą!

## Cutscena 30354
Duch Jelenia prowadzi cię do jaskini…

## Scena 10099
**Ling Ren Shi Fu:** Nie powinieneś był przychodzić!
**Youxia:** Te wszystkie krwawe sprawy, setki dusz, które odeszły — one mnie tu prowadzą!
```

Zasady:

- **jedna kwestia = jedna linia**, bez odstępu między kwestiami; pusty wiersz
  oddziela tylko jednostki (scenę, cutscenę),
- **bez punktora w ogóle — w każdym pliku:** kwestia to `**Mówca:** tekst`,
  a gdy mówcy nie ma — goły tekst. Ten sam układ w 02 (hasła) i 03 (reszta):
  `**Nazwa:** opis`. Punktor nic nie wnosił, a przy łamanych zdaniach mylił,
- **imię mówcy:** polskie, gdy jest w magazynie; inaczej angielskie (zlatynizowane)
  z danych gry, a dla etykiet zapisanych w grze tylko rolą — z ręcznego słownika
  `index/nazwy_mowcow.json` (219 haseł, rośnie z każdą sesją),
- **etykiety tylko po chińsku są transliterowane:** `大祭师` → `Da Ji Shi`,
  `卫兵1` → `Wei Bing 1`, `兰澳（少女）` → `Lan Ao (Shao Nv)`. Tabela znaków leży
  w `index/pinyin_znakow.json` (3 156 znaków), więc przebudowa nie potrzebuje
  żadnej biblioteki; odświeża ją `python3 tools/pinyin_slownik.py --pisz
  index/pinyin_znakow.json`. To transliteracja, nie przekład — gra nie daje dla
  tych etykiet nazwy obcej. Skąd to się bierze (sprawdzone w `index/`):
  w danych gry obsada scen ma **59 884** wpisy z kluczem nazwy i **wszystkie**
  mają angielską wersję (brakuje 0), a **53 184** wpisy mają tylko chińską
  etykietę roboczą (`大祭师`, `卫兵1`), bo tabliczkę z nazwą (`entity_init_data`)
  ma w wyciągu zaledwie **32%** bytów. Przykład: scena `12000946` (束罪) ma
  piętnaście linii po angielsku, a mówca stoi tam jako `['大祭师', 3, 1633540005]`
  — bez klucza nazwy i bez tabliczki, więc gra nie ma czego przetłumaczyć.
  Po dodaniu ścieżki „byt → `spaces.*.entity.N.name`” część tych imion wraca
  z danych po angielsku (66 bytów); reszta, 4 713 etykiet i 5% kwestii, to
  transliteracja,
- **samo id to nie mówca:** etykiety typu `600001`/`1632390111` nie trafiają do
  czytanki, kwestia zostaje jako goły tekst,
- **postać gracza to zawsze `Youxia`** — także gdy gra zapisze ją jako `player`,
  `main_player`, `mian_player` (literówka w danych) czy `player_1`;
  tory techniczne (`Entity轨道组` itp.) nie mają mówcy,
- **bez metadanych:** żadnych czasów, numerów klatek, kluczy technicznych ani
  tabel; numer zostaje tylko w nagłówku `## Scena N` / `## Cutscena N`, żeby
  dało się wrócić do gry,
- **kwestie bez przekładu widać:** idą z gwiazdką i tekstem z gry —
  `**Mu Ji'an:** \*The illness will flare up next turn!` — żeby nie zginęły
  z czytanki; `--zakres przetlumaczone` daje plik tylko po polsku,
- **prolog jest przetłumaczony w całości:** brakujące 5 kluczy dopisałem do
  magazynu (`tlumaczenie/pl_1000_prolog_uzupelnienia.jsonl`), więc w prologu
  nie ma już ani jednej gwiazdki,
- **bez powtórzeń:** dwie identyczne kwestie pod rząd (ten sam klucz albo ta sama
  treść z dwóch wariantów) są sklejane w jedną — w danych gry ten sam tekst bywa
  wpisany dwa razy,
- **sceny bez mapy** mają własną sekcję, żeby nic nie wypadło,
- **streszczenie cutsceny jest treścią cutsceny, nie osobnym dodatkiem.**
  W transkrypcie prologu (źródle kolejności prologu, `zwrotki/`) między kwestiami
  stoi linia, która nie jest kwestią, tylko streszczeniem przerywnika
  (`cutscenes.synopsis_text_mobile`). Taka linia zamienia się w jednostkę
  `## Cutscena N` dokładnie w tym miejscu — dlatego „Robak przelatuje i wnika
  w zwłoki…” stoi między `## Prolog 3` i `## Prolog 4`, a nie w sekcji
  „Sceny bez przypisanej mapy”. Ten numer cutsceny jest potem pomijany przy
  rozmieszczaniu cutscen w krainach, żeby nic nie stało dwa razy,
- **tabliczka krainy nie jest kwestią:** linia z `cutscene_text_oversea`
  („QINGHE - VERDANT WILDS”) otwiera nową sekcję prologu, a nie linię dialogu.

Zasady pliku 02 (kontekst):

- **tylko hasła, które gra naprawdę opisuje.** Nazwa bez opisu to za mało —
  takie hasła zostają w pliku 03, a jednostka, w której nie ma nic do pokazania,
  nie dostaje nagłówka w 02. Dzięki temu 02 to kontekst, a nie lista imion
  (wcześniej 91 tys. kart z samą nazwą, m.in. `**玩家**`, `**0**`,
  `**Entity轨道组**` — wycięte),
- **opis to definicja, nie opowieść.** Bierzemy kolumny opisowe z danych gry:
  `describe`, `describe_str`, `introduction`, `description`, `npc_desc`,
  `job_info` — czyli przedmioty, frakcje, miejsca, sztuki walki, opisy NPC.
  Świadomie **nie** bierzemy `content`, `talk_content`, `page_*`, `story_*`,
  `tips`, `jianwen_text` — to dialogi, księgi, mails i streszczenia cudzych opowieści,
- **postać dostaje krótką tożsamość z encyklopedii** (`tozsamosc`), np.
  „Chen Zixi: Master of the Vernal Hall”, „Jiang Wulang: The Traitor”.
  Rozdziałów fabularnych encyklopedii (`historie`) **nie pokazujemy** — to
  streszczenia scen, nie opisy postaci; zostają w pliku 03,
- **hasło pojawia się raz.** Powtórki nie wchodzą w ogóle (wcześniej było przy
  nich samo imię — puste imię bez treści to szum),
- **opis dłuższy niż 600 znaków jest ucinany wielokropkiem**; pełny tekst zostaje
  w pliku 03,
- **karta bez polskiego przekładu ma gwiazdkę** i tekst z gry, tak samo jak
  kwestie w 01.

## Liczby (2026-11-15, po wycięciu haseł bez opisu)

- 75 287 jednostek w pliku 01 (8 910 scen z polskim dialogiem, 1 597 cutscen,
  reszta to sceny bez przekładu — teraz też są, z gwiazdką),
- 186 961 linii kwestii: 26 554 po polsku i 160 407 z gwiazdką (tekst z gry);
  180 375 linii ma mówcę (`**Mówca:** tekst`), 6 586 to goły tekst bez mówcy,
- 36 266 kwestii należy do gracza (`Youxia`),
- **0 kwestii z chińską etykietą mówcy** i 0 z samym numerem; 4 713 etykiet
  chińskich przeszło na łacinkę (tabela 3 156 znaków),
- 3 pieśni (na końcu), 4 sekcje prologu, 38 sekcji krain,
- **501 jednostek ma kontekst w pliku 02** — tylko te, w których jest co pokazać,
  i tylko z prawdziwym opisem (178 kart, każda raz). Reszta haseł (65 420 pozycji)
  jest w pliku 03, bo gra nie daje im definicji — m.in. Jiang Yan (`江晏`),
  Nefryt Zhenguan (`镇冠珏`), Hojna Wiosna (`丰厚醇`), Dawne Przymierze Yanbei
  (`燕北旧盟`), a także rozdziały fabularne encyklopedii,
- 704 karty bez polskiego przekładu mają tekst z gry z gwiazdką (biogramy
  encyklopedii są na razie po angielsku), 805 kart nie ma nazwy w danych —
  to opisy bez nazwy, więc idą gołym tekstem,
- 61 905 pozycji w pliku 03,
- archiwum: `dist/WWM_Czytanka_PL_v2.zip` (6 607 212 B,
  SHA-256 `06eb1d2ad973e6924e9fd524bc0b5d56ce9e9cc6cfce1d448cc1f08c95c350a6`).
  Wersje numerujemy (`v1`, `v2`, `v3`…), nie datujemy — spis:
  [WERSJE_CZYTANKI.md](WERSJE_CZYTANKI.md), a `--wersja N` nie pozwala
  nadpisać istniejącej paczki.

## Uruchomienie

```bash
python3 tools/czytanka_czysta.py --wyj out/czytanka \
    --zip dist/WWM_Czytanka_PL_2026-11-15.zip
```

Wszystko, co potrzebne, jest w gicie: `index/`, `tlumaczenie/` i transkrypt
prologu w `zwrotki/`. Żadnych binariów gry ani plików z Dysku Google.

## Jak powstaje kontekst (02)

Dla każdej jednostki z pliku 01 zbierane jest to samo, co widać w scenie:

- **kto mówi** — obsada sceny z `index/sceny_*.jsonl`; imię z tabeli postaci,
  a gdy postaci nie ma w tabeli, imię z obsady; biogram z encyklopedii, jeśli jest,
- **hasła z tekstu** — nazwy z tabel kontekstowych (`world_view_person_info`,
  `school`, `equip_items`, `kongfu`, `task_*`, `manual_items`…), dopasowane
  automatem Aho-Corasick po tekście chińskim, z filtrem nazw pospolitych,
- **pełna karta przy pierwszym wystąpieniu**, przy kolejnych samo imię albo nazwa —
  dzięki temu widać, kto i co wraca w danej scenie, bez powtarzania biogramów.

## Czym to się różni od zestawu technicznego

`tools/zbuduj_czytanke_pelna.py` (trzy warstwy: chronologia, fabuła, kontekst)
i `tools/buduj_czytanke_gry.py` (sceny w tabelach z chińskim i angielskim)
zostają jako narzędzia robocze do weryfikacji i audytu — ale **nie są czytanką
dla właściciela**. Czytanka to trzy pliki opisane wyżej.
