# Instalacja referencyjna — Steam na Windows

## Dane przekazane przez właściciela

| Co pokazano lub opisano | Wartość | Źródło i ograniczenie |
|---|---|---|
| Steam App ID | `3564740` | Zrzut właściwości Steam; identyfikator aplikacji. |
| Steam Build ID | `25906190` | Zrzut właściwości Steam; wskazanie wersji dystrybucji Steam, nie hash lokalnych plików. |
| „Installed content updated” | `Nov 11, 2026 at 7:23 AM` | Data widoczna na zrzucie Steam; bez dodatkowej interpretacji strefy czasu. |
| Numer na ekranie logowania | `1.1.0.63833` | Podany przez właściciela. |
| Numer po załadowaniu | `1.0.332.63833` | Zrzut przekazany przez właściciela. |

Właściciel zgłosił, że zainstalował grę ze Steam na Windows. Nie mamy dostępu
ani nie oglądaliśmy zawartości tej instalacji. **Nie utożsamiamy Steam Build
ID z dwoma numerami z ekranów**; wspólna końcówka `63833` tych dwóch numerów nie
dowodzi, że oznaczają ten sam komponent lub zestaw plików. Nie sprawdzono
regionu, wybranego języka, aktywnych warstw, autentyczności plików ani
zgodności z którymkolwiek parserem.
Aktualizacja gry może zmienić te dane — przed późniejszymi próbami należy je
ponownie odczytać. Nie używać numeru buildu jako zgody na zapis czy dowodu
zgodności backupu.

## Najprostszy następny krok: oględziny nazw

Nie trzeba wysyłać plików gry ani instalować Pythona. Proponowany zakres to
wyłącznie **obecność i rozmiary kilku nazw**, bez ich otwierania:

1. Zamknij grę i poczekaj, aż Steam zakończy ewentualną aktualizację. W
   Bibliotece Steam kliknij grę prawym przyciskiem → **Właściwości →
   Zainstalowane pliki → Przeglądaj**. Nazwy pozycji mogą się nieco różnić.
   Otworzy się katalog gry.
2. W katalogu gry sprawdź, czy są dwa następujące podkatalogi (drugi może nie
   istnieć); przed sprawdzeniem drugiego wróć do głównego katalogu gry:
   - `Package\HD\oversea\locale`
   - `LocalData\Patch\HD\oversea\locale`
3. W każdym istniejącym katalogu w widoku **Szczegóły** znajdź nazwy zaczynające
   się od `translate_words_map_en`. Jeśli są, podaj nazwy i rozmiary lub
   prześlij zrzuty listy. Najbardziej interesują nas `translate_words_map_en`,
   `translate_words_map_en_diff`, `translate_words_map_en__small`,
   `translate_words_map_en__small_diff` oraz ewentualny wariant `_mobile`.
   Przy okazji można zaznaczyć, czy są odpowiedniki `translate_words_map_zh_cn`;
   nie są konieczne na pierwszy raport. Jeśli katalogu lub plików nie ma,
   napisz po prostu „brak” — **nie twórz ich**. Jeśli nie da się ich sprawdzić,
   napisz „niedostępne”.
4. Przed wysłaniem zrzutu zasłoń pasek ścieżki, nazwę użytkownika, inne prywatne
   informacje i wszystko, czego nie chcesz ujawniać. Nie przesyłaj samych plików,
   ich treści, zapisów gry, danych konta ani haseł. Podaj również, jaki język
   interfejsu/napisów jest ustawiony w grze.

To tropy z [przypiętego kodu instalatora społeczności](https://github.com/arimacold/wwm-spolszczenie/blob/d0a32ee8938526b6fdf6d829bf00baa0fb86b4c3/Instalator/installer.py)
i innych [publicznych opisów](FEASIBILITY.md), a nie pewna mapa tej wersji. Nie
używamy cudzego tłumaczenia. Brak kandydata w jednym miejscu nie dowodzi, że
tekstów nie ma gdzie indziej. Oględziny nazw nie są ekstrakcją, audytem całej
gry ani testem patchera.

## Opcjonalny raport metadanych dla osób z Pythonem

Jeżeli właściciel ma Python 3.11/3.12 i wybierze tę metodę, z katalogu repo:

```powershell
python -B tools/inspect_steam_layout.py --root "PEŁNA_ŚCIEŻKA_DO_KATALOGU_GRY"
```

Narzędzie sprawdza tylko dwa wskazane wyżej katalogi i dziewięć stałych nazw w
każdym z nich. Zwraca nazwy, stan i rozmiar bajtowy; nie otwiera zawartości
plików gry, nie liczy hashy, nie podejmuje zapisów do drzewa gry i nie wykonuje
bezpośrednich wywołań sieciowych. System plików może jednak działać przez sieć.
Opcja `-B` wyłącza tworzenie plików bytecode Pythona (`.pyc`); raport trafia na ekran,
chyba że samodzielnie przekierujesz wyjście do pliku. **Ścieżka może zostać w
historii powłoki lub na liście procesów**, chociaż nie trafia do JSON-a.
Przed wysłaniem zawsze obejrzyj raport. Gdy brak podkatalogu, brak dostępu lub
wykryto link/reparse, wynik jest `incomplete` (kod wyjścia 1); niedostępny lub
linkowany katalog główny i błędne argumenty dają błąd (kod 2). Brak katalogu
nie jest w raporcie przedstawiany jako brak wszystkich plików. Narzędzie nie
tworzy ani nie poprawia brakujących plików. Sprawdza linki i tożsamość
katalogów tylko na zasadzie best effort: nie zapobiega wyścigom ani nie tworzy
atomowej migawki. Przetestowano je wyłącznie na sztucznych katalogach, nie na
tej instalacji. To tylko opcja dla osób posiadających Pythona, nie docelowy ZIP
audytora ani patchera.
