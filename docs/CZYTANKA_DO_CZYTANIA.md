# Czytanka do czytania (`tools/czytanka_czysta.py`)

Trzy pliki, po jednym na rodzaj treści — bez czasów mówienia, kluczy, tabel
i pustych linii między kwestiami. Kolejność bierze się z **jednego stałego pliku
w repo** (`index/chronologia.jsonl`), a nie z układania od nowa przy każdym
uruchomieniu.

| plik | zawartość | wiersze |
|---|---|---|
| `01_sceny_i_cutsceny.md` | filmy, prolog, potem krainy po kolei — sceny **i** cutsceny przemieszane w kolejności występowania w grze | 48 043 |
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

1. **filmy** otwierające 1–3,
2. **prolog** w kolejności transkryptu właściciela
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

- **jedna kwestia = jedna linia:** `- **Mówca:** tekst`, bez odstępu między
  kwestiami; pusty wiersz oddziela tylko jednostki (scenę, cutscenę),
- **imię mówcy:** polskie, gdy jest w magazynie; inaczej angielskie z danych gry;
  postać gracza to `Ty`, tory techniczne (`Entity轨道组` itp.) nie mają mówcy,
- **bez metadanych:** żadnych czasów, numerów klatek, kluczy technicznych ani
  tabel; numer zostaje tylko w nagłówku `## Scena N` / `## Cutscena N`, żeby
  dało się wrócić do gry,
- **tylko polski:** kwestie bez przekładu są pomijane (domyślnie). `--zakres wszystko`
  wstawia `[brak przekładu]`, gdy trzeba zobaczyć lukę,
- **sceny bez mapy** mają własną sekcję, żeby nic nie wypadło.

## Liczby (2026-11-15)

- 8 910 scen i 1 597 cutscen w pliku 01; 26 941 kwestii z polskim,
  161 817 kwestii bez przekładu pominięto (zakres domyślny),
- mówcy: imię polskie lub angielskie z danych gry, postać gracza jako `Ty`,
  3 561 kwestii ma tylko imię chińskie (gra nie daje dla nich nazwy obcej),
- 3 filmy, 4 sekcje prologu, 38 sekcji krain,
- 9 477 z 10 512 jednostek ma kontekst w pliku 02; 28 176 pozycji kontekstu
  (574 hasła z pełną kartą, reszta to powtórzenia samego imienia),
- karty bez polskiego przekładu są oznaczone `*(EN)*`: biogramy encyklopedii
  w magazynie są na razie po angielsku (54 karty polskie, 520 angielskich),
- 64 112 pozycji w pliku 03,
- archiwum: `dist/WWM_Czytanka_PL_2026-11-15.zip` (2 168 050 B).

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
