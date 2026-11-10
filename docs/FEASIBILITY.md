# Where Winds Meet — rozpoznanie i wykonalność

Stan: **2026-11-10**. To przegląd publicznych źródeł, bez dostępu do instalacji
właściciela. Rozróżniamy deklaracje wydawcy, wyniki innych projektów oraz
własny test na próbce syntetycznej. Nie wybrano jeszcze platformy ani wersji
docelowej; nie przeprowadzono testu na plikach gry.

## Fakty z oficjalnych źródeł

- [Steam — karta gry](https://store.steampowered.com/app/3564740/Where_Winds_Meet/)
  (app ID `3564740`) podaje Windows 10/11 dla wersji PC, wymaga połączenia
  szerokopasmowego i wymienia tryby solo oraz sieciowe. Na dzień przeglądu w
  wykazie języków interfejsu/napisów nie ma polskiego. To **nie** ustala, jaką
  platformę lub edycję ma właściciel.
- Ta sama karta opisuje także generowany w czasie rzeczywistym tekst i głos
  niektórych NPC. Nie wolno więc zakładać, że jednorazowy ekstrakt statycznych
  tekstów obejmie wszystkie możliwe wypowiedzi ani że sam zapewni czytankę.
- [Warunki na oficjalnej stronie gry](https://www.wherewindsmeetgame.com/termsofuse.html)
  oraz [EULA powiązana ze stroną Steam](https://store.steampowered.com/eula/3564740_eula_0)
  (ostatnia aktualizacja podana w obu tekstach: 2024-12-15) w §3.2(b)(5)
  ograniczają m.in. modyfikację i tłumaczenie Software/Services, o ile warunki
  na to nie pozwalają; §4.5(a) zakazuje m.in. nieautoryzowanych narzędzi i
  modyfikacji. Stosowanie do planowanego spolszczenia wymaga wyjaśnienia z
  wydawcą lub osobą doradzającą prawnie — nie przesądzamy skuteczności tych
  postanowień w konkretnej jurysdykcji.
- W [oficjalnym komunikacie o sankcjach](https://www.wherewindsmeetgame.com/news/official/Banreport727.html)
  wydawca opisuje reakcje na nieautoryzowane narzędzia i nieprawidłowe
  zachowania, włącznie z czasowymi lub stałymi blokadami. Komunikat **nie
  rozstrzyga**, czy konkretne spolszczenie zostanie wykryte lub ukarane.
  Nie wolno obiecywać bezpieczeństwa konta ani obchodzić zabezpieczeń.

**Bramka:** przed użyciem narzędzi na rzeczywistej grze, zmianą plików lub
uruchomieniem zmodyfikowanego klienta ustalić właściwe warunki dla wydania i
uzyskać decyzję właściciela co do dalszego postępowania; rekomendowany kontakt
z wydawcą w sprawie zgody. Do tego czasu pracujemy na źródłach publicznych i
próbkach syntetycznych, bez uruchamiania gry lub narzędzi społecznościowych na
pliku właściciela. Decyzja właściciela sama w sobie nie jest zgodą wydawcy.

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

- **Edycja:** PC/Steam, oficjalny launcher, inna platforma i region, numer
  wersji/builda; ścieżki opisane dla jednego klienta nie muszą pasować do innego.
- **Źródła:** czy potrzebne mapy rzeczywiście istnieją i które warstwy są
  aktywne; zgodność wersji, `_diff`, usunięć, wariantów i powtórzeń. Nie
  przypisywać rekordów wyłącznie po pozycji w pliku.
- **Język i kontekst:** co jest oryginałem, co referencją, jak odtworzyć
  mówcę, kolejność i warianty. Mapa klucz→wartość nie dowodzi kompletności
  scen ani chronologii czytanki.
- **Aktualizacje:** autorzy projektu indonezyjskiego raportują przywracanie
  części plików przy aktualizacjach, a dla Steam także `_diff` przy starcie.
  Nie jest to nasz test. Potrzebny jawnie dozwolony sposób działania; nie
  planujemy obchodzenia kontroli integralności.
- **Jakość:** znaki polskie, tokeny, kontekst, limity, pełny backup/rollback i
  test w grze pozostają niezweryfikowane.

Po decyzji o zakresie i sposobie pracy następnym wejściem powinien być możliwie
mały [raport metadanych](INVENTORY.md), nie pełny katalog gry. Przed publicznym
ujawnieniem jakichkolwiek danych tekstowych trzeba osobno ustalić prawa i zgodę
właściciela.
