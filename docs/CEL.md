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
| pełność | 100% tekstów gry, scen i postaci |
| mówcy | 100% kwestii przypisanych do mówcy |
| sceny | 100% scen z granicami |
| chronologia | zweryfikowana przynajmniej dla wątku głównego; jeśli się nie da, kolejność według numeracji z danych gry, która ją zastępuje |
| `sceny.zip` | chronologicznie, podział na jasne sceny; każda scena z kontekstem: występujące osoby z opisami z encyklopedii gry, miejsce akcji itd. |
| `widoki.zip` | treści pozasceniczne w sensownych grupach: przedmioty, miejsca, encyklopedia, opisy zadań itd. |

Drobne braki są dopuszczalne — właściciel zgłosi je podczas gry.

## Jak pracujemy

- **Pliki gry:** właściciel wrzuca dowolne pliki na Dysk Google (folder
  `Where Winds Meet`); agent pobiera je connectorem do ignorowanego
  `google_drive/` i rozpakowuje do `local/`. Lista i sumy:
  [OVERSEA_INWENTARZ.md](OVERSEA_INWENTARZ.md).
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
