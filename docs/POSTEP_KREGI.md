# Postęp: kwestie wyzwalane w świecie (pierścienie od startu)

Aktualizacja: **2026-11-20**. Zakres: jednolinijkowe odzywki NPC z grupy
„wyzwalane w świecie” w pierwszej krainie (燕南, mapy 1/501/701). Pozycje:
relacja `spaces.*.spawn_kit_dict#<kit>` → XYZ kitu z
`index/mpk/sceny_ambient_kity.jsonl`. Narzędzie: `python3 tools/barks_regiony.py`.

Kotwica: pierwszy kit scen prologu — **X -1330,09, Z -109,59** (okolica startu).

| pierścień | kwestii razem | przetłumaczone | pozostało | pokrycie |
|---|---:|---:|---:|---:|
| ≤200 m | 384 | 384 | 0 | 100% |
| ≤400 m | 1372 | 1063 | 309 | 77.5% |
| ≤800 m | 3596 | 1213 | 2383 | 33.7% |
| ≤1000 m | 4523 | 1223 | 3300 | 27.0% |
| ≤1600 m | 5952 | 1240 | 4712 | 20.8% |
| ≤3200 m | 6832 | 1257 | 5575 | 18.4% |
| ≤6400 m | 9097 | 1268 | 7829 | 13.9% |

„Razem” obejmuje 10 940 kwestii z pozycją (w tym już przetłumaczone);
709 kwestii z tej grupy nie ma pozycji w indeksie (brak `spawn_kit_dict`
lub kitu) — do przejrzenia później, poza pierścieniami.

## Partie

| partia | kwestii | zakres | plik zwrotki | import |
|---|---:|---|---|---|
| `barks_start_aa` | 60 | ≤200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_aa.md` | 60/60, 0 odrzuceń |
| `barks_start_ab` | 170 | ≤1000 m (kolejność odległości) | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ab.md` | 170/170, 0 odrzuceń |
| `barks_start_ac` | 200 | ≤1000 m (kolejność odległości) | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ac.md` | 200/200, 0 odrzuceń |
| `barks_start_ad` | 200 | ≤1000 m (kolejność odległości) | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ad.md` | 200/200, 0 odrzuceń |
| `barks_start_ae` | 200 | ≤1000 m (kolejność odległości) | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ae.md` | 200/200, 0 odrzuceń |
| `barks_start_af` | 200 | ≤1000 m (kolejność odległości) | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_af.md` | 200/200, 0 odrzuceń |

Razem w pierścieniu ≤1000 m: **1030 kwestii** (60 + 170 + 200×4).
Pierścień ≤200 m jest **domknięty w 100%**, ≤400 m w 77,5%.

Magazyn po partii `af`: **140 683** przekłady (28,74%). Przekład AI-tymczasowy,
bez testu w grze.

Po każdej partii lista robocza topnieje: 4270 → 3900 (`ac`) → 3700 (`ad`)
→ 3500 (`ae`) → **3300** kluczy (`af`).

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
