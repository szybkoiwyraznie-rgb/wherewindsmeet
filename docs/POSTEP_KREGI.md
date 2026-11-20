# Postęp: kwestie wyzwalane w świecie (pierścienie od startu)

Aktualizacja: **2026-11-20**. Zakres: jednolinijkowe odzywki NPC z grupy
„wyzwalane w świecie” w pierwszej krainie (燕南, mapy 1/501/701). Pozycje:
relacja `spaces.*.spawn_kit_dict#<kit>` → XYZ kitu z
`index/mpk/sceny_ambient_kity.jsonl`. Narzędzie: `python3 tools/barks_regiony.py`.

Kotwica: pierwszy kit scen prologu — **X -1330,09, Z -109,59** (okolica startu).

| pierścień | kwestii razem | przetłumaczone | pozostało | pokrycie |
|---|---:|---:|---:|---:|
| ≤200 m | 384 | 236 | 148 | 61.5% |
| ≤400 m | 1372 | 263 | 1109 | 19.2% |
| ≤800 m | 3596 | 413 | 3183 | 11.5% |
| ≤1000 m | 4523 | 423 | 4100 | 9.4% |
| ≤1600 m | 5952 | 440 | 5512 | 7.4% |
| ≤3200 m | 6832 | 457 | 6375 | 6.7% |
| ≤6400 m | 9097 | 468 | 8629 | 5.1% |

„Razem” obejmuje 10 940 kwestii z pozycją (w tym już przetłumaczone);
709 kwestii z tej grupy nie ma pozycji w indeksie (brak `spawn_kit_dict`
lub kitu) — do przejrzenia później, poza pierścieniami.

## Partie

| partia | kwestii | zakres | plik zwrotki | import |
|---|---:|---|---|---|
| `barks_start_aa` | 60 | ≤200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_aa.md` | 60/60, 0 odrzuceń |
| `barks_start_ab` | 170 | ≤1000 m (kolejność odległości) | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ab.md` | 170/170, 0 odrzuceń |

Magazyn po partii `ab`: **139 883** przekłady (28,57%). Przekład AI-tymczasowy,
bez testu w grze.

## Jak kontynuować

```
python3 tools/barks_regiony.py                          # pierścienie i klastry
python3 tools/barks_regiony.py --wszystkie              # to samo, z gotowymi przekładami
python3 tools/barks_regiony.py --promien 400 --slotki dist/region_400.txt
python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_region_400 \
    --wersja 1 --data 2026-11-20 --tlumaczenie tlumaczenie \
    --tylko-sloty dist/region_400.txt --bez-zip
```

Lista `--slotki` zawiera wyłącznie kwestie **bez** przekładu, posortowane od
najbliższej — dzięki temu każda kolejna partia startuje tam, gdzie skończyła
poprzednia, bez ręcznego śledzenia numerów.

## Ograniczenia

- Odległość od startu to przybliżenie „co gracz zobaczy najpierw”, nie kolejność fabuły.
- Część kwestii występuje w kilku scenach; do pierścienia trafia najbliższe wystąpienie.
- 709 kwestii bez pozycji wymaga innego klucza (np. `trap`, `entity`) albo danych z bazy gry.
