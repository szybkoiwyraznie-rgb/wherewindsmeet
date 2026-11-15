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
- **The Shimmer of South:** O niebiosa bez litości, czemu nie dacie mi umrzeć razem z tobą!

## Cutscena 30354
- ...

## Scena 10099
- **伶人师傅:** Nie powinieneś był przychodzić!
- **Ty:** Te wszystkie krwawe sprawy, setki dusz, które odeszły — one mnie tu prowadzą!
```

Zasady:

- **jedna kwestia = jedna linia**, bez odstępu między kwestiami; pusty wiersz
  oddziela tylko jednostki (scenę, cutscenę),
- **punktor tylko przy mówcy:** `- **Mówca:** tekst`. Kwestia bez jawnego mówcy
  idzie jako goły tekst (często to dalszy ciąg zdania łamanego na dwa wiersze),
  a **cutsceny nie mają punktora wcale** — nawet gdy mówca jest znany,
- **imię mówcy:** polskie, gdy jest w magazynie; inaczej angielskie (zlatynizowane)
  z danych gry, a dla etykiet zapisanych w grze tylko rolą — z ręcznego słownika
  `index/nazwy_mowcow.json` (219 haseł, rośnie z każdą sesją),
- **postać gracza to zawsze `Youxia`** — także gdy gra zapisze ją jako `player`,
  `main_player`, `mian_player` (literówka w danych) czy `player_1`;
  tory techniczne (`Entity轨道组` itp.) nie mają mówcy,
- **bez metadanych:** żadnych czasów, numerów klatek, kluczy technicznych ani
  tabel; numer zostaje tylko w nagłówku `## Scena N` / `## Cutscena N`, żeby
  dało się wrócić do gry,
- **kwestie bez przekładu widać:** idą z gwiazdką i tekstem z gry —
  `- **Mu Ji'an:** \*The illness will flare up next turn!` — żeby nie zginęły
  z czytanki; `--zakres przetlumaczone` daje plik tylko po polsku,
- **prolog jest przetłumaczony w całości:** brakujące 5 kluczy dopisałem do
  magazynu (`tlumaczenie/pl_1000_prolog_uzupelnienia.jsonl`), więc w prologu
  nie ma już ani jednej gwiazdki,
- **bez powtórzeń:** dwie identyczne kwestie pod rząd (ten sam klucz albo ta sama
  treść z dwóch wariantów) są sklejane w jedną — w danych gry ten sam tekst bywa
  wpisany dwa razy,
- **sceny bez mapy** mają własną sekcję, żeby nic nie wypadło.

## Liczby (2026-11-15)

- 75 287 jednostek w pliku 01 (8 910 scen z polskim dialogiem, 1 597 cutscen,
  reszta to sceny bez przekładu — teraz też są, z gwiazdką),
- 186 959 linii kwestii: 26 554 po polsku i 160 405 z gwiazdką (tekst z gry);
  180 459 linii ma mówcę i punktor, 6 500 to goły tekst (bez mówcy lub cutscena),
- 36 366 kwestii należy do gracza (`Youxia`),
- 9 319 kwestii ma jeszcze chińską etykietę mówcy (4 713 różnych) — to etykiety
  opisowe bez odpowiednika w danych gry; schodzą ze słownikiem `nazwy_mowcow.json`,
- mówcy: imię polskie lub angielskie z danych gry, postać gracza jako `Ty`,
  3 561 kwestii ma tylko imię chińskie (gra nie daje dla nich nazwy obcej),
- 3 pieśni (na końcu), 4 sekcje prologu, 38 sekcji krain,
- 73 296 jednostek ma kontekst w pliku 02; kontekst obejmuje też sceny bez
  polskiego dialogu, bo mówiący i hasła są niezależne od przekładu
  (574 hasła z pełną kartą, reszta to powtórzenia samego imienia),
- karty bez polskiego przekładu mają tekst z gry z gwiazdką, tak samo jak kwestie
  w pliku 01: `- **Wang Qing:** \*Wang Qing can still recall the argument...`
  (1 035 kart; biogramy encyklopedii są na razie po angielsku),
- 64 112 pozycji w pliku 03,
- archiwum: `dist/WWM_Czytanka_PL_2026-11-15.zip` (8 486 049 B).

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
