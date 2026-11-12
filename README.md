# Where Winds Meet — polska wersja językowa

Nieoficjalny projekt polskiej wersji gry **Where Winds Meet**. Proces:
pliki gry → wyciąg `index/` → pakiet dla tłumacza → import zwrotki do magazynu
`tlumaczenie/` → łatka map tekstów (oraz powtarzalny obieg przyrostowy po
aktualizacjach gry). Cel i kryteria akceptacji opisuje [docs/CEL.md](docs/CEL.md).

**Stan (2026-11-12): pierwszy pełny pakiet dla tłumacza (`v1`) jest zbudowany
i przekazany właścicielowi** (`485 047` miejsc `PL:` na `73 373` sceny i `62`
pliki widoków). Cały obieg po stronie narzędzi (ekstrakcja bazy, budowa
pakietu, import zwrotki, łatka bazy i warstw `_diff`, audyt aktualizacji
i pakiet uzupełniający) działa na prawdziwych plikach buildu `25906190` w
piaskownicy, ale **nie był jeszcze sprawdzony w uruchomionej grze**. Gotowy jest także tryb cotygodniowych aktualizacji zbieracza (`collector/URUCHOM_AKTUALIZACJE.bat`),
bezpieczny instalator/przywracacz łatki dla Windows (`instalator/`) oraz plan
pierwszej próby UI, napisów prologu i polskich znaków ([docs/TEST_W_GRZE.md](docs/TEST_W_GRZE.md)). Brakuje
jeszcze pierwszej zwrotki przekładu oraz samego testu na uruchomionej grze. Właściciel dopuszcza wyłącznie zmiany tekstów przy wyłączonej
grze, bez wstrzykiwania i obchodzenia zabezpieczeń; warunków wydawcy nie
potwierdziliśmy niezależnie i nie obiecujemy bezpieczeństwa konta.

## Od czego zacząć

- [Stan projektu](docs/STATUS.md) oraz [cel i kryteria akceptacji](docs/CEL.md)
- [Pakiet dla tłumacza i potok aktualizacji](docs/PAKIET_TLUMACZA.md) — pełna instrukcja obsługi obiegu
- [Baza danych gry (`MANIFEST` → `indexN` → `dataN`)](docs/BAZA_GRY.md)
- [Kontener map tekstów i warstwy `_diff`](docs/LOCALE_CONTAINER.md), [patcher](docs/PATCHER_WWM.md) oraz [plan pierwszego testu w grze](docs/TEST_W_GRZE.md)
- [Dziennik eksperymentów](docs/EXPERIMENT_LOG.md) i [zestawienie dostaw z gry](docs/OVERSEA_INWENTARZ.md)
- [Plan etapów](docs/ROADMAP.md), [wykonalność i ryzyka](docs/FEASIBILITY.md),
  [wybór wersji Windows](docs/WINDOWS_OPTIONS.md), [zbieracz ZIP dla Windows](docs/COLLECTOR.md),
  [zgłoszona instalacja Steam](docs/STEAM_REFERENCE.md),
  [zasady pracy z danymi gry](docs/DATA_POLICY.md), [sposób pracy](docs/WORKFLOW.md)
- [Środowisko i uruchamianie kontroli](ENVIRONMENT.md)
- [Instrukcje dla agentów](AGENTS.md)
- [Źródła wzorców z projektu SRW](docs/PRIOR_ART.md)

Podstawowe kontrole repozytorium (bez danych gry; czytanie plików gry wymaga
dodatkowo `pip install -r requirements-dev.txt`):

```sh
python tools/check_repository.py
python tools/run_tests.py
```

## Układ repozytorium

```text
.github/       CI (Ubuntu i Windows × Python 3.11/3.12) i szablony współpracy
collector/     źródła zbieracza Windows (rozpoznanie + cotygodniowe aktualizacje)
instalator/    bezpieczny instalator Windows z kopią zapasową i przywracaniem
docs/          status, dokumentacja formatów, potoku, plan testu i dziennik
index/         wersjonowany wyciąg bazy i tekstów (wwm-indeks-v2)
paczki/        archiwalne README i manifesty kolejnych wysłanych pakietów
tools/         czytnik bazy, wyciąg, generator pakietu, importer, łatka, audyt i kontrole
tests/         testy jednostkowe i integracyjne bez plików gry
local/         prywatny katalog roboczy z plikami gry, ignorowany przez Git
build/, dist/  lokalne wyniki (np. zbudowane archiwa ZIP), ignorowane przez Git
```

Do Git trafiają teksty, wyciąg `index/`, własny kod, narzędzia i dokumentacja
([DATA_POLICY.md](docs/DATA_POLICY.md)); **wyłącznie binarne pliki gry oraz ich
zmodyfikowane kopie** zostają poza Git. Projekt nie jest powiązany z twórcami gry.
