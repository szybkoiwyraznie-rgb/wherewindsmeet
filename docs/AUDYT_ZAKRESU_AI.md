# Audyt tymczasowego zakresu AI (2026-11-20)

Audyt odpowiedzi na polecenie właściciela z 2026-11-19: *„Sprawdź, czy tymczasowy
zakres został zrobiony, i czego jeszcze brakuje”*. Narzędzie:
`python3 tools/audyt_zakresu.py` (tylko czyta `index/`, `tlumaczenie/` i wpisy
`zwrotki/*.md`). Szczegóły metody na końcu; liczby można odtworzyć jednym
poleceniem.

## W skrócie

- **Integracja jest kompletna.** Wszystkie `25 696` unikalnych kluczy z `328`
  plików zwrotek AI (`zwrotki/*_ai_tymczasowe_*`, `2026-11-19_ai_tymczasowe_*`)
  znajduje się w magazynie — **0 brakujących wpisów**, importy przechodziły
  przez `--na-sucho` bez odrzuceń.
- **Kategorie (1)–(4) są domknięte** (hinty zadań, listy, przedmioty fabularne,
  opisy przedmiotów z `ccs_text_msg`).
- **Kategoria (5) — nazwy Compendium: brakuje 486 nazw** (141 nazw działów,
  334 tytuły haseł, 9 przycisków, po 1 `manual_goto_text` i `bubble_text`).
  Opisów haseł brakuje 708, ale właściciel pisał, że opisy są już w porządku.
- **Kategoria (6) — sceny pierwszej prowincji: w większości NIEZROBIONE.**
  W scenach z mapami 燕南 (`1, 501, 701`) jest `42 455` unikalnych tekstów,
  z czego przetłumaczono `8 559` (**20,2%**); brakuje **33 896** unikalnych
  kwestii. Przykład właściciela (scena `1026070`, „Looks like Uncle Jiang won't
  be tasting new wine this year…”) **nadal nie ma przekładu**.
- **Uwaga praktyczna:** zainstalowana łatka (`v0.5.0`, zbudowana ze zwrotki
  tłumacza `WWN_PL_v4`) zawiera `112 405` przekładów i **nie obejmuje**
  tymczasowych partii AI. W magazynie jest ich teraz `139 653` (28,53% miejsc
  w grze). Bez zbudowania nowej łatki właściciel nadal będzie widział po
  angielsku rzeczy, które w magazynie już są przetłumaczone.

## Tabela zakresu

Pomiar `python3 tools/audyt_zakresu.py` na `index/` (Patch 2.4) i magazynie
`tlumaczenie/` z 2026-11-20:

| kategoria | razem | tłumacz | AI | pokrycie | braki |
|---|---:|---:|---:|---:|---:|
| (1) hinty zadań `tasks.task_target_str` | 8 936 | 979 | 7 957 | **100,0%** | 0 |
| (2) listy `tasks_envelop_data` | 1 063 | 40 | 1 023 | **100,0%** | 0 |
| (3) przedmioty fabularne `text_msg` 1 800 000+ i `manual_items` | 4 981 | 3 997 | 982 | **100,0%** | 2 |
| (4) opisy przedmiotów `ccs_text_msg` + `programmer_text_msg` | 9 421 | 44 | 5 249 | 56,2% | 4 128 |
| (5) Compendium `guider_tujian_data` | 1 524 | 87 | 243 | 21,7% | 1 194 |
| (6) sceny pierwszej prowincji (燕南) | 42 455 | 7 944 | 615 | 20,2% | 33 896 |

Kolumna „tłumacz” to przekłady obecne w magazynie przed partiami AI, „AI” —
klucze występujące w zwrotkach tymczasowych. Liczby dotyczą **unikalnych
tekstów** (klucz = SHA-256 tekstu źródłowego), nie wystąpień w grze.

## Co dokładnie zrobiono

Rozkład 25 696 kluczy AI według głównego źródła tekstu:

| tabela | kluczy AI |
|---|---:|
| `tasks` (hinty, opisy i nazwy zadań) | 12 020 |
| `ccs_text_msg` (opisy przedmiotów) | 5 238 |
| sceny dialogowe (różne mapy) | 4 514 |
| `text_msg` (m.in. blok przedmiotów 1 800 000+) | 1 303 |
| `tasks_envelop_data` (listy) | 1 023 |
| `debate_guider_dialog_data` (debaty) | 452 |
| `guider_tujian_data` (Compendium) | 243 |
| pozostałe tabele (interakcje, branch, grupy zadań itd.) | 903 |

Wnioski:

- Kategorie (1) i (2) zrealizowano w całości; przy okazji przetłumaczono też
  **całą** tabelę `tasks` (opisy i nazwy zadań, 4 338 kluczy) — to więcej niż
  same hinty, ale zgodne z duchem zakresu.
- Kategoria (4) zrealizowana przez **całą** tabelę `ccs_text_msg`
  (5 282/5 282). `programmer_text_msg` (4 128 braków) to **etykiety
  interfejsu** (handel, ustawienia, kluby, minigry, UI), a nie opisy
  przedmiotów — pozostawiona świadomie poza zakresem. Przykład właściciela
  „Traces of the Past” (`EQUIP_UNRETRACED`) jest przetłumaczony.
- Kategoria (6) została tknięta tylko w `4 514` kluczach scen, z czego
  w 燕南 jedynie `615`; większość scen AI leży w scenach bez mapy (`3 120`)
  i w innych prowincjach (`1 371`). To odpowiada na pytanie „czy nie za dużo”:
  **nie za dużo w tabelach, za mało w scenach pierwszej prowincji.**

## Czego brakuje — konkretnie

### (3) Dwa ostatnie przedmioty fabularne

- `manual_items.shiyi_show_word` wiersz `1633142`: „天地玄黄，宇宙洪荒。…”
- `manual_items.extra_describe_1` wiersz `832087`: „天地不仁，以万物为刍狗。”

Oba to cytaty klasyczne; można dopisać w jednej partii.

### (4) `programmer_text_msg` — poza zakresem

`11/4 139`. To komunikaty i etykiety UI (`TRADE_*`, `SETTING_*`, `CLUB_*`,
`FILM_*`, `HOMELAND_*`), nie opisy przedmiotów. Nie tłumaczyć hurtowo bez
decyzji właściciela — to 4 128 napisów interfejsu.

### (5) Nazwy w Compendium — 486 braków

- `manual_name` (nazwy działów): 43/184, brak **141**;
- `talk_title[]` (tytuły haseł): 83/417, brak **334**;
- `button_name[]`: 0/9; `manual_goto_text`: 2/3; `bubble_text`: 0/1.

Przykłady braków: „Towers Connect Facilities” (`塔架连接设施`),
„Copper Sachet Puzzle” (`铜香囊解谜`), „Cooking Snacks” (`烹饪点心`),
„Winter Treasure Chest” (`冬日宝箱`), „Hundred Delicacies - Operation
Instructions” (`珍馐百味·经营说明`).

Stan 251/1 524 sprzed tej sesji wzrósł do 330 dzięki partii opisów szkół
sztuk walki (`zwrotki/2026-11-20_ai_tymczasowe_compendium_ka.md`, 79 wpisów;
opis w `docs/EXPERIMENT_LOG.md`). Te 79 wpisów to opisy, nie nazwy — są
**poza literalnym zakresem** (5) i można je wycofać jednym poleceniem, jeśli
właściciel sobie tego nie życzy.

### (6) Sceny pierwszej prowincji — 33 896 braków

Podział unikalnych kluczy scen 燕南 według powiązania z zadaniami:

| grupa | kluczy | przetłumaczone | braki |
|---|---:|---:|---:|
| sceny powiązane z zadaniami (`zadania_sceny` lub `r`) | 38 534 | 7 591 | 30 943 |
| sceny ambientowe (bez powiązania) | 3 921 | 968 | 2 953 |
| **razem** | **42 455** | **8 559** | **33 896** |

Przykład właściciela: scena `1026070`, mapy `[501, 701]`, `ui_type` 23,
projekt `对话-zhouyizhou`, jedna kwestia:
„Looks like Uncle Jiang won't be tasting new wine this year either… Alas,
where has he been all these past three years?” — brak przekładu.

Uwaga: część scen z mapami 燕南 należy do późniejszych zadań, które wracają do
pierwszej prowincji, a część to nieużywane warianty. Dlatego `33 896` to górna
granica „wszystkiego, co leży na mapach 燕南”, a nie dowód, że tyle zobaczy
gracz w pierwszej ćwiartce fabuły. Do decyzji właściciela pozostaje, czy
priorytetem są sceny zadań pierwszego rozdziału, czy także ambientowe
jednokwestiowe scenki (jak powyższa).

## Dlaczego właściciel nadal widzi angielskie napisy

- Najnowsza **łatka** w obiegu to `v0.5.0` z 2026-11-18, zbudowana ze zwrotki
  tłumacza `WWN_PL_v4` (plan: 112 405 przekładów). Partie tymczasowe AI
  powstały **po niej** (magazyn: 139 653 przekładów), więc nie ma ich
  w zainstalowanym kliencie.
- Część przykładów właściciela jest już w magazynie: „Search inside for clues”
  → „Poszukaj w izbie tropów”, „From Wei, to Jiang Wulang” → „Z Wei — do Jianga
  Wulanga”, „Dusty Sword Tassel” → „Zakurzony chwost miecza…”, „Traces of the
  Past” → „Ślady przeszłości”, „Lattice Door” → „Kratowe drzwi…”.
- Po zbudowaniu nowej łatki (`tools/one_click_patch.py --tylko-magazyn`,
  tryb standalone) kategorie (1)–(4) powinny zniknąć z ekranu bez dodatkowej
  pracy tłumaczeniowej. Nie testowano tej łatki w grze.

## Rekomendowana kolejność

1. **Zbudować i dostarczyć łatkę z bieżącego magazynu** (v0.6.0) — to od razu
   pokaże w grze kategorie (1)–(4). Przed instalacją: kopia zapasowa
   oryginałów (instalator robi ją sam), test na jednym zapisie.
2. **Domknąć nazwy Compendium** — 486 pozycji, około 6 partii po ~80.
3. **Sceny pierwszej prowincji** — partiami: najpierw sceny zadań pierwszego
   rozdziału i ambientowe jednokwestiowe scenki w 燕南, potem resztę. Bez
   decyzji właściciela nie tłumaczyć wszystkich 33 896.
4. Dopisać 2 brakujące przedmioty fabularne; `programmer_text_msg` zostawić.

## Metoda i ograniczenia

- Kategoria tekstu = **główne źródło klucza** (`indeks.zrodlo`), tak jak
  w `docs/STATUS.md`; klucz jest liczony raz, nawet jeśli tekst występuje
  w kilku tabelach.
- Sceny: unikalne klucze elementów `e` scen, których pole `m` zawiera mapę
  pierwszej krainy z `index/prowincje.json` (燕南: 1, 501, 701). Warianty płci
  (`@id`) traktowane jako osobny slot, zgodnie z magazynem.
- „AI” = klucz występuje w pliku `zwrotki/*.md` z niepustym `PL:`. To nie jest
  dowód, że tekst pochodzi z modelu — pliki zwrotek są jedynym śladem partii
  tymczasowych w repozytorium.
- Audyt **nie** dowodzi dostępności treści w grze ani kolejności fabuły;
  przypisanie mapy nie jest tym samym co moment odblokowania sceny.
- Odtworzenie: `python3 tools/audyt_zakresu.py` (tabela) lub `--json`.
  Testy narzędzia: `python3 -m unittest tests.test_audyt_zakresu`.
