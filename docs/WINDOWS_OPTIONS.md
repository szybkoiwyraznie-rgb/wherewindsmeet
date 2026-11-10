# Windows: wydanie referencyjne i warianty techniczne

Stan: **2026-11-10**. Właściciel wskazał **Windows**, jeszcze nie zainstalował
*Where Winds Meet*, chce niezależnego tłumaczenia wspomaganego dobrym modelem i
preferuje tekst natywnie w grze. Nakładka ma być wariantem rezerwowym. Nie
wykorzystujemy gotowego polskiego tłumaczenia Arimy ani innych niezweryfikowanych
gotowych zwrotek; wskazane projekty badamy jako źródła informacji technicznych.

## Rekomendacja: Steam jako pierwsza wersja referencyjna

| Wariant | Co przemawia za / przeciw | Stan dowodów |
|---|---|---|
| **Windows + Steam** | [Karta Steam](https://store.steampowered.com/app/3564740/Where_Winds_Meet/) ma stały app ID `3564740`; Steam udostępnia informację o buildzie i weryfikację instalacji. Wariant pojawia się w przejrzanych opisach społeczności, więc łatwiej porównywać rezultaty. | **Rekomendacja na start, nie dowód zgodności.** Społeczność opisuje przywracanie `_diff`, także przy starcie; aktualne zachowanie nie było przez nas sprawdzane. |
| Oficjalny launcher PC | Autor polskiego instalatora uwzględnia go w heurystykach, a społeczność opisuje odrębne ścieżki. Może być późniejszym celem. | Nie wiemy, czy obecny klient łatwiej obsłuży własną lokalizację lub inaczej weryfikuje `_diff`. Nie przetestowano. |
| Epic Games | Kod polskiego instalatora zawiera typowe ścieżki i łączy ten wariant z launcherem. | Sama heurystyka nie dowodzi poprawnego wykrywania, zgodności plików ani działania w aktualnej grze. Nie przetestowano. |

Steam wybieramy dla **powtarzalnego punktu odniesienia**, nie dlatego, że jest
bezpieczniejszy dla konta albo na pewno łatwiejszy do modyfikacji. Nie ma
podstaw, by twierdzić, że alternatywny launcher eliminuje przywracanie plików.
Aktualizacje gry i weryfikacja mogą zmieniać pliki; nie planujemy omijać
kontroli integralności. Dostępne są różne katalogi bibliotek Steam — przykład
ścieżki instalatora nie wystarcza do niezawodnego wykrywania.

[Oficjalny poradnik łączenia kont](https://www.wherewindsmeetgame.com/news/official/GlobalLaunch/CrossPlatform.html)
opisuje cross-progression między Steam, Epic i launcherem. Przy przenoszeniu
istniejącej postaci trzeba połączyć konta **przed utworzeniem nowej postaci na
platformie docelowej**; według poradnika ręczne rozłączenie nie jest dostępne.
Nie zakładamy, że ustawienia lub pliki lokalne synchronizują się razem z postacią.

### Co może zrobić właściciel

Można zainstalować **zwykłą, niemodyfikowaną grę ze Steam** i zostawić zapas
miejsca na aktualizacje. Po instalacji wystarczy podać numer wersji gry i, jeśli
jest widoczny, **Steam Build ID**: Biblioteka → prawy przycisk na grze →
Właściwości → Aktualizacje (etykiety mogą się różnić między wersjami klienta).
Build ID Steam nie musi być numerem wersji gry ani dowodem stanu wszystkich
plików. Nie potrzebujemy danych konta, pełnej ścieżki, całej gry ani zrzutów z
osobistymi danymi. Na tym etapie nie prosimy o uruchamianie narzędzi na grze.

## Co wynika z polskiego instalatora Arimy

Przejrzano wyłącznie README i [kod `installer.py`](https://github.com/arimacold/wwm-spolszczenie/blob/d0a32ee8938526b6fdf6d829bf00baa0fb86b4c3/Instalator/installer.py),
commit `d0a32ee8938526b6fdf6d829bf00baa0fb86b4c3` z 2026-10-26. Nie pobrano
ani nie uruchomiono binarnego instalatora, plików gry ani jego tłumaczeń.

- Kod rozróżnia bazę i warstwy aktualizacji, warianty językowe oraz niektóre
  nazwy `__small` i `_diff`. To konkretne tropy, ale nie dowód tego, jakie
  pliki są aktywne w naszym przyszłym buildzie.
- Funkcja nazywana przez autora „injectorem” w przejrzanym kodzie obserwuje i
  podmienia **plik** podczas startu; nie stwierdziliśmy tam wstrzykiwania kodu
  do pamięci gry. Nie przejmujemy tego mechanizmu ani nie zalecamy jego użycia:
  próba utrzymania zmian mimo weryfikacji wymaga wyjaśnienia z wydawcą.
- Kod tworzy kopię plików, lecz pobiera bezpośrednio do celu i działa na wielu
  plikach kolejno. Widoczne są ryzyka niepełnej operacji, starego backupu po
  aktualizacji oraz porównywania rozmiaru zamiast tożsamości pliku. To powód,
  by w naszym przyszłym rozwiązaniu wymagać wersjonowanych kopii, hashy,
  transakcyjnego działania i testowanego przywracania — nie ocena jakości
  cudzej pracy ani twierdzenie o zachowaniu wszystkich wersji instalatora.
- W drzewie głównym nie znaleziono licencji kodu instalatora; GitHub nie
  rozpoznał licencji repozytorium. Nie kopiujemy kodu ani danych. Binaria nie
  były audytowane i nie oceniamy ich bezpieczeństwa.

## Kaption: rezerwa, nie gotowy zamiennik

[README Kaption](https://github.com/wojciechowskiapp/Kaption/blob/8f2475a72cb21ab6c95a2edede75834b98ec7e57/README.md)
opisuje przechwycenie wybranego obszaru ekranu, lokalny OCR, dopasowanie do
przygotowanej bazy dialogów i wyświetlenie napisu w osobnym oknie. Nie jest to
w opisanej głównej ścieżce po prostu ogólny model tłumaczący każdą nową linijkę
na żywo. Baza dialogów i kontekst są potrzebne; błędy OCR, brak wpisów i
niejednoznaczne dopasowanie ograniczają pokrycie.

Wskazany commit `8f2475a72cb21ab6c95a2edede75834b98ec7e57` obsługuje cztery
inne gry, a WWM widnieje jedynie w [kandydatach](https://github.com/wojciechowskiapp/Kaption/blob/8f2475a72cb21ab6c95a2edede75834b98ec7e57/games/candidates.json).
Nie ma zatem potwierdzonej gotowej obsługi WWM w tym wydaniu. Klient jest
udostępniany na [AGPL-3.0 lub licencji komercyjnej](https://github.com/wojciechowskiapp/Kaption/blob/8f2475a72cb21ab6c95a2edede75834b98ec7e57/LICENSE),
a backend i oficjalna produkcja pakietów nie są opublikowane. Korzystanie z
kodu wymagałoby osobnej analizy licencji; nie kopiujemy go.

OCR/dopasowanie według autora odbywa się lokalnie, ale to nie znaczy, że cały
produkt działa bez sieci: [polityka prywatności](https://github.com/wojciechowskiapp/Kaption/blob/8f2475a72cb21ab6c95a2edede75834b98ec7e57/docs/PRIVACY.md)
opisuje m.in. aktywację i pobieranie pakietów. Raporty błędów są według niej
opcjonalne i mogą zawierać fragment tekstu gry. Samej zgodności nakładki z
regulaminem gry ani bezpieczeństwa konta nie sprawdziliśmy.

## Przyjęty kierunek

1. **Główna droga:** niezależny obieg tekstów → własne tłumaczenie → walidacja →
   dozwolona integracja z grą, jeśli zostanie potwierdzona. Kontrola wersji,
   kontekstu, placeholderów, polskich znaków, kopii i odtwarzania to wymagania,
   nie działające jeszcze funkcje.
2. **Model:** wybrać po poznaniu źródła, kontekstu, kosztu i zasad przesyłania
   danych. Porównać wyniki na małej, legalnie użytej próbce oraz ustalić
   słownik nazw i przegląd jakości; nie wysyłać tekstów gry do dostawców bez
   ustalenia praw i sposobu przetwarzania. Nie zakładamy dostępności lub
   automatycznego powiązania angielskiej i chińskiej wersji.
3. **Plan B:** osobny wariant OCR + nakładka, gdy nie da się uzgodnić natywnej
   integracji. Wymaga profilu WWM, danych tłumaczenia, oceny prywatności i zasad;
   też nie daje gwarancji bezpieczeństwa konta ani pełnego pokrycia.
4. W obu wariantach dynamicznie generowany tekst NPC może nie występować w
   statycznym korpusie. Żaden wariant nie zapewnia dziś kompletności czytanki.

Ograniczenia oficjalnych warunków oraz bramka przed testami na kliencie:
[FEASIBILITY.md](FEASIBILITY.md). Gotowy do dostosowania, **niewysłany** szkic
pytania do wydawcy: [PUBLISHER_PERMISSION.md](PUBLISHER_PERMISSION.md).
