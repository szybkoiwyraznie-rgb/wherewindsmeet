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
3. **Osie dialogów (`dialog_timelines.*`) nie zawierają głosu przerywników.**
   Sprawdzone na wszystkich **26 990** osiach, które da się odczytać z danych
   w piaskownicy: ani jedna nie ma w `used_sound_bnk` banku `…_cs_zlxl`
   (0 trafień na 26 990). Pozostałe **48 017** osi leży w plikach
   `data204`–`data208`, których w piaskownicy **nie ma** — więc ten wynik nie
   jest jeszcze rozstrzygający i trzeba go domknąć.
4. **Tabela `cutscenes` nie ma osi czasu.** Dla 30161 daje tylko: `cine_name`
   `sq001_zlxl`, `cine_path Char/e_01_cutscene/qhrw/sq001_zlxl/sq001_zlxl.cine`,
   `cine_duration 78,664`, `montage_num 17`, `cutscene_graph
   Char/graph/cutscene/c_qinghe.graph`, przestrzeń 501 i streszczenie.
   Żadnej listy kwestii ani czasów.

## Gdzie ta kolejność najprawdopodobniej jest

**W pliku osi czasu przerywnika — `.cine`.** To ten plik, który gra odtwarza:
ma na osi czasu ponumerowane zdarzenia (nagranie, napis, kamera), a numery
`hx_01…pma_06` z `sound_data` są właśnie nazwami zdarzeń w takiej osi.
Plików `.cine` **nie ma w pakiecie aktualizacji** (sprawdzone: w zebranych
`INWENTARZ.jsonl` ani jednego wpisu `.cine`, a `docs/STATUS.md` opisuje to
samo dla `.mpk`), więc trzeba je wziąć z instalacji gry.

Druga możliwość, mniej pewna: osie `dialog_timelines.*` z plików
`data204`–`data208` (48 017 osi, których nie mogliśmy odczytać).

## Co jest potrzebne, żeby to domknąć

Albo **(A)** pliki `.cine` przerywników z instalacji gry — zbiera je
`collector/ZBIERZ_CINE.bat` (albo `collector/zbierz_cine.ps1`): kopiuje tylko
`*.cine` z `Char/e_01_cutscene`, niczego nie zmienia, pakuje ZIP-a obok skryptu;
albo **(B)** brakujące części zrzutu bazy: `…_czesc2.zip`, `…_czesc3.zip`,
`…_czesc5.zip` (w nich leżą `data1`, `data204`–`data210`).

Gdy (A) będzie w rękach: `tools/cine_kolejnosc.py` odczyta zdarzenia osi
i wypisze kwestie w kolejności czasu; jeśli wyjdzie z tego dokładnie 39 linii
właściciela, ten sam odczyt idzie do wszystkich 3 990 przerywników z tabeli
`cutscenes` (`cine_path`), a czytanka bierze kolejność z osi, nie z numerów
wierszy.
