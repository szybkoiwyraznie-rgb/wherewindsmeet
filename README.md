# Where Winds Meet — polska wersja językowa

Nieoficjalny projekt polskiej wersji gry **Where Winds Meet**. Proces:
pliki gry → wyciąg `index/` → pakiet dla tłumacza → import zwrotki do magazynu
`tlumaczenie/` → łatka map tekstów (oraz powtarzalny obieg przyrostowy po
aktualizacjach gry). Cel i kryteria akceptacji opisuje [docs/CEL.md](docs/CEL.md).

**Stan (2026-11-12): pierwszy pełny pakiet dla tłumacza (`v1`) oraz pakiet `v3` (`--tylko-z-en`) są zbudowane
i przekazane właścicielowi**, a cały obieg po stronie narzędzi (ekstrakcja bazy, budowa
pakietu, trzyplikowe Czytanki, import zwrotki, samowystarczalna łatka `patcher_wwm.py`,
audyt aktualizacji i pakiet uzupełniający) działa na prawdziwych plikach buildu `25906190`.
**Zweryfikowano w uruchomionej grze (Steam Windows):** mała łatka testowa (`tools/latka_testowa.py` —
menu, ustawienia i napisy otwierającego prologu) załadowała się w kliencie bez problemu, a czcionki gry
wyświetliły komplet polskich znaków diakrytycznych (`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`).
**Wciąż czeka na sprawdzenie:** pełna łatka fabularna (brak jeszcze zwrotki przekładu w `tlumaczenie/`)
oraz bezpośrednie uruchomienie nowego samowystarczalnego instalatora `patcher_wwm.py` w oknie gry
(zachowuje sprawdzony format map binarnych i przeszedł testy na Linux + Windows CI). Gotowy jest także tryb cotygodniowych aktualizacji zbieracza (`collector/URUCHOM_AKTUALIZACJE.bat`),
bezpieczne kopie zapasowe i przywracanie oryginałów oraz opis testu ([docs/TEST_W_GRZE.md](docs/TEST_W_GRZE.md)). Właściciel dopuszcza wyłącznie zmiany tekstów przy wyłączonej
grze, bez wstrzykiwania i obchodzenia zabezpieczeń; warunków wydawcy nie
potwierdziliśmy niezależnie i nie obiecujemy bezpieczeństwa konta.

## Od czego zacząć

- [Stan projektu](docs/STATUS.md) oraz [cel i kryteria akceptacji](docs/CEL.md)
- [Pakiet dla tłumacza i potok aktualizacji](docs/PAKIET_TLUMACZA.md) — pełna instrukcja obsługi obiegu
- [Baza danych gry (`MANIFEST` → `indexN` → `dataN`)](docs/BAZA_GRY.md)
- [Kontener map tekstów i warstwy `_diff`](docs/LOCALE_CONTAINER.md), [patcher i one-click ze zwrotki](docs/PATCHER_WWM.md), [czytanki `.md` z fabuły i encyklopedii](docs/CZYTANKI_WWM.md) oraz [plan pierwszego testu w grze](docs/TEST_W_GRZE.md)
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
