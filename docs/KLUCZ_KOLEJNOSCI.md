# Klucz techniczny kolejności tekstów w grze

Notatka z przeglądu plików gry (`WWM_AKTUALIZACJA_20261113_…_czesc1–8.zip`).
Pytanie brzmiało: **po czym poznać kolejność, w jakiej gra odtwarza teksty**,
skoro dotychczasowe Czytanki sortowały po numerze wiersza i prolog wypadał źle.

## Wnioski w skrócie

Gra trzyma teksty w **trzech różnych mechanizmach**, każdy z własnym kluczem:

| Mechanizm | Tabela | Klucz kolejności |
|---|---|---|
| Sceny dialogowe (75 007 szt.) | `dialog_timelines.<dialog_no>` | `dialog_no` rosnąco, w dialogu `order`, potem `time` |
| Pule napisów cutscen | `text_msg` / `text_msg__grey` (po ~126 tys. wierszy) | ciągły blok `id`, w bloku `id` rosnąco |
| Filmy (przerywniki) | `entry_collect_movie_subtitle_data` | `dialog_no`, w filmie `time` i `duration` |

Numeracja `text_msg` **nie jest** numeracją scen dialogowych — to osobny
basen napisów, z którego silnik czyta kolejne `id` w obrębie bloku. Dlatego
mieszanie obu porządków w jednym sortowaniu (tak jak robi to dzisiejszy
`tools/buduj_czytanki.py`) daje kolejność niezgodną z grą.

## 1. Sceny dialogowe — `dialog_timelines.<nr>`

Każdy dialog ma własną tabelę: `timeline` z drzewem `__tracks__` →
`__keyframes__`. Pojedynczy klucz animacji wygląda tak (dialog 7530284):

```json
{"time": 0.0, "duration": 3.317, "order": 0, "source_id": 753028401,
 "text": 14125065368676428644,
 "formatted_text": "俺们都是名门正派，谁偷你们东西？！差不多得了！"}
```

- `time` — sekunda odtworzenia w timeline,
- `order` — kolejność klucza w torze (tory to mówcy),
- `source_id` = `dialog_no * 100 + numer linii`,
- `formatted_text` — gotowy tekst, po nim wiążemy wiersz z indeksem
  (klucz indeksu = pierwsze 16 znaków SHA-256 tekstu; sprawdzone).

### Dowód: ucieczka na koniach

Sceny `10167`–`10181` to po jednej kwestii. Rosnąco po `dialog_no` dają
dokładnie ciąg z Twojego spisu (15 z 15 linii, ta sama kolejność):

| dialog_no | tekst w grze (EN) |
|---|---|
| 10167 | Jiang Yan! You slew your own father and stole the jade! … |
| 10168 | After him! Don't let him flee with the Zhenguan Jade! |
| 10169 | The secret within that pendant must be quite something. |
| 10170 | Not now. Come on. |
| 10171 | Heh. The whole world's after you, yet you still won't tell? |
| 10172 | You're one to talk. Still inviting me to Jiangnan? |
| 10173 | Haha, what of it? The two of us against the world—what a delight! |
| 10174 | Hahaha, Jiang Yan! Jiang Yan! |
| 10175 | Heh, they even brought out the fire cannons. |
| 10176 | Heehee, Zhenguan Jade! Zhenguan Jade! |
| 10177 | Tsk. |
| 10178 | Even the Aureate Pavilion takes interest? You're in more trouble… |
| 10179 | Cold feet? |
| 10180 | Look at that! Jiang Yan, the stone-faced hero… |
| 10181 | Hmph. |

## 2. Pule napisów — `text_msg` / `text_msg__grey`

Wiersze 590336–590351 w rosnącej kolejności `id` dają **całą pierwszą
cutscenę** z Twojego spisu (16 linii, ta sama kolejność):

```
590336 是你            It's you.
590337 是啊 来抓你       That's right, here to take you in.
590338 穷途末路         Even at the end of the road,
590339 尚有一饮入喉      a drink to wet your throat.     (warstwa _grey)
590340 如何            Well? How is it?                (warstwa _grey)
590341 淡              Bland.
590342 哈              Huh...?
590343 江南的丰和春倒是甘醇  Spring's Bounty in Jiangnan tastes sweet.
590344 不如            Shall we
590345 你我同往         go together?
590346 不去            No.
590347 怕给我惹麻烦      Worried on my account?
590348 放心            Don't be.
590349 我只怕他们不敢来   The cowards probably wouldn't dare!
590350 抓住他           Seize him!              (warstwa _grey)
590351 夺下镇冠珏        Retrieve the Zhenguan Jade!
```

Skan całej bazy (114 925 tabel) pokazał, że **żadna tabela nie wskazuje tych
`id` liczbowo** — jedynym kluczem jest sam blok i rosnące `id`. Blok
591495–591518 to scena w Qinghe (`Kiedy wreszcie pozwolisz mi zobaczyć
jianghu?` … `江湖同游` / `蝴蝶`).

### Warianty tej samej scenki

Zaraz za blokiem 590336–590351 leży **drugi wariant tej samej rozmowy**:
590352–590360 (`是啊 / 来捉你 / 这下有趣了 / 老规矩 …`), a pod 591485–591494
trzeci (`还是三个 / 我们摊牌 / 摊牌 / 来杀你 / 如何 / 你我同往 …`). To odgałęzienia
(rodzaj bohatera / wybory), nie ciąg dalszy scenki — przy układaniu Czytanek
trzeba je pokazać jako warianty, nie doklejać jeden po drugim.

## 3. Filmy — `entry_collect_movie_subtitle_data`

Trzy filmy, każdy z gotową listą linii z `time` i `duration`:

| `dialog_no` | film |
|---|---|
| 1 | pieśń o lampionach (`花果山上来了那一批灯` …) |
| 2 | `钗头凤` (pingtan z filmu drugiego) |
| 3 | `中渡桥之战` (film trzeci) |

Przykład (film 2): `101` @1,0 s → `102` @4,0 s → `103` @7,0 s … — czasu nie
trzeba zgadywać, jest w danych.

## Co jeszcze nie jest rozwiązane

Kolejność **w obrębie** dialogu i **w obrębie** bloku napisów jest już
techniczna i sprawdzalna. Otwarte zostaje **przeplatanie** bloków między sobą
(np. cutscena 590336 → ucieczka 10167–10187 → Qinghe 591495): to jest
zaprogramowane w skryptach zadań, a nie w tabeli z tekstami — w bazie nie ma
tabeli, która wymienia te jednostki po kolei. Do domknięcia trzeba albo
znaleźć tabelę zadania prologu, albo przyjąć jawną listę kolejności jednostek
ustaloną z Twojego spisu i pilnować tylko porządku wewnątrz jednostek.

## Pliki

- `tools/kolejnosc_gry.py` — zbiera klucz z bazy gry (`--baza …`), porównuje
  z transkryptem (`--sprawdz …`).
- `index/kolejnosc_0.jsonl` … `kolejnosc_f.jsonl` — 291 336 wierszy w 16
  shardach (podział po pierwszym znaku klucza, jak reszta indeksu). Pola:
  `k` (klucz tekstu), `z` (`dialog`/`napis`/`napis_grey`/`film`), `d` (dialog),
  `i` (id w puli), `t` (czas), `o` (kolejność), `s` (`source_id`).

## Prolog złożony z klucza — `zwrotki/prolog_wg_klucza.md`

`tools/prolog_z_klucza.py` składa transkrypt gracza z kluczem technicznym:

- sceny idą w kolejności transkryptu (szkielet, póki nie ma skryptu zadania),
- wewnątrz sceny linie sortuje już **klucz z danych** — dialogi po numerze
  i czasie, napisy po `id`, więc kolejność wewnętrzna nie zależy od pamięci,
- gdy ten sam tekst jest w kilku wariantach, wybierany jest **najwcześniejszy
  w danych** (wariant główny), a pozostałe odgałęzienia trafiają do aneksu.

Wynik dla prologu: 21 linii ucieczki to `dialog 10167`–`10187` w numeracji
rosnącej, a scenka otwierająca to napisy `590336`–`590351` (z dwiema liniami
z warstwy `_grey`). Aneks pokazuje warianty `590352`–`590360` i `591485`–`591494`.
