# Czytanka do czytania (`tools/czytanka_czysta.py`)

Trzy pliki, po jednym na rodzaj treści — bez czasów mówienia, kluczy, tabel
i pustych linii między kwestiami. To jest ta wersja, którą czyta się jak książkę.

| plik | zawartość | rozmiar |
|---|---|---|
| `01_sceny.md` | dialogi scen: prolog, potem krainy w kolejności odwiedzania, w krainie po numerze dialogu | 2,2 MB |
| `02_cutsceny.md` | filmy otwierające i napisy przerywników, w kolejności odtwarzania | 145 kB |
| `03_reszta.md` | przedmioty, sztuki walki, encyklopedia, postacie, zadania, reszta — „nazwa — opis” | 2,4 MB |

## Format

```markdown
# 燕南

# Prolog

## Scena 10094
- **The Shimmer of South:** O niebiosa bez litości, czemu nie dacie mi umrzeć razem z tobą!

## Scena 10099
- **伶人师傅:** Nie powinieneś był przychodzić!
- **Ty:** Te wszystkie krwawe sprawy, setki dusz, które odeszły — one mnie tu prowadzą!
```

Zasady:

- **jedna kwestia = jedna linia:** `- **Mówca:** tekst`, bez odstępu między
  kwestiami; pusty wiersz oddziela tylko sceny,
- **imię mówcy:** polskie, gdy jest w magazynie; inaczej angielskie z danych gry;
  postać gracza to `Ty`,
- **bez metadanych:** żadnych czasów, numerów klatek, kluczy technicznych ani
  tabel; numer zostaje tylko w nagłówku `## Scena N`, żeby dało się wrócić do gry,
- **tylko polski:** kwestie bez przekładu są pomijane (domyślnie). `--zakres wszystko`
  wstawia `[brak przekładu]` i tekst źródłowy, gdy trzeba zobaczyć lukę,
- **sceny bez mapy** mają na końcu własną sekcję, żeby nic nie wypadło.

## Liczby (2026-11-14)

- 8 908 scen, 92 216 kwestii z polskim; 263 076 kwestii bez przekładu pominięto,
- 25 219 linii dialogu; mówcy: 21 357 z imieniem polskim lub angielskim
  (postać gracza jako `Ty`), 3 561 z imieniem chińskim — gra nie ma dla nich
  nazwy obcej w danych, więc zostaje zapis źródłowy,
- 3 filmy, napisy przerywników w blokach `## Cutscena A–B`,
- 03_reszta: przedmioty i stroje, sztuki walki, encyklopedia, postacie, zadania,
  świat i sekty, walka, interfejs, pozostałe.

## Uruchomienie

```bash
python3 tools/czytanka_czysta.py --wyj out/czytanka \
    --zip dist/WWM_Czytanka_PL_2026-11-14.zip
```

## Czym to się różni od zestawu technicznego

`tools/zbuduj_czytanke_pelna.py` (trzy warstwy: chronologia, fabuła, kontekst)
i `tools/buduj_czytanke_gry.py` (sceny w tabelach z chińskim i angielskim)
zostają jako narzędzia robocze do weryfikacji i audytu — ale **nie są czytanką
dla właściciela**. Czytanka to trzy pliki opisane wyżej.
