# Where Winds Meet — rozpoznanie i wykonalność

Stan: **2026-11-10**. To przegląd publicznych źródeł, bez dostępu do instalacji
właściciela. Rozróżniamy deklaracje wydawcy, wyniki innych projektów oraz
własny test na próbce syntetycznej. Właściciel zgłosił instalację Steam na
Windows i podał [oznaczenia builda i wersji](STEAM_REFERENCE.md). Nie mamy
wglądu w tę instalację i nie przeprowadzono testu na plikach gry.

## Fakty z oficjalnych źródeł

- [Steam — karta gry](https://store.steampowered.com/app/3564740/Where_Winds_Meet/)
  (app ID `3564740`) podaje Windows 10/11 dla wersji PC, wymaga połączenia
  szerokopasmowego i wymienia tryby solo oraz sieciowe. Na dzień przeglądu w
  wykazie języków interfejsu/napisów nie ma polskiego. To **nie** potwierdza
  aktywnych warstw tekstów ani autentyczności plików zgłoszonej instalacji.
- Ta sama karta opisuje także generowany w czasie rzeczywistym tekst i głos
  niektórych NPC. Nie wolno więc zakładać, że jednorazowy ekstrakt statycznych
  tekstów obejmie wszystkie możliwe wypowiedzi ani że sam zapewni czytankę.
- [Warunki na oficjalnej stronie gry](https://www.wherewindsmeetgame.com/termsofuse.html)
  oraz [EULA powiązana ze stroną Steam](https://store.steampowered.com/eula/3564740_eula_0)
  (ostatnia aktualizacja podana w obu tekstach: 2024-12-15) w §3.2(b)(5)
  ograniczają m.in. modyfikację i tłumaczenie Software/Services, o ile warunki
  na to nie pozwalają; §4.5(a) zakazuje m.in. nieautoryzowanych narzędzi i
  modyfikacji. Nie wyjaśniliśmy niezależnie ich zastosowania do planowanego
  spolszczenia ani zakresu ewentualnego wyjątku dla zmian tekstu. Wyjaśnienie
  u wydawcy lub osoby doradzającej prawnie pozostaje opcją; nie przesądzamy
  skuteczności tych postanowień w konkretnej jurysdykcji.
- W [oficjalnym komunikacie o sankcjach](https://www.wherewindsmeetgame.com/news/official/Banreport727.html)
  wydawca opisuje reakcje na nieautoryzowane narzędzia i nieprawidłowe
  zachowania, włącznie z czasowymi lub stałymi blokadami. Komunikat **nie
  rozstrzyga**, czy konkretne spolszczenie zostanie wykryte lub ukarane.
  Nie wolno obiecywać bezpieczeństwa konta ani obchodzić zabezpieczeń.

## Ustalenie właściciela i zakres prac

Właściciel poinformował, że według jego sprawdzenia dozwolone są modyfikacje
ograniczone do czystego tekstu, i wybrał je zamiast ingerencji w pamięć lub
podmiany podczas gry. Nie przedstawił dokumentu zgody wydawcy; nie udało nam
się niezależnie potwierdzić zakresu takiego wyjątku ani bezpieczeństwa konta.
To jego zgłoszone ustalenie, nie nasze potwierdzenie stanowiska wydawcy.

Przyjmujemy kierunek **zmiany wartości tekstowych przy wyłączonej grze**: bez
wstrzykiwania, modyfikacji kodu wykonywalnego lub pamięci, obchodzenia
zabezpieczeń i podmieniania plików w trakcie uruchamiania lub działania gry.
Tekst nie musi znajdować się w zwykłym pliku `.txt`: może być wartością w
kontenerze binarnym. Fizyczny sposób zapisu i jego skutki wymagają rozpoznania;
nie zakładamy, że zmiana jedynie tekstowych wartości pozostawi resztę bajtów
kontenera niezmienioną. Jeśli klient automatycznie przywraca plik, nie obchodzimy
tego mechanizmu.

Kontynuujemy na źródłach publicznych i próbkach syntetycznych. Właściciel
zgłosił instalację Steam, ale nie mamy dostępu do jej plików. Proponowane
[oględziny nazw i rozmiarów](STEAM_REFERENCE.md) nie wymagają otwierania plików.
Nie żądamy ani nie modyfikujemy rzeczywistych plików bez uzgodnienia
konkretnego planu, kopii i sposobu przywrócenia. Nie wymagamy ponownego
potwierdzenia wybranego kierunku. Opcjonalny, niewysłany
[szkic kontaktu z wydawcą](PUBLISHER_PERMISSION.md) może pomóc wyjaśnić zakres
praw, ale nie jest warunkiem kontynuowania pracy syntetycznej.

Warianty Steam / launcher / Epic, polski instalator oraz Kaption porównano w
[WINDOWS_OPTIONS.md](WINDOWS_OPTIONS.md). Użytkownik preferuje natywną polską
wersję z własnym tłumaczeniem; nakładka jest tylko wariantem rezerwowym.

## Wcześniejsze prace społeczności — kandydaci, nie nasze potwierdzenia

1. [`oratakashi/where-winds-meet-indonesian-patch`](https://github.com/oratakashi/where-winds-meet-indonesian-patch/tree/2289aacd076b7f7541e741760d6c18a0570b37a0)
   (commit `2289aacd076b7f7541e741760d6c18a0570b37a0`, **GPL-3.0**) ma
   [opis techniczny](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/docs/Technical-Overview.md)
   i [specyfikację formatu](https://github.com/oratakashi/where-winds-meet-indonesian-patch/blob/2289aacd076b7f7541e741760d6c18a0570b37a0/Obsidian-Vault/knowladge/Format-Spec.md).
   Autorzy opisują m.in. pliki `translate_words_map_en`, `_diff`, `__small`
   i `_mobile`, skompresowane bloki oraz adresowanie rekordów skrótami.
   Deklarują też round-trip i opisują różnice klientów. Ich liczby i wyniki
   dotyczą **ich konkretnych wydań**, nie instalacji właściciela. Nasza próba
   na syntetycznym kontenerze v1 (2 rekordy) potwierdziła prosty dump/patch i
   odrzucenie błędnego hasha, ale wykazała, że duplikat edycji jest przyjmowany
   z zasadą „ostatni wygrywa”, a hash nie jest obowiązkowy. Potrzebny jest więc
   nasz ścisły importer i wiązanie całej zwrotki ze źródłem; szczegóły w
   [dzienniku](EXPERIMENT_LOG.md). To nie jest test na grze.
2. [`lehieugch68/WWM-Locale-Editor`](https://github.com/lehieugch68/WWM-Locale-Editor/tree/fc76ec74aed9b8e8435d035e0e389d05aa444eee)
   (commit `fc76ec74aed9b8e8435d035e0e389d05aa444eee`, **MIT**) deklaruje
   eksport do CSV i import dla plików lokalizacji. Jest starszy, korzysta z
   .NET Framework/ZstdNet; nie weryfikowaliśmy go na bieżącej wersji gry. Z
   przeglądu kodu nie wynika obsługa zwrotek częściowych ze strażnikami
   aktualności, tokenów i atomowości wymaganymi w naszym projekcie.
3. [`dest1yo/wwm_utils`](https://github.com/dest1yo/wwm_utils/tree/3992ebf8769a06edc07859d1a1a16b2724024421)
   (commit `3992ebf8769a06edc07859d1a1a16b2724024421`, **GPL-3.0**) deklaruje
   rozpakowanie/spakowanie map; jego README zaznacza brak scalania `_diff`, a
   [zgłoszenie #6](https://github.com/dest1yo/wwm_utils/issues/6) wskazuje na
   nowy wariant plików w kliencie chińskim. Nie traktować tego narzędzia jako
   uniwersalnego dla każdej aktualizacji ani archiwów `.mpk`.
4. [Dyskusja ResHax](https://reshax.com/topic/18528-where-winds-meet-zzz4messiah/)
   i dokumentacja projektów wskazują na silnik Messiah i kandydatów na mapy
   lokalizacji. To dobry trop, **nie** dowód budowy i kompletności plików w
   wybranym przez właściciela wydaniu.

Narzędzi ani cudzych tłumaczeń nie skopiowano do repozytorium. Licencja kodu
naszego projektu nie jest jeszcze wybrana; użycie/kopiowanie kodu GPL lub MIT
wymaga osobnej decyzji i spełnienia odpowiednich warunków licencji. Licencja
narzędzia nie udziela praw do tekstów ani plików gry.

## Co trzeba rozstrzygnąć przed ekstrakcją

- **Edycja:** właściciel zgłosił Windows/Steam i oznaczenia z ekranów oraz
  Steam ([szczegóły](STEAM_REFERENCE.md)); nie znamy regionu ani nie
  potwierdziliśmy stanu plików. Ścieżki jednego klienta mogą nie pasować do
  oficjalnego launchera ani Epic.
- **Źródła:** czy potrzebne mapy rzeczywiście istnieją i które warstwy są
  aktywne; zgodność wersji, `_diff`, usunięć, wariantów i powtórzeń. Nie
  przypisywać rekordów wyłącznie po pozycji w pliku.
- **Język i kontekst:** co jest oryginałem, co referencją, jak odtworzyć
  mówcę, kolejność i warianty. Mapa klucz→wartość nie dowodzi kompletności
  scen ani chronologii czytanki.
- **Aktualizacje:** autorzy projektu indonezyjskiego raportują przywracanie
  części plików przy aktualizacjach, a dla Steam także `_diff` przy starcie.
  Nie jest to nasz test. Potrzebna metoda zgodna z przyjętym zakresem prac;
  nie planujemy obchodzenia kontroli integralności ani podmiany podczas startu.
- **Jakość:** znaki polskie, tokeny, kontekst, limity, pełny backup/rollback i
  test w grze pozostają niezweryfikowane.

Następnym krokiem mogą być [oględziny nazw i rozmiarów](STEAM_REFERENCE.md)
w Eksploratorze, bez otwierania lub przesyłania plików gry. Opcjonalne
narzędzie [raportu metadanych](INVENTORY.md) testowano tylko syntetycznie.
Przed publicznym ujawnieniem danych tekstowych trzeba osobno ustalić prawa
i zgodę właściciela.
