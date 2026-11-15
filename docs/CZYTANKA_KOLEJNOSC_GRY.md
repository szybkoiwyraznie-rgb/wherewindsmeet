# Czytanka w kolejności z gry (`tools/buduj_czytanke_gry.py`)

Czytanka dla właściciela projektu: cała narracja Where Winds Meet ułożona tak,
jak gra ją pokazuje — bez zgadywania i bez pomijania scen. Różni się od
`docs/CZYTANKI_WWM.md` (tam: korpus fabuły i encyklopedii w układzie działów),
bo tu jedynym kryterium jest **kolejność występowania w grze**.

## Zasady porządku

| poziom | co porządkuje | skąd dane |
|---|---|---|
| 1 | prolog | transkrypt właściciela sprawdzony linia w linię (`zwrotki/prolog_wg_klucza.md`) |
| 2 | krainy (mapy) | kolejność odwiedzania z łańcucha zadań: `pian`, `przestrzen`, `index/prowincje.json` |
| 3 | sceny w krainie | numer dialogu rosnąco — numeracja autorska gry |
| 4 | wnętrze sceny | `time`/`order` z `dialog_timelines`; napisy puli po `id`; filmy po `time` |
| 5 | warianty | w toku pierwszy wariant z danych, pozostałe w aneksie prologu |

Prolog jest pierwszy i to on wyznacza początek gry. Krainy liczy
`tools/prowincje.py`: każde zadanie ma mapę (`przestrzen`) i część rozdziału
(`pian`), więc kraina, której zadania zaczynają się najwcześniej, jest pierwsza.
Mapy grupuje się po nazwie roboczej do dwóch znaków chińskich, bo gra trzyma ten
sam teren dwa razy — oryginał i `任务重制_…` („przerobiony”).

## Co trafia do których plików

| plik | zawartość |
|---|---|
| `00_prolog.md` | prolog w kolejności z transkryptu, z aneksem wariantów otwarcia |
| `k01_…` … `k92_…` | krainy w kolejności odwiedzania; sceny po numerze dialogu |
| `90_filmy.md` | trzy filmy otwierające: pieśń o lampionach, `钗头凤`, `中渡桥之战` |
| `91_napisy_przerywnikow.md` | pozostałe wiersze puli `text_msg`/`text_msg__grey`, po `id` |
| `95_bez_mapy.md` | dialogi projektów, których żadna scena nie wskazuje mapy |

Scena bez mapy dziedziczy krainę po swoim projekcie (`对话-*`), jeśli inne sceny
tego projektu mapę mają — dzięki temu np. `对话-qiancen` z prologu nie wypada
z 燕南. Sceny, które prolog wyczerpuje (co najmniej 80% linii pada w transkrypcie),
nie są powtarzane w krainach.

## Liczby (2026-11-14)

- 92 krainy, 285 map; pierwsze: 燕南 → 清河 → 熔炉 → 河西 → …
- 72 977 scen, 291 426 linii, w tym 28 356 z polskim
- 36 scen wyczerpanych przez prolog, 13 589 scen bez mapy w 129 projektach
- 105 135 wierszy puli napisów, 3 filmy
- poza narracją zostaje 66 997 przetłumaczonych kluczy (przedmioty, umiejętności,
  cele zadań, UI) — one są w paczce językowej, nie w scenach

## Uruchomienie

```bash
# pełna czytanka: chiński + angielski + polski („—” gdy brak przekładu)
python3 tools/buduj_czytanke_gry.py --wyj out/czytanka \
    --zip dist/WWM_Czytanka_Gry.zip

# wariant do czytania: tylko linie z polskim
python3 tools/buduj_czytanke_gry.py --wyj out/czytanka_pl --zakres przetlumaczone \
    --zip dist/WWM_Czytanka_Gry_tylko_PL.zip

# odświeżenie kolejności krain, gdy dojdzie nowy wyciąg
python3 tools/prowincje.py --index index --wyj index/prowincje.json
```

Duże krainy są dzielone na części po 1 500 scen (`k01_燕南_cz01.md`,
`k02_…`), więc żaden plik nie rośnie do rozmiarów nieczytelnych dla edytora.

## Znane granice — świadome, nie zgadywane

- **Powrót do wcześniejszej krainy.** Jeśli fabuła wraca na zwiedzoną już mapę,
  jej sceny stają przy pierwszej wizycie. Poprawiamy to punktowo, nie przez
  przestawianie całego porządku.
- **Projekty bez mapy.** 129 projektów nie wskazuje żadnej mapy i nie da się ich
  wpisać w kolejność krain z danych — stoją w `95_bez_mapy.md`, po projekcie
  i numerze dialogu. Nic nie znika.
- **Warianty.** Ta sama kwestia w różnych odgałęzieniach to osobne sceny o własnych
  numerach; w toku zostaje pierwsza z danych, reszta jest w aneksie prologu.
- **Kolejność filmów wobec prologu** nie wynika z danych: `entry_collect…` numeruje
  filmy 1–3, ale nie mówi, kiedy lecą. Dlatego stoją w osobnym pliku.
- Wszystko powyższe to porządek **z danych**. Że w grze czyta się to tak samo,
  potwierdzi dopiero przejście właściciela — patrz `docs/TEST_W_GRZE.md`.
