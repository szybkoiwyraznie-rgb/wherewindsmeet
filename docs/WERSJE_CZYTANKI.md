# Wersje Czytanki

Jedna wersja = jedna paczka, jeden numer, jeden wpis. **Nie nadpisujemy
poprzednich plików** i nie nazywamy ich datą (data się nie zmienia, a plik
w kółko ten sam). Nowa zawartość → nowy numer.

Paczka: `dist/WWM_Czytanka_PL_v<N>.zip`, budowana przez:

```bash
python3 tools/czytanka_czysta.py --wyj out/czytanka --wersja 4
```

`--wersja` sam składa ścieżkę `dist/WWM_Czytanka_PL_v4.zip` i **odmawia
nadpisania**, jeśli taka wersja już istnieje — wtedy trzeba podnieść numer.

| wersja | co się zmieniło | rozmiar | SHA-256 | Dysk Google |
|---|---|---|---|---|
| v4 | cutsceny rozdziału pierwszego wróciły do krainy: kotwicą grupy jest pierwsza scena **z przypisaną mapą** (pierwsza scena grupy pochodzi z `luwenxin.dialog`, który w wyciągu nie ma ani jednej mapy, więc cała grupa lądowała w „Scenach bez przypisanej mapy”); do tego cutsceny w grupie stoją w kolejności **zadań** (`przerywniki` w `index/zadania.jsonl`), a nie numerów. `## Cutscena 30161` (przebudzenie z Ruby, „Wodzu, obudź się!”) stoi teraz w krainie 燕南, przy pozostałych cutscenach rozdziału, ze swoimi 72 liniami napisów | 6 609 291 B | `0fe0461f28e7d89a1b53b0f6e6b2e502965b79380a716d42f4a7d5daa6afd85c` | `1WzykudtneN3nrsjVMVxVxpU7vB-C2xT4` |
| v3 | napisy przerywników (pula `text_msg`, 2 688 wierszy) wyszły z alfabetycznej reszty: te, których scenę da się rozpoznać po sprawie­dzonej kotwicy albo po nazwie nagrania, stoją **w swojej cutscenie** — m.in. `## Cutscena 30161` ma teraz całą scenę „Wodzu, obudź się!” (poemat 八俊结义, Ruby, streszczenie) zamiast samego streszczenia; pozostałe 44 bloki stoją w sekcji `# Napisy przerywników` w kolejności wierszy z pliku gry. W danych gry napis nie ma numeru cutsceny — numer siedzi w osi czasu cutsceny, której wyciąg z `index/` nie obejmuje | 6 610 597 B | `7e93e5a47af68c465c40efafbe023424bdf9761fef002d2cc99d48796418abd7` | `1c8pk1TBJE1jODrpl6IWSM2OkE9cEfTT5` |
| v2 | streszczenie cutsceny z prologu (`## Cutscena 30150`) stoi w prologu — między Prolog 3 i Prolog 4 — zamiast na końcu pliku; cutscena nie powtarza się nigdzie indziej; tabliczka krainy („QINGHE - VERDANT WILDS”) nie udaje już kwestii prologu | 6 607 212 B | `06eb1d2ad973e6924e9fd524bc0b5d56ce9e9cc6cfce1d448cc1f08c95c350a6` | `1uO_0v7fJOr1T0tbKho1rgWoh2ASLSYzq` |
| v1 | 02 pokazuje tylko hasła z prawdziwym opisem: definicje przedmiotów, frakcji, miejsc i sztuk walki oraz krótka tożsamość postaci z encyklopedii (`tozsamosc`); rozdziały fabularne encyklopedii (`historie`) i karty z samą nazwą usunięte; 501 jednostek z kontekstem | 6 607 191 B | `b7c84bee07a76b14ef44dfbe84e63a6448c71f3e8fe955541119c8c6235bc97a` | `15fZGPA4BPd6ZTss0gulX61JzXxBdwQpx` |

## Wersje sprzed wprowadzenia numeracji

Paczki nazwane datą (`WWM_Czytanka_PL_2026-11-15.zip`) są nieaktualne i leżą
w koszu na Dysku Google; zastąpiła je wersja `v1`.
