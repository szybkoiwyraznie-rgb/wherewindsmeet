# Czytanka do czytania (`tools/czytanka_czysta.py`)

Trzy pliki, po jednym na rodzaj treści — bez czasów mówienia, kluczy, tabel
i pustych linii między kwestiami. Kolejność bierze się z **jednego stałego pliku
w repo** (`index/chronologia.jsonl`), a nie z układania od nowa przy każdym
uruchomieniu.

| plik | zawartość | wiersze |
|---|---|---|
| `01_sceny_i_cutsceny.md` | prolog, potem krainy po kolei — sceny **i** cutsceny przemieszane w kolejności występowania w grze; pieśni na końcu | 186 959 kwestii |
| `02_kontekst_scen_i_cutscen.md` | kontekst do tych samych jednostek w **tej samej** kolejności: kto mówi, postacie z encyklopedii, frakcje, miejsca, przedmioty, sztuki walki | 29 892 |
| `03_reszta.md` | wszystko, czego nie ma w 01 ani w 02, pogrupowane według rodzaju danych | 62 012 |

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
3. **krainy** w kolejności odwiedzania (`index/prowincje.json`), w krainie **sceny
   po numerze dialogu**,
4. **cutsceny przypisane do grupy zadań** stoją przy scenie, od której ich grupa
   się zaczyna (tabela powtórek daje `no` przerywnika → `grupa`, a grupa ma
   zakres numerów dialogów). Dzięki temu przerywniki są przemieszane ze scenami,
   choć same nie mają numeru dialogu,
5. **cutsceny bez grupy** stoją na końcu, w kolejności własnych numerów, w sekcji
   `# Cutsceny bez grupy zadań` — nie udajemy, że znamy ich miejsce.

Plik ma po jednym JSON-ie na linię: `{"p": pozycja, "t": rodzaj, "n": numer,
"s": sekcja, "k": [klucze tekstów], "g": grupa}`. 75 704 jednostki, 4,1 MB.

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
- **sceny bez mapy** mają własną sekcję, żeby nic nie wypadło.

Zasady pliku 02 (kontekst):

- **tylko hasła, które gra naprawdę opisuje.** Nazwa bez opisu to za mało —
  takie hasła zostają w pliku 03, a jednostka, w której nie ma nic do pokazania,
  nie dostaje nagłówka w 02. Dzięki temu 02 to kontekst, a nie lista imion
  (wcześniej 91 tys. kart z samą nazwą, m.in. `**玩家**`, `**0**`,
  `**Entity轨道组**` — wycięte),
- **pełna karta przy pierwszym wystąpieniu**, przy kolejnych samo imię albo nazwa,
- **opis dłuższy niż 600 znaków jest ucinany wielokropkiem**; pełny tekst zostaje
  w pliku 03, żeby angielskie biogramy nie zalewały kontekstu,
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
- **8 891 jednostek ma kontekst w pliku 02** — tylko te, w których jest co
  pokazać: 749 haseł z opisem (pełna karta raz, potem samo imię). Reszta haseł
  (65 351 pozycji) jest w pliku 03, bo gra nie daje im żadnego opisu — m.in.
  Jiang Yan (`江晏`), Nefryt Zhenguan (`镇冠珏`), Hojna Wiosna (`丰厚醇`),
  Dawne Przymierze Yanbei (`燕北旧盟`),
- 704 karty bez polskiego przekładu mają tekst z gry z gwiazdką (biogramy
  encyklopedii są na razie po angielsku), 805 kart nie ma nazwy w danych —
  to opisy bez nazwy, więc idą gołym tekstem,
- 61 905 pozycji w pliku 03,
- archiwum: `dist/WWM_Czytanka_PL_2026-11-15.zip` (6 775 019 B,
  SHA-256 `643de95347cf25bba48bea8227606625dee80eed3fe397e11b8c913ccf90f937`).

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
