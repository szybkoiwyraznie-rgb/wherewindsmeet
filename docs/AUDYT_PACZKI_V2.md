# Audyt i projekt paczki v2 (Wariant A+B)

Dokument utrwala wyniki audytu bazy gry, map tekstów i dotychczasowej paczki v1 (`paczki/v1/paczka.json`) oraz zatwierdzone zasady przebudowy indeksu (`index/`) i generatora paczki dla tłumacza (`tools/buduj_paczke.py`).

## 1. Język docelowy patchera (`zbuduj_latke.py`)

* Patcher (`tools/zbuduj_latke.py`, `instalator/instaluj_latke.ps1`) modyfikuje **wyłącznie angielskie mapy gry**:
  * `Package/HD/oversea/locale/translate_words_map_en`
  * `Package/HD/oversea/locale/translate_words_map_en_diff`
  * `LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff`
* Chińskie mapy (`translate_words_map_zh_cn*`) służą wyłącznie jako stabilny klucz źródłowy w indeksie; klient gry pozostaje ustawiony na język **angielski**, więc pominięte wpisy wyświetlają się naturalnie po angielsku.

## 2. Wykryte problemy w `wyciag.py`, `index/` i `buduj_paczke.py` (v1)

1. **Losowy podział `X` / `X__grey`:**
   * `text_msg` (`125 616` wierszy) i `text_msg__grey` (`125 619` wierszy) dzielą `125 067` (99,6%) identycznych tekstów ZH.
   * Pętla po nieposortowanym `set()` w `tools/wyciag.py` rozdzielała `73` pary `__grey` w przybliżeniu 50/50 (`61 223` wpisów w `index/`), a `tools/buduj_paczke.py` sortował po `kind != base`, przez co ciągłe sceny (np. prolog `text_msg 590291–590459`) rozpadały się między różne pliki (`07_komunikaty_04.md` i `_12.md`).
2. **Kolizje hashy ZH między różnymi kontekstami:**
   * Ten sam ciąg znaków ZH w grze miewa różne 64-bitowe `text_id` i zupełnie różne znaczenie po angielsku (np. `590438` `十步杀一人` w cutscenie = *"Cut them down, left and right"*, a w `buff`/`stuff_items` = *"Relentless Advance"*; podobnie `590439` *"Never leave a trace"* vs *"Swift Execution"*).
   * Ponieważ `wyciag.py` scalał wszystkie `text_id` po samym `sha256(zh)` i wybierał pojedyncze `most_common(1)`, kwestie w cutscenach były podmieniańce etykietami z innych tabel (`709` znaczących kolizji w samym zakresie `590000–592694`).
3. **Brak wydzielonej sekcji cutscen:**
   * W bazie gry nie ma bezpośrednich relacji ID z tabel `cutscenes` / `task_cutscene_replay` do `text_msg` (timeliny `.cine` leżą poza tabelami bazy), jednak w `text_msg 590000–592694` leży ciągły blok `2 688` linii dialogowych cutscen (w tym prolog), do którego w `sound_data` istnieje `582` dopasowań audio (`vo_*`) wskazujących kody scen i mówców. Dodatkowe treści cutscenowe (`cutscenes`, `task_cutscene_replay`, `entry_collect_movie_subtitle_data`, `wds_oneday_intro_cutscene_data`) były dotąd rozrzucone po widokach `06_` i `09_`.
4. **Niepotrzebne treści meta / nicki w paczce:**
   * `text_msg 3220000–3269999` zawiera **`49 959`** losowych nicków botów/graczy (od `3270000` wracają zwykłe kwestie NPC).
   * `programmer_text_msg` (`3 753` w widoku), tabele samouczków (`guider_*`, `battle_guide_*`, `homeland_guide*`, `growth_guide_*`, `activity_season_guide_*`), konfiguracje sterowania/klawiszy (`input_func_config`, `setting_*`, `windows_key*`, `xbox*`, `key_guide_*`, `key_preset_*`, `pc_slot_tip*`, `dungeon_joystick_data`, `cutscene_qte_config`), techniczne formaty UI (`datetime_format_config`, `right_side_page_comps`, `click_target_info_config`, `ui_corner_btn_config`, `common_tip_*`, `common_share_config`, `pvp_room_grey_gonggao`), placeholdery (`~239`), chińskie umowy beta/reklamy WeChat (`~16`) i komunikaty błędów sieciowych (`~639`) nie powinny trafiać do paczki tłumacza.

## 3. Zatwierdzone zasady v2 (Wariant A+B)

1. **Przebudowa `index/` (`wyciag.py`, `indeks.py`, `zbuduj_latke.py`, `apply_translation.py`):**
   * Deterministyczny priorytet źródeł: preferować tabele bez sufiksu `__grey` oraz kontrolować kolejność zapisu źródeł.
   * Zachowanie wariantów znaczeniowych dla kolizji `(zh, en_oryg)`: gdy różne `text_id` o tym samym `zh` mają znacząco różne `en` (szczególnie w cutscenach), rozróżniać je osobnym kluczem wariantu w `index/` oraz dopasowywać kontekstowo w `zbuduj_latke.py` (porównując oryginalne `en` z mapy gry, z zachowaniem kompatybilnego fallbacku po `zh`).
2. **Wykluczenia z paczki tłumacza (`buduj_paczke.py`):**
   * Wykluczyć z paczki elementy meta i nietłumaczone (zostają po angielsku):
     * nicki botów `text_msg 3220000–3269999`,
     * placeholdery, węzły testowe, chińskie reklamy WeChat/WeCom/NetEase God i umowy beta,
     * `programmer_text_msg`, komunikaty błędów sieciowych/serwera/limitów zapytań,
     * tabele meta: samouczki, helpy, sterowanie/klawisze, QTE, ustawienia, komunikaty UI/czatu i patch-noty balansu PvP.
   * Zachować elementy fabuły, zadań, dialogów, postaci, przedmiotów, encyklopedii, świata, walki oraz `10_bez_zrodla` (zawiera realne linie fabularne i zadania wywoływane ze skryptów).
3. **Dedykowana sekcja cutscen (`cutsceny/`):**
   * Wydzielić treści cutscenowe obok `sceny/` i `widoki/` z maksymalnym kontekstem:
     * `cutsceny/01_napisy_cutscen_*.md` — `text_msg 590000–592694` pogrupowane po lukach ID i segmentach `sound_data`, z jawnym oznaczeniem Prologu, mówców (prefiksy ZH / `sound_data` / warianty EN), kodów nagrań `vo_*` i par bohater/bohaterka,
     * `cutsceny/02_intro_i_filmy.md` — `wds_oneday_intro_cutscene_data` i `entry_collect_movie_subtitle_data` (znaczniki czasu + mówcy),
     * `cutsceny/03_plansze_i_streszczenia.md` — `cutscenes` (plansze + `synopsis_text`) i `task_cutscene_replay` (powiązanie z zadaniem/rozdziałem).
4. **Test w grze (`latka_testowa.py`):**
   * Zakres `prolog` w łatce testowej oprzeć o odbudowane bloki prologu z `cutsceny/` oraz sceny rozdziału 1, a po weryfikacji wygenerować docelową paczkę `--tylko-z-en` i łatkę testową `ui+prolog`.
