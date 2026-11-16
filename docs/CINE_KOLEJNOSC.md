# Skąd bierze się kolejność kwestii w przerywniku (30161)

Stan: 2026-11-14. Dokument zbiera **dowody**, nie przypuszczenia — po to, żeby
kolejny krok nie był znowu zgadywaniem.

## Czego chcemy

Właściciel przepisał z ekranu cały przerywnik 30161 (39 linii, od „Wodzu!
Wodzu!” do „To przychodź szybko, dobrze?”). Ta kolejność ma wyjść z danych, tym
samym sposobem dla wszystkich przerywników.

## Co już wiemy na pewno

1. **Numer wiersza puli napisów nie jest kolejnością gry.** Ta sama scena leży
   w `text_msg` dwa razy (wiersze 590153–590179 i 591148–591175) i w żadnym
   z tych bloków nie stoi w kolejności z ekranu: w nowszym bloku „站住” („Stój!”)
   ma numer 591170, czyli wypada **po** całej rozmowie, choć w grze jest trzecią
   kwestią. Dlatego v6–v9 myliły się niezależnie od tego, jak dzieliły bloki.
2. **Nagrania mają numer, ale tylko w obrębie jednego mówcy.** `sound_data`
   trzyma dla tego przerywnika 23 nagrania: `vo_sm_sxdm4_cs_zlxl_hx_01…hx_17`
   (Ruby, 17 kwestii) i `…_pma_01…pma_06` (gracz, 6 kwestii). Numery w obrębie
   każdej serii idą zgodnie z grą, ale **nie mówią, jak serie się przeplatają**
   — a właśnie przeplatanie decyduje o kolejności („Stój!” pada między drugą
   a czwartą kwestią Ruby).
3. **Baza gry — cała — nie zawiera kolejności kwestii przerywnika.** Właściciel
   wgrał na Dysk brakujące binarki (`binarki/`: `data1`, `data204`–`data210`,
   `index*`, `MANIFEST`), więc baza jest teraz kompletna i sprawdzenie jest
   pełne, nie częściowe. Dowody (narzędzie: `tools/szukaj_w_bazie.py`):
   - **osie dialogów:** wszystkie **75 007** tabel `dialog_timelines.*` czyta się
     bez błędu; **ani jedna** nie ma w `used_sound_bnk` banku `…_cs_zlxl`
     i **ani jedna** nie zawiera kwestii z tej sceny (szukane teksty: 站住,
     老大 / 周红线, 快点起来),
   - **wiersz napisów:** identyfikator `591148` („老大 老大”, pierwsza kwestia
     z ekranu) występuje w całej bazie **dwa razy** — w `text_msg` i w
     `text_msg__grey`. Żadna inna tabela się do niego nie odwołuje. To samo jego
     hash (`13727916233045163908`): tylko `text_msg__grey`,
   - **nagranie:** identyfikator `7150686` (`vo_sm_sxdm4_cs_zlxl_hx_01`)
     występuje tylko w `sound_data` — nic go nie szereguje,
   - **żadna tabela nie jest kluczowana numerem przerywnika** (30161 jako klucz
     nie istnieje), a `new_graph_cues.*` (2 530 tabel) nie zna ani jednej nazwy
     zawierającej `zlxl`.
4. **Tabela `cutscenes` nie ma osi czasu.** Dla 30161 daje tylko: `cine_name`
   `sq001_zlxl`, `cine_path Char/e_01_cutscene/qhrw/sq001_zlxl/sq001_zlxl.cine`,
   `cine_duration 78,664`, `montage_num 17`, `cutscene_graph
   Char/graph/cutscene/c_qinghe.graph`, przestrzeń 501 i streszczenie.
   Żadnej listy kwestii ani czasów.

## Gdzie ta kolejność najprawdopodobniej jest

**W pliku osi czasu przerywnika — `.cine`** — i tylko tam. To ten plik, który gra odtwarza:
ma na osi czasu ponumerowane zdarzenia (nagranie, napis, kamera), a numery
`hx_01…pma_06` z `sound_data` są właśnie nazwami zdarzeń w takiej osi.
Plików `.cine` **nie ma w pakiecie aktualizacji** (sprawdzone: w zebranych
`INWENTARZ.jsonl` ani jednego wpisu `.cine`, a `docs/STATUS.md` opisuje to
samo dla `.mpk`), więc trzeba je wziąć z instalacji gry.

To już nie jest hipoteza „być może”: po uzupełnieniu bazy wszystkie 75 007 osi
dialogów zostało sprawdzonych i żadna nie dotyczy tego przerywnika (patrz punkt 3
wyżej).

## Co jest potrzebne, żeby to domknąć

(Baza jest już kompletna, więc ta droga jest zamknięta.) Zostaje **(A)**: pliki
`.cine` przerywników. Jeśli leżą jako pliki w instalacji gry, zbiera je
`collector/ZBIERZ_CINE.bat` (kopiuje tylko `*.cine`, nic nie zmienia). Jeśli
siedzą wyłącznie w paczkach `.mpk` (1 GB), trzeba je najpierw z paczek wyjąć —
służy do tego `collector/SNIFFER_MPK.bat` w trybie `-Szybki` na 3 paczkach:
wynik to kilka MB, z których odczytam układ indeksu paczki; jeśli nazwy ścieżek
są w paczce widoczne, napiszę wycinarkę pobierającą **tylko** `sq001_zlxl.cine`.

Gdy (A) będzie w rękach: `tools/cine_kolejnosc.py` odczyta zdarzenia osi
i wypisze kwestie w kolejności czasu; jeśli wyjdzie z tego dokładnie 39 linii
właściciela, ten sam odczyt idzie do wszystkich 3 990 przerywników z tabeli
`cutscenes` (`cine_path`), a czytanka bierze kolejność z osi, nie z numerów
wierszy.
