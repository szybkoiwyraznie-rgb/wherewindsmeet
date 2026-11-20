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
| ≤800 m | 3596 | 3596 | 0 | 100% |
| ≤1000 m | 4523 | 4523 | 0 | **100%** |
| ≤1600 m | 5952 | 5952 | 0 | **100%** |
| ≤3200 m | 6832 | 6832 | 0 | **100%** |
| ≤6400 m | 9097 | 9097 | **0** | **100%** |
| ≤12000 m (dalszy próg) | 10940 | 9116 | 1824 | 83,3% |

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
| `barks_start_ak` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ak.md` | 200/200, 0 odrzuceń |
| `barks_start_al` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_al.md` | 200/200, 0 odrzuceń |
| `barks_start_am` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_am.md` | 200/200, 0 odrzuceń |
| `barks_start_an` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_an.md` | 200/200, 0 odrzuceń |
| `barks_start_ao` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ao.md` | 200/200, 0 odrzuceń |
| `barks_start_ap` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ap.md` | 200/200, 0 odrzuceń |
| `barks_start_aq` | 203 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_aq.md` | 203/203, 0 odrzuceń |
| `barks_start_ar` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ar.md` | 200/200, 0 odrzuceń |
| `barks_start_as` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_as.md` | 200/200, 0 odrzuceń |
| `barks_start_at` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_at.md` | 200/200, 0 odrzuceń |
| `barks_start_au` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_au.md` | 200/200, 0 odrzuceń |
| `barks_start_av` | 200 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_av.md` | 200/200, 0 odrzuceń |
| `barks_start_aw` | 97 | ≤1000 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_aw.md` | 97/97, 0 odrzuceń |
| `barks_start_ax` | 200 | ≤1600 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ax.md` | 200/200, 0 odrzuceń |
| `barks_start_ay` | 200 | ≤1600 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ay.md` | 200/200, 0 odrzuceń |
| `barks_start_az` | 200 | ≤1600 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_az.md` | 200/200, 0 odrzuceń |
| `barks_start_ba` | 200 | ≤1600 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_ba.md` | 200/200, 0 odrzuceń |
| `barks_start_bb` | 200 | ≤1600 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bb.md` | 200/200, 0 odrzuceń |
| `barks_start_bc` | 200 | ≤1600 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bc.md` | 200/200, 0 odrzuceń |
| `barks_start_bd` | 212 | ≤1600 m — **domknięcie** | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bd.md` | 212/212, 0 odrzuceń |
| `barks_start_be` | 150 | ≤3200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_be.md` | 150/150, 0 odrzuceń |
| `barks_start_bf` | 150 | ≤3200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bf.md` | 150/150, 0 odrzuceń |
| `barks_start_bg` | 150 | ≤3200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bg.md` | 150/150, 0 odrzuceń |
| `barks_start_bh` | 150 | ≤3200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bh.md` | 150/150, 0 odrzuceń |
| `barks_start_bi` | 150 | ≤3200 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bi.md` | 150/150, 0 odrzuceń |
| `barks_start_bj` | 113 | ≤3200 m — **domknięcie** | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bj.md` | 113/113, 0 odrzuceń |
| `barks_start_bk` | 150 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bk.md` | 150/150, 0 odrzuceń |
| `barks_start_bl` | 150 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bl.md` | 150/150, 0 odrzuceń |
| `barks_start_bm` | 150 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bm.md` | 150/150, 0 odrzuceń |
| `barks_start_bn` | 150 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bn.md` | 150/150, 0 odrzuceń |
| `barks_start_bo` | 250 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bo.md` | 250/250, 0 odrzuceń |
| `barks_start_bp` | 250 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bp.md` | 250/250, 0 odrzuceń |
| `barks_start_bq` | 250 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bq.md` | 250/250, 0 odrzuceń |
| `barks_start_br` | 250 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_br.md` | 250/250, 0 odrzuceń |
| `barks_start_bs` | 250 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bs.md` | 250/250, 0 odrzuceń |
| `barks_start_bt` | 250 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bt.md` | 250/250, 0 odrzuceń |
| `barks_start_bu` | 154 | ≤6400 m | `zwrotki/2026-11-20_ai_tymczasowe_barks_start_bu.md` | 154/154, 0 odrzuceń |

Razem w pierścieniu ≤1 000 m: **4 330 kwestii** w partiach `aa`–`aw`
(60 + 170 + 10 × 200 + 8 × 200 + 203 + 97) plus 193 kwestie przetłumaczone
wcześniej w innych partiach — daje to **4 523 / 4 523 = 100%**.

Pierścienie **≤200 m, ≤400 m, ≤800 m i ≤1 000 m są domknięte w 100%**.
Obowiązkowy promień z polecenia właściciela (<400 m) oraz preferencyjny
(<1 000 m) oraz ≥ piersień ≤1 600 m (5 952/5 952) mają pełny przekład.
Pierścień **≤3 200 m domknięty w 100%** (6 832/6 832). Zostaje najdalszy
próg ≤6 400 m: **9 097/9 097 (100%)** — domknięty partiami `bk`–`bu`.

Magazyn po partii `bu`: **148 512** przekładów (**30,34%**).
Kolejny próg do zrobienia: 6 400–12 000 m — **1 824** kwestie
(`dist/region_12000.txt`); poza tym ~429 kwestii bez pozycji lub dalej niż 12 km. Przekład AI-tymczasowy,
bez testu w grze.

Po każdej partii lista robocza topnieje: 4 270 → (…) → 1 097 (`aq`) → 897 (`ar`)
→ 697 (`as`) → 497 (`at`) → 297 (`au`) → 97 (`av`) → **0** kluczy (`aw`,
pierścień ≤1 000 m domknięty). Nowa lista `--promien 1600`: 1 412 → **1 212**
kluczy (`ax` → 1 012 `ay` → 812 `az` → 612 `ba` → 412 `bb` → **0** `bd`).

## Jak kontynuować

```
python3 tools/barks_regiony.py                          # pierścienie i klastry
python3 tools/barks_regiony.py --wszystkie              # to samo, z gotowymi przekładami
python3 tools/barks_regiony.py --promien 6400 --slotki dist/region_6400.txt
python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_region_6400 \
    --wersja 1 --data 2026-11-20 --tlumaczenie tlumaczenie \
    --tylko-sloty dist/region_6400.txt --bez-zip
```

Lista `--slotki` zawiera wyłącznie kwestie **bez** przekładu, posortowane od
najbliższej — dzięki temu każda kolejna partia startuje tam, gdzie skończyła
poprzednia, bez ręcznego śledzenia numerów.

## Ograniczenia

- Odległość od startu to przybliżenie „co gracz zobaczy najpierw”, nie kolejność fabuły.
- Część kwestii występuje w kilku scenach; do pierścienia trafia najbliższe wystąpienie.
- 709 kwestii bez pozycji wymaga innego klucza (np. `trap`, `entity`) albo danych z bazy gry.
- Pierścienie pokrywają 10 683 z 11 369 kwestii grupy: po domknięciu ≤6 400 m
  zostaje jeszcze **1 586 kwestii dalszych niż 6 400 m** (do 11 085 m) oraz
  ok. **686 bez pozycji** — to nie „koniec całości”, tylko koniec geografii
  wokół startu gry.
