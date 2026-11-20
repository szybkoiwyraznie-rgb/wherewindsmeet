# Postęp: kwestie wyzwalane w świecie (pierścienie od startu)

Aktualizacja: **2026-11-20**. Zakres: jednolinijkowe odzywki NPC z grupy
„wyzwalane w świecie” w pierwszej krainie (燕南, mapy 1/501/701). Pozycje:
relacja `spaces.*.spawn_kit_dict#<kit>` → XYZ kitu z
`index/mpk/sceny_ambient_kity.jsonl`. Narzędzie: `python3 tools/barks_regiony.py`.

Kotwica: pierwszy kit scen prologu — **X -1330,09, Z -109,59** (okolica startu).

| pierścień | kwestii razem | przetłumaczone | pozostało | pokrycie |
|---|---:|---:|---:|---:|
| ≤200 m | 384 | 384 | 0 | 100% |
| ≤400 m | 1372 | 1372 | 0 | 100% |
| ≤800 m | 3596 | 2013 | 1583 | 56,0% |
| ≤1000 m | 4523 | 2023 | 2500 | 44,7% |
| ≤1600 m | 5952 | 2040 | 3912 | 34,3% |
| ≤3200 m | 6832 | 2057 | 4775 | 30,1% |
| ≤6400 m | 9097 | 2068 | 7029 | 22,7% |

„Razem” obejmuje 10 940 kwestii z pozycją (w tym już przetłumaczone);
709 kwestii z tej grupy nie ma pozycji w indeksie (brak `spawn_kit_dict`
lub kitu) — do przejrzenia później, poza pierścieniami.

## Partie

| partia | kwestii | zakres | plik zwrotki | import |
|---|---:|---|---|---|
| `barks_start_aa` | 60 | ≤200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_aa.md` | 60/60, 0 odrzuceń |
| `barks_start_ab` | 170 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ab.md` | 170/170, 0 odrzuceń |
| `barks_start_ac` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ac.md` | 200/200, 0 odrzuceń |
| `barks_start_ad` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ad.md` | 200/200, 0 odrzuceń |
| `barks_start_ae` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ae.md` | 200/200, 0 odrzuceń |
| `barks_start_af` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_af.md` | 200/200, 0 odrzuceń |
| `barks_start_ag` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ag.md` | 200/200, 0 odrzuceń |
| `barks_start_ah` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ah.md` | 200/200, 0 odrzuceń |
| `barks_start_ai` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ai.md` | 200/200, 0 odrzuceń |
| `barks_start_aj` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_aj.md` | 200/200, 0 odrzuceń |

Razem w pierścieniu ≤1000 m: **2 030 kwestii** (60 + 170 + 200×9).
Pierścienie **≤200 m i ≤400 m są domknięte w 100%** — cały obowiązkowy
promień z polecenia właściciela ma przekład.

Magazyn po partii `aj`: **141 483** przekłady (28,90%). Przekład AI-tymczasowy,
bez testu w grze.

Po każdej partii lista robocza topnieje: 4270 → 3900 (`ac`) → … → 2500 kluczy
(`aj`), czyli w promieniu 1000 m ubyło 1770 kwestii.

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
