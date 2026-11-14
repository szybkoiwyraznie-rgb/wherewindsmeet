# Cel projektu i kryteria akceptacji paczki dla Tłumacza

Zapis polecenia właściciela z **2026-11-11**. To jest punkt odniesienia dla
każdej sesji: jeśli praca nie przybliża do tego celu, jest zbędna. Nie pytaj
właściciela o rzeczy, które są tu rozstrzygnięte.

## Zadanie

Zbudować **paczkę ZIP dla Tłumacza** w układzie paczki SRW Y
(`plik_dla_tlumacza_v8.zip` na Dysku właściciela: `README.md` + `sceny.zip` +
`widoki.zip`), z zachowaniem różnic między grami.

1. Zwrotka Tłumacza ma pozwalać zbudować **patcher**, który wstrzyknie
   tłumaczenia do odpowiednich plików gry.
2. Gra jest sieciowa i dostaje aktualizacje co najmniej raz w tygodniu.
   Pipeline musi działać **przyrostowo**:
   nowy patch gry → audyt zmian → paczka uzupełniająca dla Tłumacza →
   nowy patch tłumaczenia.

## Kryteria akceptacji

| wymaganie | miara |
|---|---|
| pełność | 100% tekstów wydanych w kliencie globalnym (obecność wersji `EN` wyznacza zakres; tłumaczenie z `ZH` z `EN` jako pomocą — wpisy wyłącznie chińskie bez `EN` pomijane do czasu wydania w Global jako „patch tłumaczenia”), plus sceny i postacie |
| mówcy | 100% kwestii przypisanych do mówcy |
| sceny | 100% scen z granicami |
| chronologia | zweryfikowana przynajmniej dla wątku głównego; jeśli się nie da, kolejność według numeracji z danych gry, która ją zastępuje |
| `sceny.zip` | chronologicznie, podział na jasne sceny; każda scena z kontekstem: występujące osoby z opisami z encyklopedii gry, miejsce akcji itd. |
| `widoki.zip` | treści pozasceniczne w sensownych grupach: przedmioty, miejsca, encyklopedia, opisy zadań itd. |

Drobne braki są dopuszczalne — właściciel zgłosi je podczas gry.

## Jak pracujemy

- **Pliki gry:** właściciel wrzuca pliki gry na Dysk Google (folder
  `Where Winds Meet`) **wyłącznie na potrzeby etapu eksploracji i aktualizacji
  wyciągu `index/`**. Po zbudowaniu `index/` wszystkie narzędzia potoku
  (pakiety dla tłumacza, Czytanki, audyt aktualizacji, łatka testowa oraz
  `WWM_LATKA_PL.zip` ze zwrotek) działają **w 100% samowystarczalnie na
  samym repozytorium (`index/` + `tlumaczenie/`)**, bez pobierania binarnych
  plików gry z Dysku Google i bez pakowania zmodyfikowanych plików gry do
  dystrybuowanej łatki ([OVERSEA_INWENTARZ.md](OVERSEA_INWENTARZ.md),
  [PATCHER_WWM.md](PATCHER_WWM.md)).
- **Skrypty u właściciela:** agent przygotowuje ZIP z BAT-em i skryptem
  (`ps1` albo `py`), właściciel go uruchamia, wynik ląduje na pulpicie i wraca
  przez Dysk. Wzór: `collector/`. Właściciel dopuszcza też skrypty czytające
  dane z działającej gry — sięgać po to dopiero wtedy, gdy plików nie da się
  odczytać statycznie, i opisać ryzyko dla konta.
- **Nie powtarzać zrobionej pracy:** najpierw [STATUS.md](STATUS.md),
  [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md), [BAZA_GRY.md](BAZA_GRY.md).
- **Korzystać z cudzej wiedzy technicznej:** fanowskie tłumaczenia
  (indonezyjskie, polskie) i narzędzia do plików gry — odnośniki w
  [PRIOR_ART.md](PRIOR_ART.md). Analizujemy formaty i kod, nie kopiujemy
  cudzych tłumaczeń.
- **Wszystko zapisywać i od razu wypychać:** każdy spójny krok to commit i push
  na gałąź sesji oraz roboczy PR. Do Git trafiają teksty, indeksy, powiązania,
  wnioski i dokumentacja. **Poza Git zostają wyłącznie binarne pliki gry.**
