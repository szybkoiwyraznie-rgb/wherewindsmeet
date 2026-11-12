# Czytanki Where Winds Meet (`tools/buduj_czytanki.py`)

Narzędzie `tools/buduj_czytanki.py` generuje polskie czytanki `.md` oraz
deterministyczne archiwum `WWM_CZYTANKI_PL.zip` (wzorowane na czytelniczym
formacie SRW Y / SRW OE, dopasowane do struktury wyciągu `index/` w Where Winds Meet).

## Uruchomienie

Z pełnego lub częściowego magazynu `tlumaczenie/`:

```bash
python3 tools/buduj_czytanki.py \
  --magazyn tlumaczenie \
  --wyj-katalog dist/czytanki \
  --wyj-zip dist/WWM_CZYTANKI_PL.zip
```

Albo bezpośrednio z częściowej zwrotki tłumacza (np. przetłumaczonego fragmentu
prologu lub pierwszego rozdziału):

```bash
python3 tools/buduj_czytanki.py \
  --zwrotka zwrotka_czesc1.zip \
  --tylko-zwrotka \
  --zakres przetlumaczone \
  --wyj-katalog dist/czytanki_podglad \
  --wyj-zip dist/WWM_CZYTANKI_PL_podglad.zip
```

Najważniejsze przełączniki:
- `--zakres przetlumaczone | kompletne-rozdzialy | wszystko` — domyślnie zawiera
  wyłącznie przetłumaczone kwestie i wpisy; `kompletne-rozdzialy` dopuszcza
  tylko w 100% ukończone sekcje; `wszystko` buduje pełny szkielet z jawnymi
  markerami `[Brak polskiego tekstu (...)]`.
- `--plec oba | bohater | bohaterka` — obsługa kwestii zależnych od płci postaci
  gracza (`@id` w dialogach i pary w napisach cutscen).
- `--z-otoczeniem` — dołącza katalog dialogów poza zadaniami (`06_rozmowy_otoczenia.md`).
- `--podziel-powyzej 1500000` — automatycznie dzieli księgi większe niż limit bajtów
  na części (`*_czesc_01.md`, ...) w granicach sekcji.

## Struktura wyjściowych czytanek

- `README.md` — metryczka edycji, pokrycie tłumaczeń per księga oraz spis treści.
- `00_prolog_i_przerywniki.md` — intro (`wds_oneday_intro_cutscene_data`), filmowy Prolog (`text_msg` 590291–590459), napisy filmowe (`entry_collect_movie_subtitle_data`) oraz przerywniki nieprzypisane bezpośrednio do zadań.
- `01_watek_glowny.md` — chronologiczny scenariusz Wątku Głównego według kolejności rozdziałów i łańcuchów zależności zadań (`tools/uklad_scen.py`), ze streszczeniami rozdziałów (`plot_recap_data`), przerywnikami, wizytówkami, wyborami gracza oraz zintegrowanym kontekstem (pierwsze wystąpienia bohaterów z encyklopedii bez spoilerów kolejnych historii oraz wzmiankowane przedmioty i techniki).
- `02_zadania_poboczne_i_swiat.md` — zadania poboczne pogrupowane według kategorii z adnotacją o nieliniowości w otwartym świecie.
- `03_encyklopedia_swiata.md` — kalendarium historyczne, regiony, sekty i frakcje, pełne biografie postaci Jianghu, kompendium świata, zapiski regionalne, księgi z gry strona po stronie oraz listy i poszlaki.
- `04_przedmioty_i_ekwipunek.md` — katalog wyposażenia i przedmiotów z opisami oraz historią fabularną.
- `05_sztuki_walki_i_zdolnosci.md` — style walki (`kongfu`), sztuki wewnętrzne (`xinfa`), techniki Jianghu i zdolności bojowe.

## Zasady tekstu i czytelności

- **Wyłącznie język polski:** nigdy nie wstawia cicho tekstów angielskich ani chińskich zamiast brakujących tłumaczeń.
- **Czysta proza bez kodów gry:** usuwa kody kolorów NetEase (zarówno `#[A-Z]` jak i 6-cyfrowe `#rrggbb` bez ucinania sąsiednich cyfr) oraz rozwija odnośniki rich-text `<Tekst|id|...>`.
- **Tabele zawijane do 120 znaków bez `<br>`:** dzięki wierszom kontynuacji pliki są czytelne zarówno w przeglądarkach Markdown, jak i zwykłych edytorach tekstu.
