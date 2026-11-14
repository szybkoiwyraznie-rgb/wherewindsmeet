# Where Winds Meet — pakiet dla tłumacza (chiński → polski), wersja 1

To jest cały tekst gry w zasięgu klienta zachodniego: wszystkie dialogi z podziałem na sceny i mówców oraz wszystkie nazwy, opisy i komunikaty z tabel gry. Tłumaczy się **tekst w plikach `.md`**, wpisując polski po znaczniku `PL:`. Nie trzeba znać formatów gry ani żadnych narzędzi.

Dane gry: Steam 3564740, build 25906190, pliki z 2026-11-11. Pakiet zbudowano 2026-11-12.
Źródłem przekładu jest **tekst chiński**; angielska wersja gry stoi obok jako pomoc (nazwy, terminy).

## 0. W skrócie

1. Rozpakowujesz **`sceny.zip`** — dialogi: 73 373 scen, 203 943 elementów (kwestie, plansze, wybory gracza). Do wpisania: **168 183 linii `PL:`**. Każda scena ma w nagłówku zadanie, miejsce i uczestników; `spis-misji.md` i `spis-scen.md` w tym samym zipie pokazują układ całości.
2. Rozpakowujesz **`widoki.zip`** — teksty spoza scen w grupach: postacie, zadania, przedmioty, walka, świat, encyklopedia, komunikaty, interfejs. Do wpisania: **316 864 linii `PL:`** (razem w pakiecie **485 047**).
3. Pod każdym tekstem chińskim są linie `EN:` (angielska wersja gry jako odniesienie) i `PL:` — **polski wpisujesz po `PL:`**.
4. Odsyłasz pliki **tak jak są** (może być zip). Nie zmieniasz nazw plików, linii `klucz:` ani tekstu chińskiego.

## 1. Jak wygląda jeden element

```text
14. [Kwestia — 红线 (Ruby)] 造成#Y{0}#E点伤害\n持续三息。
   klucz: 693cf29aef2cf70a
   tokeny: zachowaj dokładnie: #Y, {0}, #E
   EN: Deals #Y{0}#E damage\nfor three breaths.
   PL:
```

- Pierwsza linia: numer, rodzaj elementu z mówcą albo polem gry w nawiasie i **tekst chiński**.
- `klucz:` — po tej linii narzędzia znajdują tekst w grze. Nie zmieniaj jej.
- `tokeny:` — kody gry, które muszą zostać w przekładzie dokładnie takie same (punkt 2.4).
- `limit:` (tylko w widokach) — orientacyjna długość, punkt 3.
- `dotyczy:` (tylko w widokach) — nazwa rzeczy, której dotyczy opis (np. nazwa przedmiotu przy jego opisie).
- `EN:` — angielska wersja gry. Pomaga w nazwach i terminach, ale tłumaczymy z chińskiego.
- `PL:` — tu wpisujesz polski, w tej samej linii co znacznik.
- `\n` w tekście to **przejście do nowej linii** w grze. W polskim wstaw `\n` tam, gdzie ma być nowa linia.

## 2. Zasady

1. **Piszesz tylko po `PL:`.** Linie nad `PL:` są nienaruszalne.
2. **Nie zmieniasz numerów, kolejności ani linii `klucz:`.**
3. **Cały przekład jednego elementu stoi w jednej linii po `PL:`.** Nowa linia w grze to `\n` wpisane w tekst, nie Enter.
4. **Nie tłumaczysz kodów gry** — zostają dokładnie takie, jakie są. Najczęstsze: `#E`, `#Y`, `{}`, `%s`, `{0}`, `#G`, `#R`, `{1}`, `#H`, `#a66829`, `#ffc89c`, `%d`, `{prop}`, `$T(2001)`. Linia `tokeny:` pod elementem wylicza wszystkie kody tego elementu. `#Y…#E` to kolor (początek i koniec), `{0}`, `{}`, `%s`, `%d` to miejsca, w które gra wstawia liczbę albo nazwę, `$T(…)` to wartość wyliczana przez grę. W odnośniku `<nazwa|780|#C|15>` tłumaczysz tylko `nazwa`; część od pierwszej kreski `|` do `>` zostaje bez zmian.
5. **Jedna nazwa — jedna pisownia** w całym pakiecie. Imiona i nazwy ustalasz w `widoki/00_postacie_*.md`, `03_przedmioty_*.md`, `05_swiat_i_miejsca_*.md` i tak samo piszesz je w dialogach.
6. Spacje na początku i końcu tekstu dopisują narzędzia — nie musisz ich odtwarzać.

## 3. Długość tekstu

**W danych gry nie ma limitów długości pól i nie zostały one zmierzone w grze.** Dlatego pakiet podaje tylko to, co da się policzyć:

- **Kwestie w scenach** nie mają linii `limit:`. Trzymaj się długości wersji angielskiej: połowa angielskich kwestii ma do 59 znaków, 95% do 152, 99% do 200, najdłuższa 522.
- **Widoki:** `limit: do N znaków`, gdzie `N` to długość najdłuższego tekstu angielskiego **w tym samym polu gry** (np. we wszystkich nazwach przedmiotów). To wiadomość „tyle gra na pewno wyświetla w tym polu”, a nie pomiar okna. Przy wątpliwości wybierz krótszy wariant.
- Jeśli w grze coś się nie zmieści, właściciel zgłosi to i dostaniesz poprawioną listę — bez zgadywania z góry.

## 4. Polskie znaki i interpunkcja

Pisz normalną polszczyzną z `ą ć ę ł ń ó ś ź ż`. **Nie sprawdzono jeszcze w grze, czy jej czcionki mają wszystkie polskie znaki** — to zadanie dla narzędzi i pierwszego testu w grze, nie dla tłumacza. Chińskie znaki interpunkcyjne (`，。！？“”「」……`) zamieniaj na polskie odpowiedniki; wielokropek `……` to zwykłe `...`.

## 5. Elementy bez `PL:`

- `(powtórzenie elementu N — nie wpisuj tu nic)` — ten sam tekst jest wyżej w tej samej scenie.
- `(powtórzenie — tłumaczysz raz: plik, scena N, element M)` — ten sam tekst ma swoje `PL:` we wskazanym miejscu; przekład dziedziczy się sam.
- `PL (już jest): …` — tekst został już przetłumaczony; pokazany dla kontekstu.
- `EN: (brak wersji angielskiej w grze)` — tłumaczysz z chińskiego jak resztę.
- `EN: (to jest tekst źródłowy — chińskiej wersji nie ma w danych)` — najnowsze teksty gry mają na razie tylko wersję angielską; pierwsza linia elementu jest wtedy po angielsku i z niej tłumaczysz.

## 6. Bohater i bohaterka

Gracz wybiera płeć postaci. Dane gry mają dla części kwestii **osobne tory dla bohatera i bohaterki** — takich kwestii jest 1 860. Mają w etykiecie `wariant: bohater` albo `wariant: bohaterka` i klucz zaczynający się od `@` (osobne miejsce w grze dla każdej wersji), więc możesz — i powinieneś — użyć właściwego rodzaju („zrobiłem” / „zrobiłam”), także gdy tekst chiński obu wersji jest jednakowy. Dotyczy to też kwestii innych postaci w takich torach: zwracają się do mężczyzny albo do kobiety. Jeśli polskie zdanie brzmi jednakowo w obu wersjach, wystarczy wpisać je przy jednym wariancie — drugi wariant tego samego tekstu chińskiego, zostawiony pusty, odziedziczy przekład.

Pozostałe kwestie gracza (37 407) i kwestie skierowane do niego są **wspólne dla obu płci**. Jeśli polskie zdanie wymaga rodzaju, wybierz formę neutralną: czas teraźniejszy, bezokolicznik, konstrukcję bezosobową („Udało się”, „Trzeba iść”). Nie zgaduj płci — błędny rodzaj jest gorszy niż zdanie neutralne.

## 7. Mówcy

Każda kwestia (186 025) leży w danych gry w grupie jednego mówcy — przypisanie jest odczytane z budowy sceny, nie zgadywane z treści (kwestii bez grupy mówcy: 0).

- `gracz` — postać gracza (37 407 kwestii).
- `红线 (Ruby)` — nazwa z gry: z tabliczki nad postacią albo z samej sceny (111 398 kwestii). W nawiasie wersja angielska.
- `江湖人*` — **gwiazdka**: gra nie ma dla tego mówcy nazwy na ekranie; to robocza etykieta twórców (37 168 kwestii). Jeśli taki sam chiński napis jest w grze nazwą postaci, w nawiasie stoi jej wersja angielska. Etykiety się nie tłumaczy — służy do rozpoznania, kto mówi.
- `???` — mówca bez nazwy i bez etykiety (52 kwestii).
- W nagłówku sceny `uczestnicy:` wymienia mówców z tytułem i opisem postaci z danych gry (jeśli gra je ma), a `obecni bez kwestii:` — postacie, które w scenie są, ale nic nie mówią.

## 8. Kolejność scen

Gra nie ma jednej listy „scena po scenie”. Kolejność w `sceny.zip` wynika z danych gry, od najmocniejszych do najsłabszych (szczegóły i liczby: `spis-scen.md`):

1. **Zadania.** Tabela zadań wskazuje dialogi wprost, a zadania tworzą łańcuch poprzedników. Pliki `NN_watek-glowny_…` to wątek główny po rozdziałach, dalej pozostałe rodzaje zadań (każdy rodzaj w osobnej serii plików). Scen w plikach zadań: 34 516, w tym w wątku głównym 2 445.
2. **Numeracja.** 25 456 z tych scen nie ma własnego wpisu w tabelach zadań; stoją za sceną, z którą sąsiadują numerem w tym samym projekcie. W nagłówku jest wtedy napisane `brak wpisu w tabelach zadań — scena ułożona według numeru`. To kolejność z numeracji gry, nie stwierdzone powiązanie z zadaniem.
3. **`80_dialogi-wg-projektow_NN.md`** — 12 303 scen bez żadnego wpisu zadania, według projektu (pliku roboczego twórców) i numeru.
4. **`90_rozmowy-tla_NN.md`** — 26 554 scen wskazywanych tylko przez rozmieszczenie NPC w świecie: pogawędki, powitania, reakcje. Pogrupowane według miejsca.

**Kolejności nie sprawdzono w grze.** Łańcuch zadań pochodzi z danych i w wątku głównym jest spójny (żadne zadanie nie stoi przed swoim poprzednikiem; w całej grze 36 razy łańcuch zamykał się w pętlę i został przerwany), ale część scen fabularnych wywołują skrypty, których w plikach tabel nie ma — te sceny trafiły do punktu 2 albo 3.

## 9. Widoki

Każdy tekst spoza scen stoi przy tabeli i polu gry, z którego pochodzi (`[tabela · pole · wiersz]`). Podział na pliki:

| pliki | co zawiera | plików | elementów | do wpisania `PL:` |
|---|---|---:|---:|---:|
| `00_postacie_NN.md` | Postacie: imiona, tytuły, opisy, encyklopedia osób | 5 | 26 045 | 25 905 |
| `01_zadania_NN.md` | Zadania: nazwy, cele, opisy i podsumowania | 4 | 20 067 | 20 010 |
| `02_wybory_i_rozmowy_NN.md` | Wybory gracza i teksty rozmów spoza scen | 3 | 15 996 | 10 179 |
| `03_przedmioty_NN.md` | Przedmioty, wyposażenie, stroje, budowle | 7 | 35 736 | 35 700 |
| `04_walka_i_umiejetnosci_NN.md` | Walka: umiejętności, efekty, talenty, przeciwnicy | 5 | 22 522 | 22 498 |
| `05_swiat_i_miejsca_NN.md` | Świat: miejsca, regiony, mapy, obiekty | 3 | 13 111 | 13 085 |
| `06_encyklopedia_i_ksiegi_NN.md` | Encyklopedia, księgi, zapiski, listy, przerywniki | 7 | 19 572 | 19 045 |
| `07_komunikaty_NN.md` | Komunikaty i dymki (text_msg i pokrewne) | 18 | 114 771 | 114 245 |
| `08_interfejs_i_systemy_NN.md` | Interfejs i systemy gry | 4 | 21 606 | 21 550 |
| `09_pozostale_NN.md` | Pozostałe tabele | 3 | 16 720 | 16 490 |
| `10_bez_zrodla_NN.md` | Teksty, których nie wskazuje żadna tabela ani scena | 3 | 18 160 | 18 157 |

`10_bez_zrodla` to teksty, które są w mapie tekstów gry, ale nie wskazuje ich żadna odczytana tabela ani scena (93.59% identyfikatorów tekstu ma wskazane źródło). Nie wiadomo, gdzie gra ich używa — przekład jest potrzebny, kontekstu brak.

## 10. Co odsyłasz

Te same pliki `.md` z wypełnionymi liniami `PL:` — wszystkie albo tylko te, nad którymi pracowałeś. Może być zip. Puste `PL:` znaczy „jeszcze nie przetłumaczone” i niczego nie psuje; można odsyłać partiami.

## 11. Czego w pakiecie nie ma

- 700 766 identyfikatorów tekstu, które istnieją tylko w chińskiej mapie i których nie wskazuje żadna tabela ani scena — klient zachodni nie ma dla nich żadnej wersji językowej, więc ich nie wyświetla.
- 1 577 dialogów bez żadnego tekstu (same animacje i dźwięk).
- Tekstów zaszytych w grafikach, filmach i w samym programie gry.

Błędy i braki zgłaszaj z nazwą pliku i numerem sceny albo elementu — po numerze dialogu i kluczu da się dojść do danych gry.
