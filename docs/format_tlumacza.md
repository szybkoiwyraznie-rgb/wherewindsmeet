# Format tabeli dla tłumacza (sceny, dialogi, mówcy)

Źródło: `tools/timeline.py` (parser `data205` i nowych plików `data201`–`data206`) → JSONL. Tekst źródłowy to chiński — angielski tylko pomocniczo (decyzja `zh_en`).

Tekst pod `text_id` jest identyczny z wpisem w `translate_words_map_zh_cn` (sprawdzono: 100% `text_id` ze scen występuje w mapie, teksty zgodne). Przekład wpisuje się pod to samo `id` w mapie tłumaczeń (`tools/apply_translation.py`).

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

## Zasady

- Chiński jest źródłem; przekład wpisuje się tylko w kolumnie `przekład`, nigdy nie nadpisuje źródła.
- Mówcę i kolejność réplik bierze się z timelinu — nie zmieniać, nie domyślać się.
- Puste/niejasne wartości (brak `dialog_no`, brak mówcy, tekst nieznaleziony w mapie) zgłaszać jako problem, nie zgadywać.
- Teksty nie-dialogowe (przedmioty, specjale, encyklopedia) są częścią zadania: ich klucze też są w `translate_words_map_zh_cn` i dostają kontekst sceny.
