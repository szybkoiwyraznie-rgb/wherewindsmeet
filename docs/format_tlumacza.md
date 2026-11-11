# Format tabeli dla tłumacza (sceny, dialogi, mówcy)

Źródło: `tools/timeline.py` (parser `data205` i nowych plików `data201`–`data206`) → JSONL. Tekst źródłowy to chiński — angielski tylko pomocniczo (decyzja `zh_en`).

Tekst pod `text_id` jest **takim samym kluczem** jak w `translate_words_map_zh_cn` — sprawdzono na 50 000 `text_id` ze scen: **100% występuje w mapie**, 42 208 tekstów identycznych, 7 006 różni się tylko łamaniami wiersza. Przekład wpisuje się pod to samo `id` w mapie tłumaczeń (`tools/apply_translation.py`).

### Którą wersję brać — liczby z całego korpusu

Na pełnym korpusie (176 146 unikalnych tekstów) **25 258 tekstów (14,3%)** ma w
mapie `zh_cn` dłuższą wersję niż scena. Różnica to nie tylko łamania wiersza
(7 006 przypadków), ale właśnie ten dopisek. Pełny tekst do tłumaczenia jest
więc w shardach `index/teksty_*.jsonl` pod kluczem `tekst_mapa`, a wersja
wyświetlana w grze pod `tekst_zh`. Narzędzie `tools/sceny_z_indeksu.py --z-mapa`
wypisuje listę `{id, text}` w wersji z mapy, gotową dla
`tools/build_translator_pack.py`.

### Dwa źródła jednej répliki — którą brać?

| źródło | co zawiera |
|---|---|
| `translate_words_map_zh_cn` (mapa) | pełna linia **z dopiskiem scenicznym w nawiasach**, np. `（正声）咳咳，江湖中有…` albo `喵喵喵喵！（你这些天去哪了，好久没喂我了，哼！）` |
| `formatted_text` w scenie | tylko **wypowiadany fragment** bez nawiasów |

Różni się treścią **1 863 z 50 000** (3,7%): w 1 055 przypadkach dopisek stoi **przed** kwestią (sposób mówienia, np. `（恍然）`), w 322 — **za** nią (myśl bohaterki, np. `（嗯嗯！）`). Tłumaczyć trzeba **pełny tekst z mapy** (z nawiasami), bo tylko on jest w pliku tekstów gry; wersja ze sceny jest podglądem do kontekstu. Który wariant faktycznie renderuje klient — **do sprawdzenia w grze**, nie zakładać.

### Mówcy nie zawsze są osobami

Z 12 920 różnych `entity_tag` większość to imiona postaci, ale trafiają się też etykiety techniczne i generyki: `玩家`, `主角`, `player`, `player_1/2`, `我`, `你` (postać gracza) oraz `Entity轨道组` i puste tagi (grupy techniczne). Dla tłumacza ważna jest treść i kolejność; etykietę-generyka w raporcie oznaczać jako „gracz / nieokreślony", nie wymyślać imienia.

## Kolumny

| kolumna | znaczenie |
|---|---|
| `dialog_no` | numer dialogu z rejestru `MANIFEST` (`dialog_timelines.<id>`); może być `null` w scenach pobocznych |
| `scena / projekt` | nazwa projektu/pliku sceny z timelinu (np. `对话-zhangjunjie`) |
| `czas` | początek répliki w sekundach od początku sceny |
| `mówca` | `entity_tag` — imię mówcy po chińsku (kolejność réplik w scenie wynika z `(czas, kolejność)`) |
| `text_id` | 16-znakowy klucz (hex) wpisu w mapie tłumaczeń |
| `tekst źródłowy (chiński)` | réplika wyświetlana w grze; `⏎` oznacza łamanie wiersza w grze |
| `przekład` | **puste do wypełnienia przez tłumacza** — nie zgadywać brakujących wartości |
| `uwagi` | problemy, niejasności, kontekst sceny |

## Przykładowe wiersze (dane prawdziwe, z `data201`–`data206`)

| dialog_no | scena/projekt | czas | mówca | text_id | tekst źródłowy (chiński) | przekład | uwagi |
|---|---|---|---|---|---|---|---|
| 10000002 | 对话-zhangjunjie | 0.0 | 周琪琪 | bb5a6fd4d4cbcbd5 | 他到底啥时候下手呀？ | | |
| — | — | 0 | 主角 | 0a08b69242ac2f27 | 小孩子不学好，看别人偷东西做什么？ | | |
| — | — | 5.0 | 周琪琪 | 3b4129b9e7e118cf | 偷东西怎么了！怎么不学好了！ | | |
| — | — | 10.81 | 主角 | ad2154a4646f31e9 | 自然是不学好。 | | |
| — | — | 12.31 | 周琪琪 | 272fd2f4e118ef50 | 哼！偷东西的也是好人。 | | |
| — | — | 15.31 | 主角 | 0254d4c12a2a1e0e | 行啊，那我倒是把人抓回来给你看看。 | | |
| 10000004 | 对话-zhangjunjie | 0.0 | 唐岳 | 7659e56bd679e7da | 你…… | | |
| — | — | 0 | 主角 | 7221490cc2caeafb | 好哇，连药钱都偷，走，跟我去巡检司走一趟吧。 | | |
| — | — | 3.0 | 小偷 | f736fb540cc24dc7 | 别、别去见官—— | | |
| — | — | 5.5 | 小偷 | fdc96c9d6699a273 | 我……我前阵子东家倒了，我没活干，我、我才…… | | |

### Dwa wiersze z dopiskiem scenicznym (z mapy, nie ze sceny)

| dialog_no | scena/projekt | czas | mówca | text_id | tekst źródłowy (chiński, z mapy) | przekład | uwagi |
|---|---|---|---|---|---|---|---|
| 100586 | 对话-sunyiming | 0 | player | c7b761b2c28d5c11 | 喵喵喵喵！（你这些天去哪了，好久没喂我了，哼！） | | dopisek po kwestii = myśl mówcy |
| — | — | 24.565 | 游采苓 | 4d9d1854f47bfdde | （恍然）——蹊跷蕴之？原来这就是那道士说的天地之籁。 | | dopisek przed kwestią = sposób mówienia |

## Zasady

- Chiński jest źródłem; przekład wpisuje się tylko w kolumnie `przekład`, nigdy nie nadpisuje źródła.
- Tłumaczy się **pełny tekst z mapy** (z dopiskiem w nawiasach), nie skróconą wersję ze sceny — skrót jest tylko podglądem kontekstu.
- Mówcę i kolejność réplik bierze się z timelinu — nie zmieniać, nie domyślać się. Etykiety-generyka (`玩家`, `主角`, `player`, `我`, `你`, `Entity轨道组`) oznaczać jako „gracz / nieokreślony", nie wymyślać imienia.
- Puste/niejasne wartości (brak `dialog_no`, brak mówcy, tekst nieznaleziony w mapie) zgłaszać jako problem, nie zgadywać.
- Teksty nie-dialogowe (przedmioty, specjale, encyklopedia) są częścią zadania: ich klucze też są w `translate_words_map_zh_cn` i dostają kontekst sceny.
