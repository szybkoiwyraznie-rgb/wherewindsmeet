# Plan prac i bramki jakości

To kierunek pracy, nie obietnica zgodności ani wybór technologii. Każdy etap
ma wejście, wynik, dowody oraz warunki zakończenia. Aktualny stan jest w
[STATUS.md](STATUS.md).

## 0. Repozytorium i workflow — obecny etap

Instrukcje dla agentów, środowisko, Git/PR, ochrona danych, dziennik i CI
uruchamiane bez gry. Nie udajemy, że powstał już patch lub ekstraktor.

## 1. Rozpoznanie i wykonalność

- Celem jest Windows; [Steam rekomendowano na start](WINDOWS_OPTIONS.md). Po
  instalacji ustalić wydanie, region, wersję, język źródłowy i zakres projektu.
  Sprawdzić wcześniejsze narzędzia i ich licencje, warunki gry oraz ryzyko
  związane z trybami sieciowymi i zabezpieczeniami.
- Zacząć od metadanych: nazw, rozmiarów i identyfikatorów wersji; ustalić,
  co raport może bezpiecznie ujawniać. Nie zakładać silnika ani formatów.
- Właściciel zgłosił, że według jego ustalenia zmiany wyłącznie tekstowe są
  dozwolone, i wybrał taki kierunek. Nie potwierdziliśmy niezależnie wyjątku w
  warunkach wydawcy; kontakt w celu wyjaśnienia pozostaje opcjonalny.
- Dla przyszłych prób ustalić minimalny materiał, prawa, kryterium powodzenia,
  konkretny plan, kopię i przywracanie. Do tego czasu pracować na syntetycznych
  danych. Nie obchodzić zabezpieczeń/anti-cheat.
- **Wynik:** potwierdzone fakty oddzielone od ustaleń właściciela i niewiadomych,
  ocena ryzyka oraz plan odpowiadający uzgodnionemu kierunkowi.

## 2. Lokalizacja i ekstrakcja tekstów

- Ustalić faktyczne kategorie tekstów, języki, kodowanie, kontekst i sposób
  identyfikacji rekordów. Spisać źródłowe wersje i hashe; zachować kolejność,
  powtórzenia, znaczniki i powiązania, których znaczenie wynika z danych.
- Budować narzędzia i testy na syntetycznych próbkach; rzeczywiste pliki gry
  pozostają lokalne. Zakres i kompletność podawać na podstawie policzonych
  danych, a nie liczby potencjalnych kontenerów.
- **Wynik:** odtwarzalny ekstrakt z manifestem i raportem pokrycia, po
  uzgodnieniu miejsca przechowywania danych tekstowych.

## 3. Pakiet dla tłumacza i bezpieczny import

- Jest [prototyp znormalizowanego pakietu JSON](TRANSLATION_BUNDLE.md) na
  fikcyjnych danych: tworzenie szablonu i walidacja zwrotki, bez zapisu plików.
  Nie jest ekstraktorem, importerem ani formatem potwierdzonym dla gry.
- Przygotować docelowo czytelny pakiet z kontekstem, uzgodnionym źródłem/referencjami,
  identyfikatorami, słownikiem, regułami tokenów i ograniczeniami tam, gdzie są
  zmierzone. Format uzgodnić z tłumaczem, nie narzucać formatu SRW Y.
- Właściciel chce niezależnej pracy z dobrym modelem, nie gotowej cudzej
  polonizacji. Model wybrać po porównaniu jakości, kosztów i warunków
  przetwarzania; przed wysłaniem tekstów gry ustalić prawa i prywatność.
- Związać pakiet z dokładną wersją źródła i manifestem. Importować partiami;
  odróżniać brak tłumaczenia od rekordu usuniętego, sprawdzać tożsamość,
  strukturę i znaczniki. Konflikty kierować do przeglądu.
- **Wynik:** walidowany import z raportem, testem niezmienionego round-trip i
  zapisem atomowym; błędna partia nie może częściowo nadpisać danych.

## 4. Integracja z grą i instalacja

- Preferowany jest natywny tekst w grze; nakładka OCR jest rezerwą, nie gotową
  alternatywą. Zakres to zmiana wartości tekstowych **przy wyłączonej grze**,
  bez modyfikowania kodu wykonywalnego, pamięci, zabezpieczeń ani podmieniania
  plików w trakcie uruchamiania lub rozgrywki. Tekst może być przechowywany w
  kontenerze binarnym; fizyczny sposób zapisu trzeba dopiero rozpoznać i uzgodnić.
- Przyszły proces musi sprawdzać wersję, utrzymywać weryfikowane kopie i mieć
  przetestowane przywracanie. Nie obchodzić kontroli integralności ani
  automatycznego przywracania plików; jeśli klient cofa zmianę, jest to
  niepowodzenie testu, nie powód do obejścia.
- Testować najpierw na syntetycznych danych, a na rzeczywistej instalacji
  dopiero po uzgodnieniu konkretnego planu, kopii i przywracania. Nie
  rozprowadzać oryginalnych ani zmodyfikowanych plików gry.
- **Wynik:** powtarzalny proces budowy i cofnięcia, bezpieczna odmowa przy
  niezgodnym buildzie oraz osobno udokumentowany wynik rzeczywistego testu.

## 5. QA polskiej wersji

- Osobno sprawdzić komplet polskich znaków (małe i wielkie), interfejs,
  dialogi, zawijanie, wymiary pól, znaczniki, zapisy i regresje. Rzeczywiste
  limity mogą zależeć od powierzchni i szerokości glifów, nie tylko od liczby
  znaków.
- Rozróżniać test jednostkowy, test na kopii, test na Windows i wynik w grze;
  pokrycie i nieznane elementy podawać jawnie.

## 6. Czytanka

- Korzystać z zaakceptowanej wersji tłumaczenia i potwierdzonej struktury
  źródła. Kolejność scen, warianty i kontekst muszą wynikać z dowodów; elementy
  nieustalone oznaczać zamiast wymyślać.
- Zapewnić powtarzalne generowanie, niezależną kontrolę pokrycia i raport,
  z którego wiadomo, jaki build i zwrotka były wejściem.

## 7. Aktualizacje gry i wydania

- Porównywać wersje po zaufanych identyfikatorach i fingerprintach: nowe,
  zmienione, usunięte i niepewne rekordy rozdzielać. Zachować poprzednie
  zwrotki; przy zmianie źródła nie przypisywać tłumaczeń na ślepo.
- Niezgodną wersję gry wykrywać przed zapisem. Przygotować plan aktualizacji
  i cofnięcia, regresje oraz czytelną informację o obsługiwanych buildach.
- W przyszłości PR ma testować i budować bez publikacji; publikacja jedynie po
  osobnym, uzgodnionym przeglądzie. Obecnie workflow wydań nie istnieje.
