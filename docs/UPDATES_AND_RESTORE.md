# Aktualizacje tłumaczenia i bezpieczne cofanie — projekt

**Stan: analiza i prototypy wyłącznie na danych wymyślonych.** Nie mamy jeszcze
ekstraktora WWM, pamięci tłumaczeń, importera do gry ani instalatora lub
odinstalatora. Nie badaliśmy instalacji właściciela, nie znamy stabilności ID,
aktywnych warstw ani kompletnego zakresu tekstów. Poniższy proces docelowy
wymaga ich potwierdzenia; zgodność z grą i bezpieczeństwo konta nie są dowiedzione.
Kierunek wybrany przez właściciela to zmiana wyłącznie tekstu przy wyłączonej
grze, bez zmian kodu/pamięci i obchodzenia kontroli integralności. Docelowy
podział na [audytor i patcher Windows](TWO_APPLICATIONS.md) oraz zasada jednej
aktualnej kopii na plik są opisane osobno.

## Czego uczą inne projekty

Analiza statyczna, bez pobierania cudzych tłumaczeń, plików gry ani
uruchamiania wymienionego kodu:

| Źródło | Wniosek dla naszego projektu |
|---|---|
| Indonezyjski projekt: [procedura aktualizacji](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/.agents/skills/wwm-game-update/SKILL.md), [porównanie](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/.agents/skills/wwm-game-update/scripts/compare_update.py), [dopisywanie tekstów](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/tools/rebuild_unique_strings.py) | Najpierw porównanie plików i liczników, potem dopisanie nowych prac bez renumerowania wcześniejszych. Jednak identyczny tekst nie zawsze oznacza identyczny kontekst: nie kopiujemy deduplikacji po samym tekście jako reguły automatycznego przekładu. Badany skrypt porównujący zapisuje rekordy w słowniku po hashu, więc duplikaty mogą się nadpisać; niektóre dodatkowe brakujące wejścia w skrypcie dopisującym są pomijane. Nasz przyszły proces ma wykrywać obie sytuacje, nie ukrywać ich. |
| [Indonezyjski `patch_all.py`](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/tools/patch_all.py) | Autorzy opisują różne teksty dla tego samego hasha w różnych wariantach. Sam hash, tekst ani pozycja w kontenerze nie są wystarczającym, potwierdzonym ID między buildami. |
| [Wietnamski ekstraktor](https://github.com/hps-nguyen/wwm_localization/blob/32efefe9dcb25baf56fe81a83c7186a881ad3e02/tools/extract_language_files.py) i [repacker](https://github.com/hps-nguyen/wwm_localization/blob/32efefe9dcb25baf56fe81a83c7186a881ad3e02/tools/repack_translations.py) | Autorzy analizują bazę i `_diff`. To wskazówka do badania warstw, nie dowód, że wszystkie wydania działają tak samo. W badanym kodzie część błędów ekstrakcji/dekodowania jest pomijana, a przy repacku kopiowany jest oficjalny `_diff` w deklarowanym celu przejścia weryfikacji. Nie powielamy tych zachowań ani nie obchodzimy integralności. |
| [Instalator Arimy](https://github.com/arimacold/wwm-spolszczenie/blob/d0a32ee8938526b6fdf6d829bf00baa0fb86b4c3/Instalator/installer.py) | Badana ścieżka przywracania usuwa obecny plik i kopiuje `.backup` bez sprawdzenia zgodności jego hasha i buildu; usuwa też pliki `_diff`. Po aktualizacji taki schemat może zastąpić albo usunąć nowsze dane. Nasz projekt ma odmawiać takiego działania, nie korzysta z tłumaczenia Arimy. |
| [SRW — manifest i import](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/docs/IMPORTER_Y.md) | Wzorzec prywatnego manifestu, hashowania pełnych wejść, ponownej walidacji i odmowy zapisu. Atomowy zapis pojedynczego wyniku nie jest transakcją obejmującą wiele plików. Format i kod SRW nie są gotowym rozwiązaniem WWM. |

Skala również ma znaczenie: [stan indonezyjskiego projektu](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/Obsidian-Vault/progress/Current-Status.md)
z 2026-10-18 deklaruje dla swojej próbki około **1,12 mln wystąpień** w mapie
bazowej i około **11 tys.** w `_diff`. To deklaracje autorów dla ich wersji, nie
nasz pomiar, lista wszystkich tekstów WWM ani dowód zgodności z klientem właściciela.
GitHub wykrywa GPL-3.0 w projekcie indonezyjskim, MIT w wietnamskim i nie
wykrywa licencji repozytorium Arimy. To nie rozstrzyga praw do tekstów gry;
kodu ani tłumaczeń tych projektów nie przenosimy do naszego repozytorium.

## Proponowany obieg po każdej aktualizacji

1. **Stan wejściowy.** Po uzgodnieniu zakresu i praw zebrać lokalnie czyste,
   zaufane oryginały dla dokładnej platformy, regionu, buildu, języka i wszystkich
   aktywnych wariantów/warstw. Oddzielić je od plików potencjalnie już
   spolszczonych. Nie traktować starego backupu automatycznie jako oryginału
   nowej wersji. Gra nie może działać podczas przyszłych operacji na plikach.
2. **Manifest i pełna ekstrakcja.** Przyszły parser ma zapisać prywatny manifest:
   zakres, build, język, wariant/warstwę, wersję parsera, oczekiwane wejścia,
   ich stan i SHA-256, liczniki oraz błędy. Sprawdzić stabilność wejść na czas
   odczytu. Brak oczekiwanej warstwy, nieznany wariant, błąd dekodowania lub
   niepełna ekstrakcja wstrzymuje porównanie, zamiast udawać zero zmian.
   Rzeczywista kolejność nakładania warstw i znaczenie ewentualnych tombstone
   muszą zostać osobno rozpoznane i przetestowane.
3. **Porównanie wersji.** Porównywać wystąpienia z uwzględnieniem zakresu,
   wariantu, kontekstu, tekstu i znaczników. Stałość i unikalność ID trzeba
   udowodnić na kolejnych wydaniach; zduplikowane klucze zachować i zgłosić.
   Nowe, zmienione, nieobecne oraz niejednoznaczne wystąpienia są osobnymi
   kategoriami. Sama nieobecność w ekstrakcie nie dowodzi usunięcia: tombstone
   lub inne potwierdzenie ma sens dopiero po zweryfikowaniu semantyki formatu.
   Gdy dokładne bajty wejścia, zakres, parser i jego ustawienia są identyczne,
   można rozważyć użycie wcześniej sprawdzonego indeksu zamiast ponownej
   ekstrakcji; cache też wymaga kontroli pochodzenia i integralności.
4. **Pamięć tłumaczeń i kolejka.** Przechowywać oddzielnie historię wersji,
   źródło i kontekst, dosłowne znaczniki, własny przekład, status recenzji i
   decyzję człowieka. Jeżeli ID/zakres są potwierdzone, a tekst, kontekst i
   tokeny są dokładnie takie same, przyszły system może proponować ponowne
   użycie wcześniej **zatwierdzonego** przekładu zgodnie z jawną polityką.
   Zmiany, konflikt ID, podobieństwo tekstu i niepewne konteksty wymagają
   przeglądu; nie używać samej zgodności tekstu lub hasha jako dowodu. Nie
   przypisywać starego tłumaczenia do zmienionego rekordu automatycznie.
5. **Pakiet i zwrotka.** Nowe, zmienione i niewiadome przypadki dzielić na
   partie ze źródłem, kontekstem i odwołaniem do pełnego manifestu. Po zwrotce
   zweryfikować jej pochodzenie względem niezależnie zachowanego źródła, ID,
   tokeny, strukturę oraz zatwierdzenie i konflikty. Pominięcie rekordu w
   częściowej zwrotce to stan nieznany, a nie dowód, że nie ma go w bazie.
   Sam niepusty przekład nie oznacza zatwierdzenia. Tłumaczenie modelowe i
   udostępnianie tekstów gry wymagają osobnego uzgodnienia praw i prywatności.
6. **Budowa, QA i wydanie.** Dopiero przyszły, przetestowany na kopiach parser
   i repacker mogą tworzyć rezultat z **oryginałów nowego buildu** i
   zwalidowanych, zaakceptowanych przekładów. Weryfikować ponowną ekstrakcję,
   zmienione wartości, nienaruszone pozostałe dane, tokeny, glify, układ i
   pokrycie. Testy na fikcyjnych danych i kopii offline nie są testem w grze;
   rzeczywiste próby wymagają wcześniej uzgodnionego planu i zgody. Nie
   dystrybuować oryginalnych ani zmodyfikowanych plików gry.

## Prototyp audytu: przykładowe polecenia

Python 3.11/3.12, biblioteka standardowa, z katalogu repozytorium. Dane są w
całości fikcyjne. Wszystkie tryby czytają `.json` i wypisują wynik na stdout;
**skrypt nie zapisuje plików ani nie dotyka instalacji**.

```sh
python tools/audit_translation_update.py --old-source tests/fixtures/synthetic_update_old.json --new-source tests/fixtures/synthetic_update_new.json --old-bundle tests/fixtures/synthetic_update_old_return.json --assume-comparable
python tools/audit_translation_update.py --old-source tests/fixtures/synthetic_update_old.json --new-source tests/fixtures/synthetic_update_new.json --old-bundle tests/fixtures/synthetic_update_old_return.json --assume-comparable --mode todo
python tools/audit_translation_update.py --old-source tests/fixtures/synthetic_update_old.json --new-source tests/fixtures/synthetic_update_new.json --old-bundle tests/fixtures/synthetic_update_old_return.json --assume-comparable --mode review
```

`--assume-comparable` to **niesprawdzone zapewnienie wywołującego**, że wejścia
reprezentują ten sam pełny zakres i porównywalne, stabilne ID. Bez flagi skrypt
odmawia działania; nawet z flagą nie potwierdza buildu, kompletności ani ID.
Etykieta `source_id` nie jest zweryfikowanym Build ID. Przesłanka może okazać
się fałszywa, np. przy zmianie ID; nie uruchamiaj prototypu na tekstach gry.

- **`report`** (domyślny) nie wypisuje tekstów, ID ani ścieżek; zawiera
  liczniki i skróty źródeł/zwrotki. Skróty mogą identyfikować dane. Liczniki
  `changed_source`, `changed_context` i `changed_protected_tokens` mogą się
  nakładać. `id_only_in_old` to wyłącznie brak ID w drugim wejściu.
- **`todo`** wypisuje częściowy szablon [formatu zwrotki v1](TRANSLATION_BUNDLE.md),
  powiązany skrótem z **całym nowym źródłem**. Zawiera nowe ID, zmienione
  rekordy oraz niezmienione z jawnym `null` lub nieznanym stanem; wszystkie
  jego tłumaczenia są początkowo `null`. Niezmienione rekordy z niepustym
  poprzednim przekładem trafiają do przeglądu, a nie do `todo`.
- **`review`** wypisuje teksty, konteksty, ID, poprzednie przekłady, przyczyny
  zadań i listę ID obecnych tylko w starym źródle. Niezmieniony przekład jest
  **niezweryfikowanym kandydatem**, nie automatycznym zatwierdzeniem. Zmieniony
  rekord zawiera wcześniejszy przekład tylko jako odniesienie. Jednoznaczna
  równość treści/kontekstu/tokenów przy różnych ID daje wskazówkę do ręcznej
  kontroli możliwej zmiany ID, nie dowód tożsamości. Duplikaty lub inne
  niejednoznaczności nie są automatycznie kojarzone.

`todo` i `review` **ujawniają treści**; nie umieszczaj ich w publicznych logach
ani Git. Wskazana stara zwrotka jest najpierw walidowana względem całego starego
źródła. Bez niej wszystkie niezmienione rekordy mają nieznany wcześniejszy
stan. Prototyp nie ma statusu zatwierdzenia ani importu/łączenia tłumaczeń:
żaden wcześniejszy przekład nie jest automatycznie przenoszony do zwrotki nowego
źródła. Jeżeli ręcznie zapisujesz stdout, uważaj na kodowanie PowerShell 5.1
oraz nadpisanie wejść; szczegóły w [opisie zwrotki](TRANSLATION_BUNDLE.md).

W przykładzie: 7 → 7 rekordów; 3 bez zmian, 2 zmienione (tekst i kontekst),
2 ID tylko w nowym i 2 tylko w starym. Jeden z tych ostatnich jest możliwym
przeniesieniem ID, ale nadal wymaga sprawdzenia. Spośród niezmienionych jest
1 kandydat, 1 jawny `null` i 1 pominięty w zwrotce. `todo` ma 6 zadań;
`review` zawiera 4 odniesienia. To wyłącznie wynik dla fikcyjnych danych.

## Skala: prototyp a docelowy indeks

Obecny format v1 ma limit **10 000 rekordów i 8 MiB na każde źródło**, 32 MiB
na zwrotkę oraz limit pracy tokenów z [opisu formatu](TRANSLATION_BUNDLE.md).
Wynik wybranego trybu również ograniczono do 32 MiB. Dane są wczytywane do
pamięci; narzędzie nie nadaje się do pełnego korpusu wspomnianego wyżej ani do
realnego WWM. Nie należy bez planu dzielić obu źródeł i sumować `old-only`:
przesunięcia między częściami i brakujące partie dałyby fałszywe wyniki.

Docelowo rozważyć lokalną bazę SQLite lub inny indeks dyskowy: osobne wiersze
**każdego wystąpienia** z wersją/zakresem/warstwą, historią źródeł oraz
oddzielną pamięcią zatwierdzonych tłumaczeń; indeksy po potwierdzonym złożonym
ID i odciskach pól, zachowanie kolizji i duplikatów. Strumieniowa ekstrakcja i
indeksowane porównanie mają ograniczać RAM i pozwalać wysyłać tylko nowe partie;
zawsze sprawdzać pełne pola, nie ufać samemu odciskowi. Potrzebne są m.in.
transakcje bazy, wersjonowanie schematu, kontrola miejsca, przerwań, kompletności
partii, wydajności i testy na skali docelowej. **To projekt, nie implementacja.**

## Instalacja, aktualizacja i przywracanie — zasady przyszłego rozwiązania

Przed przyszłą instalacją potrzebny jest osobny manifest dla konkretnego buildu
i każdego objętego pliku: stan pierwotny/obecność, hash czystego oryginału,
zweryfikowanego backupu i docelowego patcha, ścieżka/rola, wersja narzędzia oraz
identyfikacja instalacji. Kopia powinna znajdować się poza katalogiem gry,
zostać sprawdzona po zapisaniu i nie nadpisywać bez ostrzeżenia wcześniejszej.
Hash potwierdza zgodność z zaufanym wpisem, **nie pochodzenie**; podmieniony
manifest i pliki wymagają osobnej kontroli zaufania.

| Stan stwierdzony przez przyszły preflight | Konserwatywna reakcja |
|---|---|
| Ten sam potwierdzony build; plik odpowiada zapisanemu oryginałowi | Nic nie przywracać dla tego pliku; zachować go. |
| Ten sam potwierdzony build; plik odpowiada zainstalowanemu patchowi, kopia jest zweryfikowanym oryginałem tego buildu | Kandydat do przywrócenia dopiero po pełnym preflight wszystkich plików i innych kontroli; nie dowód gotowości do zapisu. |
| Build się zmienił, zakres jest inny, plik/backup jest nieznany, brakujący lub zmieniony | **Nie kopiować starego backupu i nie usuwać pliku.** Zatrzymać całą operację, zachować dowody i poprosić o diagnozę; żadnego automatycznego nadpisywania nowej wersji. |

Po aktualizacji może wystąpić mieszanina starych plików patcha i nowszych plików
gry. Nie rozstrzygać tego po nazwie, dacie ani samym fakcie istnienia backupu.
Potrzebny będzie osobny, świadomy plan odzyskania zgodnego bieżącego buildu i
weryfikacji jego warstw. Ewentualny wyjątek od blokady po zmianie buildu
wymaga odrębnego, zaufanego potwierdzenia i zaprojektowania; obecnie go nie ma.

Przed dowolnym przyszłym zapisem: pełny preflight **wszystkich** plików,
uprawnień, wolnego miejsca, backupów, linków/reparse i spodziewanych ścieżek;
ponowna kontrola hashy tuż przed zmianą; tymczasowe wyniki na właściwym
systemie plików; trwały dziennik stanów oraz testy odzyskiwania po przerwaniu.
`os.replace` może być atomowe dla **jednego** pliku na odpowiednim filesystemie,
nie dla zestawu plików; nie dowodzi trwałości zapisu. Plan odzyskiwania musi
ponownie sprawdzać stan i zatrzymywać się przy konflikcie. Proces aktualizacji
launchera nadal może wejść w wyścig z preflightem — nie jest to rozwiązane.
Nie manipulować plikami podczas działania gry ani uruchamiania klienta.

Steam oferuje weryfikację w **Właściwości → Zainstalowane pliki → Sprawdź
spójność plików** (instrukcja Bethesda dla Steam: [1](https://help.bethesda.net/app/answers/detail/a_id/25561/~/how-do-i-verify-the-integrity-of-my-game-files-in-steam)).
Przed użyciem świadomie zabezpieczyć własne dane i konfigurację: weryfikacja
może przywrócić pliki zarządzane przez platformę i cofnąć modyfikacje. Nie ma
jednak gwarancji usunięcia dodatkowych plików lub naprawienia warstw zarządzanych
przez osobny launcher; nie jest to sprawdzony, kompletny rollback WWM.

## Model decyzji przywracania — tylko fikcyjne hashe

```sh
python tools/model_restore_preflight.py --recorded tests/fixtures/synthetic_restore_recorded.json --observed tests/fixtures/synthetic_restore_observed.json
python tools/model_restore_preflight.py --recorded tests/fixtures/synthetic_restore_recorded.json --observed tests/fixtures/synthetic_restore_observed.json --details
```

Przykład zwraca `blocked_build_mismatch`: obserwowany build ma inną etykietę,
jeden plik wygląda na stary patch, drugi ma nieznany hash. `--details` ujawnia
podane logiczne ID. Model porównuje **wyłącznie dostarczone napisy i hashe**:
nie czyta plików gry, nie uwierzytelnia manifestu, nie wykrywa procesów i nie
robi backupu, instalacji ani odinstalowania. W syntetycznej obserwacji `null`
oznacza hash niedostępny, nie potwierdzoną nieobecność; model nie rozstrzyga
usuwania plików utworzonych przez patch. Wymaga poprawnego backupu dla każdego
rekordu, także gdy już podano hash oryginału. Nawet `needs_further_preflight`
nie pozwala na zapis (`write_authorized: false` zawsze); brak lub nadmiar ID
jest błędem. Kod wyjścia `0` oznacza tylko poprawny przebieg modelu, również
dla decyzji blokującej. To test zasad, nie narzędzie ratowania instalacji.
