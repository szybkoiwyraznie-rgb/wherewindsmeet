# Wersje Czytanki

Jedna wersja = jedna paczka, jeden numer, jeden wpis. **Nie nadpisujemy
poprzednich plików** i nie nazywamy ich datą (data się nie zmienia, a plik
w kółko ten sam). Nowa zawartość → nowy numer.

Paczka: `dist/WWM_Czytanka_PL_v<N>.zip`, budowana przez:

```bash
python3 tools/czytanka_czysta.py --wyj out/czytanka --wersja 2
```

`--wersja` sam składa ścieżkę `dist/WWM_Czytanka_PL_v2.zip` i **odmawia
nadpisania**, jeśli taka wersja już istnieje — wtedy trzeba podnieść numer.

| wersja | co się zmieniło | rozmiar | SHA-256 | Dysk Google |
|---|---|---|---|---|
| v1 | 02 pokazuje tylko hasła z prawdziwym opisem: definicje przedmiotów, frakcji, miejsc i sztuk walki oraz krótka tożsamość postaci z encyklopedii (`tozsamosc`); rozdziały fabularne encyklopedii (`historie`) i karty z samą nazwą usunięte; 501 jednostek z kontekstem | 6 607 191 B | `b7c84bee07a76b14ef44dfbe84e63a6448c71f3e8fe955541119c8c6235bc97a` | `15fZGPA4BPd6ZTss0gulX61JzXxBdwQpx` |

## Wersje sprzed wprowadzenia numeracji

Paczki nazwane datą (`WWM_Czytanka_PL_2026-11-15.zip`) są nieaktualne i leżą
w koszu na Dysku Google; zastąpiła je wersja `v1`.
