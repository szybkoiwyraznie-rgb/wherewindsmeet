# Sceny, mówcy i chronologia w `data205` — jak to jest zbudowane

Ten dokument opisuje format, który pozwala odczytać z gry **kto mówi**, **w jakiej
kolejności** i **gdzie kończy się jedna scena, a zaczyna następna**. Wcześniejsze
podejścia (mapa `keyHash → tekst`) dawały tylko płaską listę stringów bez kontekstu;
`data205` daje pełny graf dialogów.

## `dialog_no` to grupa dialogowa, nie pojedynczy timeline

Pole `dialog_no` w obiekcie `TimelinePObject` **nie** identyfikuje jednoznacznie
jednego timeline'u. Ten sam numer występuje w dwóch różnych plikach z **inną**
treścią, innymi mówcami i innym `id` timeline'u:

| `dialog_no` | plik | `id` timeline'u | kwestii | treść |
|---|---|---|---|---|
| 1960001321 | `data203` | 1167636709 | 5 | 木闻莺 o蒙学院 |
| 1960001321 | `data1200` (patch) | 1709454066 | 9 | 黎书韵 o衙门 |

W całym korpusie jest **10** takich grup. Dlatego:

- **scalać po `dialog_no` nie wolna** — jedna z wersji zostałaby zgubiona;
- rejestr `MANIFEST` liczy **grup** (`dialog_timelines` = 74 951), więc pokrycie
  „X% dialogów" oznacza grupy, dla których mamy przynajmniej jeden timeline;
- tłumaczenie i tak jest kluczowane `text_id`, więc obie wersje są tłumaczone
  niezależnie i żadna nie jest nadpisywana.

## Serializator

Każda wartość to `<tag: u8><payload>`:

| tag | znaczenie |
|-----|-----------|
| `0x01` | u8 |
| `0x02` | u16 |
| `0x03` | u32 |
| `0x04` | u64 |
| `0x06` | f64 |
| `0x08` | string: `u16` **długość w bajtach** UTF-8 |
| `0x09` | lista: `u16` liczba elementów |
| `0x0a` | obiekt |
| `0x0b` | None |
| `0x0c` / `0x0d` | False / True |

Pole to `08 <u16 len> nazwa` + wartość. **Offset wartości to `offset + 3 + len(nazwa)`**
(wcześniejsza pomyłka o `+15`/`+16` dawała zero trafień).

### Pułapka: licznik w nagłówku obiektu nie jest liczbą pól

Obiekt zaczyna się od `0x0a` i `u16`, ale ta liczba **nie** równa się liczbie pól
(obserwowane 18 przy 9 polach, 20 przy 9, 16 przy 8). Dlatego obiektu nie parsuje się
po liczniku. Zamiast tego:

1. czytaj pola, dopóki bajt nie jest `0x08` (czyli do początku następnego obiektu),
2. nazwa, która już wystąpiła, kończy obiekt,
3. tablice `__children__`, `__keyframes__`, `__tracks__` mają postać `09 <u16 n>`
   i zawierają `n` obiektów `0x0a …`.

### Pułapka: pola są zapisywane **po** dzieciach

Kolejność w pliku dla grupy postaci wygląda tak:

```
… entity_tag 李嫣儿 · entity_no 1738000182 · entity_name · skeleton · npc_config …
Type = EntityTrackGroup          ← nagłówek grupy pojawia się PO jej polach
   EntityWatchTrack / EntityWatchSpan …
   EntityTextTrack
      EntityTextSpan: time, lock, duration, group_id, source_id, text, formatted_text, order
   EntityMotionTrack / EntityAnimTrack …
```

Wniosek praktyczny: **kwestia należy do ostatniego `entity_tag` zapisanego przed nią**.
Pole `group_id` w `EntityTextSpan` jest zawsze `0` w badańych danych i **nie** wskazuje
mówcy — nie używać.

## Co jest czym

| pojęcie | obiekt | pola |
|---------|--------|------|
| scena | `TimelinePObject` | `dialog_no` (u32), `project_name`, `total_duration`, `startTime`, `id`, `before_black_screen` |
| mówca | grupa w `__tracks__` | `entity_tag`, `entity_no`, `entity_name`, `skeleton` |
| kwestia | `EntityTextSpan` | `time`, `order`, `text` (hash mapy EN), `formatted_text` (**chiński oryginał**), `source_id`, `duration` |
| przypis głosu | `EntityVoiceSpan` | `voice_no`, `voice_entity_no`, `time` (rzadkie, `voice_entity_no` bywa `0`) |

`formatted_text` to gotowy tekst chiński, np. `哈哈哈哈，被抓住喽被抓住喽！`,
`它这是，邀请我们同乘？` — więc tłumaczenie z chińskiego ma pełne oparcie w danych,
a `text` pozwala powiązać linię z mapą EN (`hash → angielski`) i z patcherem.

## Reguły porządkowania

- **kolejność kwestii w scenie**: `(time, order)`; w scenach dialogowych `time`
  rośnie 0, 4, 9, 14… co odpowiada długościom wypowiedzi.
- **granica sceny**: jeden `TimelinePObject`; scena kończy się tam, gdzie zaczyna
  się następny `TimelinePObject`.
- **kolejność scen**: rosnące `dialog_no`. Bloki `dialog_no` są przydzielone per
  projekt (`对话-<pinyin>` = rozmowy z daną postacią), a w obrębie projektu rosną
  zgodnie z kolejnością zapisu treści.
- **sceny bez `dialog_no`** (cinematics, `project_name` pusty) nie mają żadnego
  znacznika miejsca w fabule — dostają własną numerację `S9001+` w kolejności pliku.

## Statystyki (stan: `000008_data205`, 2 606 chunków)

- `TimelinePObject`: **8 484**
- scen z tekstem: **7 849**, kwestii: **17 268**
- unikalnych `text` (hashy): **16 691**
- kwestii z mówcą (nazwa w `entity_tag`): **17 247**; bez nazwy w danych: **21**
- różnych etykiet mówcy: **~1 000**
- kwestii z angielskim w mapie EN: **13 954** (80,8%)
- projekty: **49** (`对话-mocheng` 4 614 jednozdaniowych barksów, `对话-liangchenghong` 309 scen/880 kwestii, …)
- scen bez `project_name`: **933** ze **6 431** kwestiami i **440** mówcami
  (cinematics **mają** mówców — to sprawdzone, nie założone)

## Ograniczenia — czytać przed tłumaczeniem

1. `dialog_no` to identyfikator dialogu w assetach. Kolejność w obrębie projektu jest
   wiarygodna, **kolejność między projektami nie jest potwierdzona** jako kolejność
   fabuły — w `data205` nie ma numeru rozdziału ani zadania.
2. Nie ma grafu zależności między scenami: `time_ref_id` (224 wartości) nie trafia
   w żadne `id` timeline'u.
3. Mówcy `玩家`, `player`, `player_1`, `player_2`, `主角`, `我`, `你` to postać gracza
   (imię wybiera gracz) — nie tłumaczyć jako konkretnej postaci.
4. `Entity轨道组` i puste `entity_tag` to grupy techniczne, nie postaci.
5. `data3` nie zawiera tekstów dialogowych (0 trafień hash → tekst); źródłem jest
   `data205`.

## Jak odtworzyć

```bash
python3 tools/timeline.py local/data205.bin --jsonl local/sceny.jsonl
python3 tools/build_scene_pack.py local/sceny.jsonl \
    --angielski local/unikalne.jsonl --wyjscie local/tlumacz
```

`local/tlumacz` zawiera: `00_INDEX.md`, `01_MOWCY.md`, `02_CHRONOLOGIA.md`,
`sceny/*.md` (49 plików, kwestie z mówcą, chińskim, angielskim i `id`) oraz
`sceny.jsonl` (te same dane maszynowo, 12 MB całości).

## Rejestr kluczy `MANIFEST` — ile dialogów ma gra i czego brakuje

`Package/HD/oversea/MANIFEST` (1,4 MB, zstd) to posortowany rejestr nazw kluczy:
`dialog_timelines.<id>`, `spaces.*`, `maps.*`, `AL.*`, … Rekordy nie mają stałej
długości, więc czyta się je skanem `u16 długość + ASCII` (`tools/manifest_keys.py`).

Wynik (`python3 tools/manifest_keys.py local/manifest.bin --sceny local/sceny.jsonl`):

| miara | wartość |
|-------|---------|
| kluczy w rejestrze | 281 002 |
| `dialog_timelines.<id>` | **74 951** |
| zakres `dialog_no` | 5 – 4 640 002 542 |
| naszych scen z `dialog_no` (z `data205`) | 7 571 |
| scen poza rejestrem (błąd odczytu) | **0** |
| pokrycie korpusu | **10,1%** |
| brakujących dialogów | **67 380** |

Wniosek: **`data205` to tylko jeden shard.** Wszystkie 7 571 naszych `dialog_no`
jest w rejestrze (więc identyfikatory czytamy poprawnie), ale 90% dialogów leży
w pozostałych plikach `Package/HD/oversea/data*` — obok `data205` w tej samej
gałęzi są `data1`–`data11`, `data200`–`data212`, `data1001`, `data1200`
(po ~1–16 MB, razem ok. 200 MB). Rejestr jest listą kontrolną pokrycia: po
dostarczeniu kolejnych plików widać dokładnie, ile dialogów przybyło.

## Gdzie szukać stref i kolejności fabuły (i dlaczego ich tu nie ma)

W `data205` przejrzano **2 589 różnych nazw pól** — nie ma `zone`, `map`, `area`,
`chapter`, `quest`, `story`, `act`, `scene_no`. Nie ma też grafu zależności scen
(`time_ref_id` nie trafia w żadne `id` timeline'u). Dlatego w `data205` **nie da się**
odczytać strefy ani fabularnej kolejności scen.

Rejestr `MANIFEST` pokazuje jednak tabele, które te dane mają:

| tabela (klucz) | co daje |
|----------------|----------|
| `dialog_source_id_to_entry_data` | mapowanie `source_id` kwestii (mamy go w każdej linii!) na wpis dialogu |
| `dialog_group_skip`, `dialog_anim_info`, `dialog_light_weather_time_data` | metadane dialogu |
| `chapter_unlock_to_world_level`, `dungeon_2p_chapter_*` | rozdziały i odblokowania |
| `maps.*` (3 416), `spaces.*` (184 946) | przestrzenie i mapy — potencjalne źródło strefy |
| `storyline.*` | animacje stanów, **nie** fabuła (nazwa myli) |

`data3` (10,8 MB, 3 949 chunków) to **blueprinty budynków** (`bp_302_pref_building_...`,
współrzędne f32); nie ma tam tekstu ani dialogów. `CameraZone.json` i `Audio_Area`
też są w grze, ale nie w tej paczce.

**Kolejny krok, żeby domknąć strefę i chronologię:** dostarczyć `data200`–`data212`
(cały korpus dialogów) oraz — jeśli będzie potrzebna strefa — pliki z tabelami
`maps`/`spaces`/`chapter`. Bez nich jedyną pewną chronologią pozostaje kolejność
w obrębie projektu (`dialog_no`), a jedynym kontekstem — mówcy i obsada sceny.
