# Czytanki Where Winds Meet (`tools/buduj_czytanki.py`)

Narzędzie `tools/buduj_czytanki.py` (z modułem powiązań `tools/powiazania_czytanek.py`)
generuje polskie czytanki `.md` oraz deterministyczne archiwum `WWM_CZYTANKI_PL.zip`
wzorowane na układzie SRW Y, rozszerzonym do trzyplikowego zestawu dla pełnego
korpusu Where Winds Meet (także bez żadnej straty treści spoza scen).

## Uruchomienie

Z pełnego lub częściowego magazynu `tlumaczenie/`:

```bash
python3 tools/buduj_czytanki.py \
  --magazyn tlumaczenie \
  --wyj-katalog dist/czytanki \
  --wyj-zip dist/WWM_CZYTANKI_PL.zip
```

Albo tylko dla Prologu i Wątku Głównego (z całym powiązanym z nimi kontekstem):

```bash
python3 tools/buduj_czytanki.py \
  --magazyn tlumaczenie \
  --tylko-watek-glowny \
  --wyj-katalog dist/czytanki_watek_glowny
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
  wyłącznie przetłumaczone kwestie, sceny i wpisy; `kompletne-rozdzialy` dopuszcza
  tylko w 100% ukończone sekcje/wiersze; `wszystko` buduje pełny szkielet z
  jawnymi markerami `[Brak polskiego tekstu (...)]`.
- `--plec oba | bohater | bohaterka` — obsługa kwestii zależnych od płci postaci
  gracza (`@id` w dialogach i pary w napisach cutscen; w trybie `oba` identyczne
  kwestie obojga wariantów są scalane w jedną linię).
- `--tylko-watek-glowny` — ogranicza `epizody.md` i `kontekst_scen.md` do Prologu
  i Wątku Głównego (oraz odfiltrowuje zadania poboczne i dialogi scen z `dodatkowe.md`).
- `--z-otoczeniem` — dołącza rozmowy świata i reakcje poza zadaniami do
  epizodów i kontekstu (gdy flaga jest wyłączona, nieużyte w `epizody.md` wpisy
  są zachowane w `dodatkowe.md`).
- `--podziel-powyzej N` — domyślnie `0` (jednolity zestaw trzyplikowy); podanie
  limitu bajtów `> 0` dzieli duże pliki na części (`*_czesc_01.md`, ...) w
  granicach nagłówków `## `, a jeśli pojedynczy dział przekracza limit — także
  wzdłuż podnagłówków `### ` i wierszy długich list/tabel.
- `--podglad-en` — jawny tryb podglądu samej formy i układu czytanek na tekstach
  angielskich z `index/` (do oceny przed rozpoczęciem tłumaczenia; domyślnie
  narzędzie działa wyłącznie po polsku).

## Struktura wyjściowych czytanek (`wwm-czytanki-v2`)

- `README.md` — metryczka edycji, pokrycie tłumaczeń oraz spis numerowanych epizodów.
- `epizody.md` — czysty, ciągły skrypt fabularny podzielony na spójnie
  ponumerowane `## Epizod E` i `### Scena E.S` (Prolog i intro otwierające,
  chronologiczny Wątek Główny, wątki poboczne z notką o otwartym świecie oraz
  pozostałe cutsceny/filmy/plansze), z narracjami z gry na start epizodu,
  rozpoznanymi mówcami (`You Xia` z obsługą przebrań, obsada ze struktur gry i
  rozpoznania audio/głosów cutscen) oraz wyborami gracza wskazującymi docelowe
  `Scena X.Y`.
- `kontekst_scen.md` — jeden samowystarczalny towarzysz kontekstowy o
  identycznych co do joty nagłówkach `## Epizod E` i `### Scena E.S`. Łączy przy
  każdej scenie wszystkie warstwy bazy gry:
  1. bezpośrednie powiązania po ID (`tasks`, `task_group_info`, `task_progress_light_info`,
     `task_progress_dark_info/group`, `task_progress_ending`, `opcje_npc`,
     `guider_task`, `region_game_config`, `spaces.*.region`),
  2. obsadę i profile postaci (`entity_attr`, `world_view_person_info`, cytaty
     `world_view_person_voice`, relacje `npc_amity_relation_data`, world bossowie,
     mistrzowie sekt),
  3. automatyczne dopasowania Aho-Corasick po frazach źródłowych sceny (frakcje
     `world_view_shili_data` wraz z ich kalendarium `world_view_history_info`,
     dziedzictwo sekt, podobszary map, poematy miejsc, karty ładowania, kompendium,
     zapiski regionalne, księgi, wyposażenie, przedmioty, stroje, tytuły,
     sztuki walki `kongfu`/`xinfa`/`jianghu_skills`/`qishu` i wpisy UI),
  4. poszlaki, listy i księgi powiązane jednoznacznym imieniem własnym postaci
     debiutującej na scenie.
  - **Anty-duplikacja:** każde hasło otrzymuje pełną kartę przy pierwszym
    wystąpieniu; kolejne sceny podają zwięzłe zbiorcze odesłanie (`*Wcześniej
    opisane:* ...` / `pełna karta przy pierwszym wystąpieniu: Scena E.S`).
  - **Ochrona przed spoilerami:** przy scenie podawany jest wyłącznie pierwszy
    wpis biografii i pierwsza historia relacji (`story_1`); dalsze odblokowywane
    wpisy spotkanych bohaterów znajdują się w sekcji końcowej `kontekst_scen.md`.
- `dodatkowe.md` — cały pozostały materiał ze świata gry spoza scen, sekwencji
  i przypisanych kart z `kontekst_scen.md`, bez jakichkolwiek luk (`100%`
  pokrycia pozostałych tekstów z `index/`, w tym z wykluczonych wcześniej tabel
  technicznych i tekstów bez nazwy tabeli źródłowej). Rozdzielony tematycznie na
  9 przejrzystych działów z bogatymi kartami/tabelami u góry oraz domykającym
  przebiegiem zero-luk na końcu każdego działu:
  1. Bohaterowie, NPC, relacje, bossowie i tytuły
  2. Zadania, wątki cienia, zakończenia i wskazówki
  3. Przedmioty, wyposażenie, stroje i budowle
  4. Encyklopedia świata, historia, księgi, poszlaki i listy
  5. Świat, regiony, miejsca i lokacje
  6. Sztuki walki, umiejętności, efekty i przeciwnicy
  7. Rozmowy, wybory i komunikaty poza scenami
  8. Osiągnięcia, poradniki, interfejs i systemy gry
  9. Pozostałe tabele i teksty bez przypisanej tabeli

## Zasady tekstu i czytelności

- **Wyłącznie język polski:** nigdy nie wstawia cicho tekstów angielskich ani
  chińskich zamiast brakujących tłumaczeń.
- **Czysta proza bez kodów gry:** usuwa kody kolorów NetEase (zarówno `#[A-Z]`
  jak i 6-cyfrowe `#rrggbb`) oraz rozwija odnośniki rich-text `<Tekst|id|...>`.
- **Tabele zawijane do 120 znaków bez `<br>`:** czytelne w każdym edytorze i
  przeglądarce Markdown.
