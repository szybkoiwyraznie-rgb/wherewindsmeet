# Analiza korpusu: dialog–mówca, kompletność, chronologia, kontekst, elementy poza scenami

Wyniki liczone z wersjonowanego `index/` (`tools/sceny_z_indeksu.py` nie jest
potrzebny — dane są w repo). Generator: `python3 tools/analiza_korpusu.py --wyj analiza`
(opcjonalnie `--grupy`). Maszynowe wersje: `analiza/*.json`.

## 1. Dialog ↔ mówca

- **69 092 grup dialogowych** (`dialog_no`), 178 572 kwestii.
- **16 grup ma więcej niż jeden timeline** — ten sam `dialog_no` w dwóch plikach
  z **inną** treścią i innymi mówcami. Scalać po `dialog_no` nie wolna.
- Rozkład liczby mówców w grupie: 6 503 grup bez mówcy, 46 126 z jednym,
  14 396 z dwoma, 1 676 z trzema, dalej rzadziej (maksimum 9).
- **16 463 grup ma więcej niż jednego mówcę**; **13 476 grup ma wyłącznie
  mówcę generyczny** (`玩家`, `主角`, `player`, `我`, `你`) lub techniczny
  (`Entity轨道组`) — dla tych grup tłumacz nie ma „rozmowy", tylko kwestie
  gracza/techniczne, i nie wolno im wymyślać imion.
- 25 533 unikalnych par (`mowca`, `speaker_no`) przy 16 528 różnych nazw —
  czyli **ta sama nazwa mówcy występuje z różnymi numerami** (postacie
  powtarzające się w wielu scenach). Po rodzaju: 65 923 „postać",
  13 194 „gracz", 2 363 „techniczny", 119 bez nazwy.
- Szczegóły per grupa (mówcy, rodzaj, liczba kwestii, pliki, projekty):
  `python3 tools/analiza_korpusu.py --grupy` → `analiza/dialog_mowca_grupy.jsonl`
  (ok. 18 MB, dlatego generowany tylko na żądanie).

## 2. Kompletność paczek i powiązań

- Pokrycie rejestru `MANIFEST`: **69 092 z 74 951 `dialog_timelines` = 92,2%**;
  **brakuje 5 859 dialogów**; 0 scen poza rejestrem.
- Sceny na plik: `data207` 11 847, `data202` 10 600, `data203` 8 939,
  `data204` 8 811, `data205` 8 484, `data206` 12 272, `data201` 6 926,
  `data208` 7 042, `data1200` (patch) 33, `data3` 25.
- **5 871 scen nie ma `dialog_no`** i niesie **46 052 kwestii (25,8% całego
  tekstu!)** — to dialogi poboczne, ambient i cinematiczne. Bez `dialog_no`
  nie ma ich w rejestrze, więc „pokrycie 92,2%" **nie oznacza**, że mamy 92,2%
  tekstu: te sceny są poza rejestrem i trzeba je tłumaczyć osobno.
- **2 337 `text_id` występuje w więcej niż jednej scenie** (maksymalnie 3 razy) —
  ten sam tekst używany w kilku miejscach; tłumaczenie jest jedno na `text_id`,
  więc kontekst scen jest tylko pomocą, nie źródłem rozstrzygnięcia.
- **Powiązania scena ↔ tekst są w 100% spójne**: 0 linii wskazuje na `text_id`,
  którego nie ma w indeksie, i 0 tekstów w indeksie jest nieużywanych. Indeks
  zawiera dokładnie tyle tekstów (176 146), ile sceny potrzebują — nic nie
  ucieka i nic nie jest dodatkowe.
- **1 640 262 wpisów mapy `zh_cn` nie jest przypisane do żadnej scenie** —
  szczegóły w sekcji 5.

## 3. Chronologia scen i tekstów

- Kolejność linii wynika z pary (`czas`, `kolejnosc`) i jest **spójna**: 0 scen
  z niemonotonicznym czasem po tym sortowaniu.
- **291 scen ma powtórzony czas** — rozstrzyga je pole `kolejnosc`.
- Długość sceny: mediana 6 s, średnia 12,04 s, maksimum 360 s. Kwestii na scenę:
  mediana 1, średnia 2,38, maksimum 60.
- `start_time` jest wypełnione w 100% scen, ale **tylko 4 sceny mają wartość
  różną od 0** (minimum −2,0) — pole nie niesie informacji o przesunięciu.
- **1 160 scen (1,5%) ma linię poza oknem `start_time + total_duration`**
  (przykład: scena o `total_duration` 1,0 s z ostatnią linią na 20,7 s).
  Wniosek: `total_duration` **nie jest** wiarygodną granicą sceny — nie używać
  go do ucinania tekstu ani do wyznaczania końca dialogu. 50 scen nie ma
  wypełnionej wartości.
- Częstotliwość: medianowo **0,198 kwestii na sekundę**.

## 4. Dane kontekstowe w scenach

| pole | uzupelnienie |
|---|---|
| `start_time`, `total_duration`, `czas`, `kolejnosc`, `source_id` | 100% |
| `mowca` | 178 340 / 178 572 (99,9%) |
| `speaker_no` | 120 564 / 178 572 (67,6%) — brak, gdy mówca jest generyczny |
| `projekt` | 68 931 / 74 979 scen (92%) |
| `timeline_id` | 71 553 / 74 979 (95%) |
| `obsada` | 68 276 / 74 979 (91%) |

- `projekt` daje 336 różnych nazw projektów, `timeline_id` 59 439 wartości —
  to jedyne trwałe identyfikatory scen obok `dialog_no`.
- `source_id` jest **prawie unikalny na linię**: 178 361 unikalnych na 178 572
  linii (211 kolizji). Najpewniej to identyfikator klatki kluczowej, nie tekstu.
- `obsada` ma medianowo 1 wpis, maksymalnie 25 — to lista mówców sceny
  z `speaker_no` i `skeleton`.

## 5. Elementy poza scenami (widoki: interfejs, przedmioty, miejsca)

Mapa tłumaczeń `zh_cn` jest znacznie większa niż tekst dialogowy. Liczby
zweryfikowane przy odczycie mapy (2026-11-11, `docs/EXPERIMENT_LOG.md`) i
wyliczone z indeksu:

| wartość | liczba |
|---|---|
| wpisy w nagłówkach chunków mapy | 3 581 256 |
| niepuste pary `id` → tekst | 1 816 408 |
| przypisane do scen (unikalne `text_id`) | 176 146 |
| **poza scenami** | **1 640 262 (90,3% mapy)** |

- Co siedzi w tych 90,3%: miejsca (`寿昌坊-平民`), imiona postaci
  (`邵冷乄德明`), przedmioty (`耳砂珍坯·三阶`), interfejs (`累计登录2天`),
  encyklopedia — czyli wszystko, co nie jest wypowiadane w dialogu, a musi być
  przetłumaczone, żeby gra działała.
- **25 258 tekstów ma w mapie dłuższą wersję niż w scenie.** Żaden z nich nie
  jest identyczny: 22 620 różni się wyłącznie łamaniami wierszy (w scenach
  zostają tabulatory), a **2 638 (10,4%) różni się treścią** — mapa trzyma
  pełną linię z dopiskiem scenicznym w nawiasach, scena tylko wypowiadany
  fragment: `（没有真生气，故作痞痞的逗他）陈叔不是让你管我吗…`. Tłumaczyć trzeba
  wersję z mapy; który wariant renderuje klient — do sprawdzenia w grze.
- Skala dla decyzji „tłumaczyć wszystko czy tylko sceny": mapa EN ma
  1 122 784 wpisy, z czego 503 206 unikalnych tekstów (619 578 powtórzeń) i
  daje paczkę 24 MB ZIP z 583 tokenami. Dla `zh_cn` ta liczba jest teraz
  zmierzona — patrz niżej.

### 5a. Elementy poza scenami po odczycie pliku mapy (`--mapa`)

Mapa `zh_cn` pobrana z Dysku (69 470 988 B, SHA-256 w `index/manifest.json`)
i przeczytana do końca: **1 816 408 niepustych wpisów** w 7 097 chunkach
(jeden chunk jest uszkodzony i jest pomijany — 3 581 256 wpisów w nagłówkach
potwierdza, że mapa ma też puste wpisy). Wyniki: `analiza/mapa_zh_cn.json`.

| wartość | liczba |
|---|---|
| wpisy przypisane do scen | 176 119 |
| wpisy poza scenami | **1 640 289** |
| unikalnych tekstów poza scenami | **428 560** |
| unikalnych tekstów w całej mapie | 580 100 |

- **Najważniejsza liczba dla tłumaczenia: 428 560 unikalnych tekstów poza
  scenami** — tyle faktycznie trzeba przetłumaczyć, jeśli tłumaczy się całą
  mapę, a nie tylko dialogi (dla porównania: cała mapa EN dawała 503 206
  unikalnych tekstów).
- Połowa wpisów poza scenami ma **≤ 5 znaków** (725 795 wpisów krótszych niż
  5 znaków), 14 703 ma ponad 100 znaków (encyklopedia, opisy). Tokeny
  formatowania (`#H`, `{…}`, `$T(…)`, `[[…]]`) występują w 63 125 wpisach
  (3,8%), interpunkcja dialogowa w 66 880 (4,1%) — czyli tylko 4% wpisów poza
  scenami wygląda na tekst mówiony, reszta to nazewnictwo i interfejs.
- Najczęściej powtarzane wpisy to nazwy wewnętrzne, nie tekst dla gracza:
  `生态物种` (26 453×), `陈嘉铮` (14 622×), `对话` (14 167×),
  `数据加载中` (7 148×), `奖励表-陈佳伟` (7 133×). Powtórzenia nie zwiększają
  pracy tłumacza — tłumaczy się tekst, nie wpis.
- **Blokada tłumaczeniowa: 27 `text_id` używanych w scenach nie ma wpisie w
  mapie `zh_cn`.** Wszystkie 27 pochodzi z `data1200_patch` (m.in. dialogi
  3402410–3402412, 12201947, 1960001218, 1960001321). Tekst tych linii jest
  w timeline'ach, więc go mamy, ale nie ma go w mapie — nie da się ich
  przepisać do tłumaczenia bez dopisania wpisów do mapy.

## 6. Co wymaga decyzji człowieka (nie da się zautomatyzować)

Raport `analiza/do_decyzji.json`, szczegóły per grupa przez `--grupy`:

- **16 grup z wieloma timeline'ami** — pełna lista w raporcie. Dwa timeliney mogą
  być w **tym samym pliku** (np. `dialog_no` 7400065 w `data207`), więc podział
  po pliku ich nie rozstrzyga. Nie scalać po `dialog_no`.
- **13 476 grup ma wyłącznie mówcę generycznego lub technicznego** — tłumacz nie
  może wymyślać imion; przekład po bezosobowej wersji z mapy.
- **6 503 grup nie ma w ogóle mówcy** — przed paczką trzeba ustalić, kto mówi.

## 7. Mapowanie mówców — czym mówca jest identyfikowany

Raport `analiza/mapowanie_mowcow.json` (liczony z `index/`):

- **Nazwa mówcy jest w 100% kwestii poza 232** (0,13%) — `mowca` nie jest luką.
- **`speaker_no` brakuje w 58 008 kwestiach (32,5%)** — występuje tam, gdzie mówca
  jest generyczny lub głośnik jest wspólny dla kilku linii.
- Identyfikatorem mówcy **nie jest sama nazwa**: 26 006 par (`mowca`, `speaker_no`)
  przy 17 491 nazwach. **3 478 nazw ma więcej niż jeden `speaker_no`** (maksymalnie
  401 numery na jedną nazwę) i **2 625 `speaker_no` ma więcej niż jedną nazwę** —
  czyli relacja nazwa ↔ encja nie jest 1:1 i scalać po samym `speaker_no` nie wolno.
- 1 500 nazw ma więcej niż jeden `skeleton`, 2 338 nazw nie ma skeletonu wcale.
- **`entity_name` (prawdziwe imię) jest w grze zawsze puste**: 0 niepustych wartości
  na 84 393 wystąpieniach w `data201`–`data206`. Pole istnieje w strukturze
  timeline'u, ale gra go nie wypełnia — **nie uzupełnia brakujących mówców**.
- **52 nazwy dłuższe niż 20 znaków to nie imiona**, a etykiety wystąpień scenicznych,
  np. `天水集-军备区-角楼外长廊一段-汉人中年男-士兵3` (lokalizacja + typ + wariant).
  Dla tłumacza oznaczają „NPC w tle", nie osobę — nie tłumaczyć jak imion własnych.

## 8. Co blokuje 100% w czterech filarach

Raport `analiza/co_brakuje.json` — po jednym wpisowi na filar, z listą plików do
dostarczenia. W skrócie:

| filar | stan | czego brakuje |
|---|---|---|
| pokrycie danych | **92,18%** (69 092 / 74 951 dialogów), lista 5 859 brakujących znana | źródła: wszystkie pliki z timeline'ami są już w `index/`; `data209`–`data212` to dane modelowe, `data200`/`data1`/`data2` to skille, `data4`–`data11`/`data1001` to tabele bez timeline'ów |
| kategorie tekstów | 428 560 unikalnych tekstów poza scenami, podział tylko po cechach (długość, tokeny) | kategorii gry: `storyline` w rejestrze to animacje awatara, `new_graph_cues` (2 442) nie powiązane z `dialog_no` ani `timeline_id` (0 trafień), `maps` to hex_world, a `data200` nie zawiera kluczy ani tekstów mapy (0/300) |
| mapowanie mówców | identyfikator = para (`mowca`, `speaker_no`), `entity_name` puste | źródła imion/encji do rozstrzygnięcia 2 625 numerów z wieloma nazwami |
| chronologia | 0 scen niemonotonicznych w obrębie pliku, kolejność `(czas, kolejność)` spójna | mapy scena → misja → rozdział (danych misji nie ma w dostarczonych plikach) |

## Co jest jeszcze do zrobienia (skrót)

1. **Pokrycie do 100%** — potrzebne pliki z timeline'ami dialogowymi, których nie ma
   w dostarczonych archiwach. Lista brakujących `dialog_no` jest gotowa
   (`analiza/brakujace_dialogi.json`).
2. **Kategorie tekstów do 100%** — potrzebne dane gry przypisujące klucze mapy do
   kategorii (przedmioty, questy, interfejs) albo decyzja, że kategorie ustala
   właściciel/tłumacz ręcznie.
3. **Mapowanie mówców do 100%** — potrzebne źródło encji/imion (pliki NPC z gry).
4. **Chronologia do 100%** — potrzebne dane misji/questów wskazujące sceny zadania.

**Nie budujemy paczki dla tłumacza, dopóki te cztery filary nie są zamknięte.**
Paczka (`sceny.zip` + `widoki.zip` w formacie SRW Y) jest ostatnim etapem; narzędzia
do jej zbudowania są gotowe i przetestowane (`tools/build_scene_pack.py`,
`tools/build_translator_pack.py`, wejście z `index/` przez
`tools/sceny_z_indeksu.py`).
