# Co się zmieniło w pakiecie v5 (2026-11-14)

Ten plik zastępuje dotychczasową instrukcję w zakresie, w którym się różni.
Zasady wypełniania `PL:` się nie zmieniły — nadal: jeden przekład w jednej linii
po `PL:`, kody gry (`{}`, `#M`, `#[A-Z]` itd.) bez zmian, klucza nie ruszamy.

## 1. Nowa sekcja: `cutsceny/04_sceny_cinematiczne_NN.md`

Sceny odtwarzane jako **przerywniki** (w danych `ui_type` 10) leżały dotąd
w `sceny/` razem ze zwykłymi kwestiami i ginęły w wielkim worku. Teraz mają
własny plik, w kolejności numerów scen, z mówcą i pełnym `EN`.

- **Razem: 11 677 elementów, z czego 9 109 do wpisania** (reszta to powtórzenia).
- Nagłówek sceny: `## Scena 10168 — dialog 10168 — projekt 对话-qiancen`.
- Te same kwestie **zniknęły z plików `sceny/`**: w ich miejscu stoi odsyłacz
  `tłumaczysz raz: 04_sceny_cinematiczne_…`. To **nie jest brak** — nie trzeba
  nic dopisywać w `sceny/`, tłumaczy się wyłącznie w nowej sekcji.
- Numeracja elementów w nagłówku pliku mówi, ile linii ma dana część.

## 2. Prolog jest już przetłumaczony — nie trzeba go robić

Te bloki mają przekład w magazynie (przygotowany redakcyjnie):

- pierwsza cutscena i ucieczka (`text_msg` około `590336–590360`),
- napisy `text_msg` `590000–592694` — **100%**,
- intro „One Day in the Imperial Service” — **100%**,
- napisy filmów 1–3 (w tym wiersze `钗头凤` i `中渡桥之战`) — **100%**,
- sceny przerywników `10094–10188` (prolog: dziedziniec, ucieczka) — **0 braków**.

Jeśli któraś z tych linii zostanie wypełniona ponownie, import jej nie odrzuci,
ale zgłosi `bez zmian` — nie ma sensu jej tłumaczyć drugi raz.

## 3. Warstwa „szara” napisów — nie wymaga pracy

Część napisów ma drugą wersję w tabeli `text_msg__grey` (mówca wpisany w treść,
np. `Master: …`). Te wiersze **dziedziczą przekład** z wiersza głównego
o tym samym numerze, więc nie trzeba ich wypełniać osobno. Jeśli jednak któraś
linia szarej warstwy nie ma bliźniaka, pojawi się w pakiecie normalnie.

## 4. Co jest najważniejsze dla nas w tej turze

Kolejność: **Prolog i wątek główny (rozdziały 1–2), potem reszta**. Nie trzeba
wypełniać tabel interfejsu i meta (`04_walka_i_umiejetnosci`, komunikaty itp.) —
to nie wpływa na odbiór fabuły.

## 5. Jak odesłać pracę

Bez zmian: same pliki `.md` (może być zip z katalogiem `sceny/`, `cutsceny/`,
`widoki/`), liczą się wyłącznie linie `klucz:` i `PL:`. Można odsyłać częściami
i wielokrotnie — import scali je bezstratnie, a powtórzony klucz z inną treścią
zostanie zgłoszony jako konflikt do rozstrzygnięcia.
