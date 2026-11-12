# Stan projektu

Aktualizacja: **2026-11-12**. Punkt wejścia dla kolejnej sesji. Cel i kryteria
akceptacji: [CEL.md](CEL.md). Historia prób: [dziennik](EXPERIMENT_LOG.md).

## Gdzie jesteśmy

**Pierwszy pełny pakiet dla tłumacza jest zbudowany i przekazany właścicielowi**
(`paczka_dla_tlumacza_wwm_v1.zip` w folderze projektu na jego Dysku,
44 362 422 B, SHA-256 `c25ddd2d…76ecb0`; kopia `README.md` i manifestu:
[paczki/v1](../paczki/v1/README.md)). Cały obieg — wyciąg z plików gry, pakiet,
import zwrotki, łatka map tekstów, audyt aktualizacji i pakiet uzupełniający —
działa na prawdziwych plikach gry **w piaskownicy**. Opis i polecenia:
[PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md).

Przygotowano również **tryb cotygodniowej aktualizacji w zbieraczu**
(`collector/URUCHOM_AKTUALIZACJE.bat` + dzielenie dużych paczek w `spakuj_dane.ps1`),
**bezpieczny instalator Windows z kopią zapasową i przywracaniem** (`instalator/`,
`tools/build_installer_kit.py`) oraz **plan małej próby UI i polskich znaków**
([TEST_W_GRZE.md](TEST_W_GRZE.md), `tools/latka_testowa.py`).

**W grze nie sprawdzono niczego**: ani łatki, ani instalatora na prawdziwej
instalacji Steam, ani polskich znaków, ani kolejności scen. Nie ma jeszcze
żadnego przekładu (`tlumaczenie/` powstanie przy pierwszej zwrotce).

## Co wiadomo

- **Baza gry odczytana w całości** ([BAZA_GRY.md](BAZA_GRY.md)): `MANIFEST` →
  `indexN` → `dataN`, z warstwą aktualizacji (`index1001`/`1200`). 114 169
  z 114 171 tabel czyta się bez błędu, liczba wierszy zgadza się z `MANIFEST`
  w każdej tabeli. Narzędzie: `tools/baza_gry.py`.
- **Mapy tekstów z warstwami `_diff`** ([LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)):
  warstwa podmienia, dopisuje i kasuje wpisy; klient nakłada paczkę, potem
  `LocalData/Patch`. Narzędzie: `tools/mapa_tekstow.py`.
- **Wyciąg `index/` (`wwm-indeks-v2`)** w repozytorium: 483 190 unikalnych
  tekstów (chiński + angielski), 74 950 dialogów ze 186 025 kwestiami — każda
  w grupie mówcy — zadania, wybory, postacie z opisami, encyklopedia, miejsca.
  93,59% identyfikatorów mapy angielskiej ma wskazane źródło (tabelę albo scenę).
- **Poprzedni indeks był błędny** i został zastąpiony: stary parser przypisywał
  scenie numer i projekt sceny następnej, stąd „5 859 brakujących dialogów”
  i „`dialog_no` to grupa”. Brakujących dialogów nie ma.
- **Pakiet v1**: 73 373 sceny, 528 249 elementów, **485 047 miejsc `PL:`**
  (168 183 w scenach, 316 864 w widokach); każdy tekst ma dokładnie jedno
  miejsce na przekład (kontrola po zbudowaniu).
- **Kolejność scen** pochodzi z danych: 8 971 scen ma wpis w tabeli zadań,
  89 jest następstwem wyboru, 25 456 stoi „według numeru” za taką sceną
  (oznaczone w pakiecie jako kolejność z numeracji, nie powiązanie), 12 303 jest
  ułożonych według projektu, 26 554 to rozmowy tła według miejsca.
- **Płeć bohatera**: 1 860 kwestii ma osobne identyfikatory dla bohatera
  i bohaterki; w pakiecie mają osobne `PL:`.
- **Aktualizacja przyrostowa sprawdzona na danych**: różnica między paczką gry
  a stanem po `LocalData/Patch` to 387 nowych tekstów, 64 usunięte, 0 zmienionych
  scen; pakiet uzupełniający ma 387 miejsc `PL:`.
- Decyzje właściciela (bez zmian): język źródłowy chiński, angielski pomocniczo;
  własny przekład, bez cudzych polonizacji; tylko zmiany tekstu przy wyłączonej
  grze, bez wstrzykiwania i obchodzenia zabezpieczeń; teksty i indeksy w Git,
  poza Git tylko binarne pliki gry ([DATA_POLICY.md](DATA_POLICY.md)).
  Instalacja odniesienia: Steam, Windows, App ID `3564740`, build `25906190`
  ([STEAM_REFERENCE.md](STEAM_REFERENCE.md)). Warunków wydawcy nie
  potwierdziliśmy niezależnie; nie obiecujemy bezpieczeństwa konta.

| Obszar | Stan |
|---|---|
| Repozytorium i workflow | Ponad 325 testów (Linux + Windows PS 5.1); `check_repository.py` i `git diff --check` czyste; CI na Ubuntu i Windows × Python 3.11/3.12. |
| Odczyt plików gry | Baza tabel, dialogi, mapy tekstów z warstwami — odczytane i sprawdzone na całości danych. |
| Wyciąg i powiązania | `index/` w Git, deterministyczny, ze stałym podziałem plików. |
| Pakiet tłumacza | Wersja 1 zbudowana i przekazana. Generator, README, spisy, kontrola własna. |
| Import zwrotki | Gotowy i przetestowany; czeka na pierwszą zwrotkę. |
| Łatka i instalator Windows | `tools/zbuduj_latke.py` (`--mapa`, `--build-gry`) + `instalator/` (`ZAINSTALUJ.bat`, `PRZYWROC.bat`, `SPRAWDZ_STAN.bat`) + `tools/latka_testowa.py` i [TEST_W_GRZE.md](TEST_W_GRZE.md). Sprawdzone w Windows CI na fikcyjnej instalacji; **nie sprawdzone w grze**. |
| Aktualizacje gry | `collector/URUCHOM_AKTUALIZACJE.bat` (format `wwm-collection-v2`), dzielenie paczek w `spakuj_dane.ps1`, `audyt_aktualizacji.py` i pakiet uzupełniający działają. |
| Starsze prototypy | `translation_bundle`, `audit_translation_*`, modele przywracania i skaner plików ([TRANSLATION_BUNDLE.md](TRANSLATION_BUNDLE.md), [UPDATES_AND_RESTORE.md](UPDATES_AND_RESTORE.md), [TWO_APPLICATIONS.md](TWO_APPLICATIONS.md)) działają tylko na wymyślonych danych i **nie są częścią obiegu** opisanego wyżej. |

## Otwarte ustalenia

1. **Test w grze** — najważniejsza niewiadoma. Mała łatka (kilka widocznych
   napisów) pokaże, czy klient przyjmuje zmienione mapy, czy czcionki mają
   polskie znaki i jak zachowuje się przy aktualizacji. Wymaga planu, kopii
   oryginałów i sprawdzonego przywracania.
2. **Który język klienta zastępujemy.** Łatka przepisuje pliki podane
   w `--cel`; dotąd próbowano na mapie angielskiej.
3. **Chronologia** nie była sprawdzana w grze. 12 303 sceny bez wpisu zadania
   i 25 456 ułożonych według numeru czeka na lepsze źródło (skrypty `*.ets`
   zadań nie leżą w odczytanych tabelach).
4. **18 157 tekstów bez źródła** — są w mapie, nie wskazuje ich żadna odczytana
   tabela (prawdopodobnie interfejs zaszyty w skryptach klienta).
5. **Limity pól** — nieznane; pakiet podaje długości wersji angielskiej.
6. 700 766 identyfikatorów tylko chińskich pominięto jako niewyświetlane
   w kliencie zachodnim — hipoteza.
7. Dwie tabele rozmieszczenia obiektów (`spaces.s66027.spawn.*`) nie czytają
   się do końca; bez tekstów.
8. Licencja własnego kodu i przekładu — nie wybrana, brak `LICENSE`.

## Następny krok

1. Wykonać pierwszy mały test UI i polskich znaków w grze według
   [TEST_W_GRZE.md](TEST_W_GRZE.md) (przy użyciu `tools/latka_testowa.py`
   i `instalator/ZAINSTALUJ.bat` / `PRZYWROC.bat`).
2. Czekać na zwrotkę tłumacza → `tools/import_zwrotki.py` → commit `tlumaczenie/`.
3. Po każdym cotygodniowym patchu gry: właściciel klika
   `collector/URUCHOM_AKTUALIZACJE.bat`, następnie obieg z [PAKIET_TLUMACZA.md](PAKIET_TLUMACZA.md).
