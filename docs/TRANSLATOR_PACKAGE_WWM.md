# Paczka dla Tłumacza — format docelowy (WWM)

Wzorzec: `plik_dla_tlumacza_v8.zip` z projektu SRW Y
(`mtgcrawler` → `srw-oe-translation`). Ten dokument opisuje, jak ten sam
proces przenosimy na *Where Winds Meet*, i **co jeszcze blokuje** jego
uruchomienie. Nie jest instrukcją gotową do wysłania tłumaczowi.

## 1. Co dostaje tłumacz (układ jak w SRW)

Jedna paczka ZIP:

| plik | treść |
|---|---|
| `README.md` | instrukcja: co wpisywać, gdzie, jakich znaków nie ruszać |
| `sceny.zip` | fabuła: dialogi i narracja w kolejności scen, z mówcą i uczestnikami |
| `widoki.zip` | nazwy i tabele: postacie, bronie, umiejętności, przedmioty, interfejs, teksty misji |

Tłumacz wypełnia **jedną linię na element** — `PL:` — i odsyła pliki `.md`
bez zmiany nazw, numerów i kolejności. Nie dostaje JSON-ów, narzędzi ani
plików gry.

## 2. Różnica względem SRW Y

| | SRW Y | WWM |
|---|---|---|
| źródło | japoński tekst w grze | **angielski** tekst gry (`translate_words_map_en`) |
| język istniejący w grze | EN (oficjalne) | brak PL, EN jest wersją oficjalną |
| element | `1. [Dialog - ヒイロ] 「…」` + `EN:` + `PL:` | `1. [Dialog - <mówca>] <tekst EN>` + `EN:` + `PL:` |
| limit pola | zmierzony (B / jednostki na linię) | **nieznany** — musi być zmierzony, nie zgadywany |
| zapis zwrotny | sprawdzony (kontener przebudowany) | **nieznany** |

Proponowany szkic elementu (do zatwierdzenia po pomiarach):

```text
## Scena 12/4386 — <identyfikator chunku>
- grupa: <katalog/plik źródłowy>
- uczestnicy:
  - <mówca EN>

1. [Dialog - <mówca>] <pierwsza linia tekstu EN>
   kontynuacja tekstu EN
   id: <stabilny klucz z mapy>
   limit: <do zmierzenia>
   EN: <tekst EN w jednej lub kilku liniach>
   PL:
2. [Narracja] …
   id: …
   limit: …
   EN: …
   PL:

_koniec sceny_
```

Markup gry (`#Y…#E`, `#G…#`, `#Z…#E`, `$T(5001)`, `{}`) jest **nieprzetłumaczalny**
i musi zostać bez zmian — jak `%s` i `＠0` w SRW.

## 3. Co jest już gotowe

- Odebrany i zweryfikowany materiał: mapa EN 50 550 179 B, dwa `_diff`,
  `MANIFEST` ×2, `data3`, `data205` (patrz [COLLECTOR.md](COLLECTOR.md)).
- Struktura kontenera i dekompresja: 4386/4386 chunków, każdy z ramką zstd na
  stałym przesunięciu 9; tekst leży w chunku jako **jeden ciągły blob** UTF-8
  z markupem. Narzędzie: `tools/locale_container.py` + testy.
- Skala: **1 122 784 wpisów** z nagłówków chunków, 94 581 912 B rozpakowanego
  payloadu (patrz [LOCALE_CONTAINER.md](LOCALE_CONTAINER.md)).

## 4. Co blokuje wysłanie paczki

1. **Indeks `klucz → tekst` w chunku nie jest rozłożony.** Rekordy nie mają
   stałej długości: test „suma długości = rozmiar bloba” nie przechodzi dla
   żadnego układu 2/4/8/16/20/24 B, więc kodowanie jest zmienne (varint lub
   bitowe). Bez kluczy nie ma `id`, nie ma zapisu zwrotnego i nie ma audytu
   aktualizacji.
2. **Mówca i kolejność scen** nie są widoczne w samej mapie. W SRW pochodziły
   z rekordów scen w kontenerach gry. W WWM trzeba je pozyskać z innych
   pojemników (`data*`/`index*`) albo z kolejności chunków — to hipoteza do
   sprawdzenia, nie ustalenie.
3. **Limity pól** są nieznane. W SRW zmierzono je z oryginału i sprawdzono
   w grze. Tutaj trzeba zmierzyć realną długość istniejących tekstów EN per
   kategoria i **oznaczyć to jako nieweryfikowane w grze**.
4. **Zapis zwrotny** — nie wolno zakładać, że wystarczy podmienić blob.
   Kolejność, kompresja, sumy i zachowanie klienta są niesprawdzone.

## 5. Proces docelowy (po odblokowaniu)

```text
audyt instalacji → ekstrakcja (klucz, tekst, kontekst) → PLN paczka .md
     → Tłumacz (PL:) → import do pakietu → patcher (lokalnie u właściciela)
     → test w grze → raport
```

Aktualizacja po patchu gry:

1. audyt: porównanie inwentarza i SHA-256 plików lokalizacyjnych,
2. ekstrakcja **nowych i zmienionych** wpisów (mapa `_diff` jest do tego
   naturalnym kandydatem, ale jej kierunku użycia nie sprawdzono),
3. nowa paczka `.md` tylko z różnicami,
4. zwrotka tłumacza → import → patch aktualizacyjny.

## 6. Zasady, które zostają

- Pliki gry, ekstrakty i paczki robocze trzymamy w ignorowanym `local/`;
  do Git trafia wyłącznie kod, testy i dokumentacja.
- Nie wysyłamy tłumaczowi niczego poza tekstem potrzebnym do pracy.
- Żadnego dopasowywania „na oko”: błąd klucza, brak wpisu lub zmiana formatu
  ma zatrzymywać operację, a nie powodować cichy, częściowy zapis.

## Generator paczki

Paczkę buduje `tools/build_translator_pack.py`:

```text
python3 tools/build_translator_pack.py wpisy.jsonl katalog_paczki --grupa "Tekst"
```

Wejście: JSONL, po jednym obiekcie `{"id": "...", "text": "..."}` na linię
(`id` to hash wpisu z gry). Wyjście: `README.md`, `widoki/<nazwa>.md`,
`tokeny.tsv`. Nazwę widoku ustala się potem przez zmianę nazwy pliku — numeracja
w pliku jest stała i nie zależy od nazwy.
