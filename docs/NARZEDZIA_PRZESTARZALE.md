# Narzędzia przestarzałe (obsolete)

Stan: **2026-11-20**. Cel: żeby nikt — ani kolejna sesja agenta, ani człowiek —
nie zbudował czytanki starym skryptem i nie wgrał jej na Dysk pod bieżącym numerem.

**Aktywny generator czytanki:** `tools/czytanka_czysta.py` → `czytanka_v*.zip`
(pliki `01 - …` / `02 - …` + `README.md`). Opis: [CZYTANKA_DO_CZYTANIA.md](CZYTANKA_DO_CZYTANIA.md),
historia wydań: [WERSJE_CZYTANKI.md](WERSJE_CZYTANKI.md).

## Rejestr

| narzędzie | status | co robiło | dlaczego przestarzałe |
|---|---|---|---|
| `tools/buduj_czytanki.py` | **PRZESTARZAŁE** | trzy pliki: `epizody.md`, `kontekst_scen.md`, `dodatkowe.md` (`WWM_CZYTANKI_PL.zip`) | inny układ niż czytanka właściciela; od v1 czytankę buduje `czytanka_czysta.py` |
| `tools/zbuduj_czytanke_pelna.py` | **PRZESTARZAŁE** | składa warstwy `01_prolog`/`02_krainy`/`03_fabula`/`04_kontekst`/`05_reszta` | pakiet techniczny „na trójkę”, nieczytelny dla właściciela; zastąpiony |
| `tools/buduj_czytanke_gry.py` | **PRZESTARZAŁE** | sama chronologia scen wg kolejności w grze | weszła jako sekcja 01 do `czytanka_czysta.py` |
| `tools/powiazania_czytanek.py` | **PRZESTARZAŁE** | indeks powiązań kontekstowych dla `buduj_czytanki.py` | jedyny konsument (`buduj_czytanki.py`) jest przestarzały |

## Jak oznaczenie działa w praktyce

1. **Docstring** każdego pliku zaczyna się od `⚠ PRZESTARZAŁE (OBSOLETE) — NIE UŻYWAĆ do budowy czytanek.`
   i wskazuje `tools/czytanka_czysta.py`.
2. **CLI**: uruchomienie skryptu wypisuje na stderr `UWAGA: narzędzie PRZESTARZAŁE (obsolete) …`
   (import modułu i testy nie są zaśmiecane).
3. **Lista maszynowa**: `tools/przestarzale.txt` — pilnuje jej
   `tests/test_narzedzia_przestarzale.py` (każdy wpis istnieje, ma baner;
   aktywny generator banera **nie** ma; dokumentacja wymienia każdy plik).
4. **Testy** `tests/test_buduj_czytanki.py` i `tests/test_czytanka_gry.py`
   zostają jako regresja ścieżki audytowej — to nie znaczy, że te skrypty wolno używać do wydań.

## Czego NIE robić

- Nie budować `czytanka_v*.zip` z tych skryptów i nie wgrywać takich plików na Dysk.
- Nie zmieniać numeracji czytanek „z pamięci sesji”: numer ustala się z Dysku
  (`name contains 'czytanka'`) i z [WERSJE_CZYTANKI.md](WERSJE_CZYTANKI.md).
- Nie usuwać tych plików bez zgody właściciela — pełnią rolę archiwum audytowego.
