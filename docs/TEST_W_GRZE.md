# Plan pierwszego testu w grze (UI + prolog + polskie znaki)

To najkrótsza i bezpieczna próba sprawdzenia w prawdziwym kliencie Steam:
1. czy gra przyjmuje przepisane pliki `translate_words_map_*` bez błędu
   i bez automatycznego cofnięcia przez launcher,
2. czy wbudowane czcionki — zarówno **interfejsu (menu i ustawienia)**, jak
   i **napisów filmowych w otwierającym prologu** — wyświetlają wszystkie
   polskie znaki diakrytyczne (`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`)
   bez pustych ramek (`□`) i ucięć.

Test zmienia wyłącznie kilkanaście etykiet menu głównego / ustawień oraz 7
początkowych kwestii otwierającej cutscenki prologu (wiersze `590336–590351`
tabel `text_msg` i `text_msg__grey`, m.in. `Even at the end of the road,` /
`a drink to wet your throat.`), bez modyfikacji plików `.exe`, `.dll` ani
pamięci procesu.

**Zastrzeżenie:** test nie był jeszcze uruchomiony w prawdziwej grze.
Projekt nie gwarantuje bezpieczeństwa konta ani zgodności z warunkami wydawcy.

---

## Krok 1: Zbudowanie małej paczki testowej (po stronie narzędzi)

Narzędzie `tools/latka_testowa.py` tworzy w izolowanym folderze tymczasowym
zestaw etykiet UI (`TEST_LABELS`) i pierwszych napisów prologu
(`PROLOG_LINES`, dopasowywanych parą `(EN, ZH)`, bez ruszania magazynu
`tlumaczenie/`) i pakuje gotowy ZIP ze skryptami z `instalator/`:

```bash
python3 tools/latka_testowa.py \
  --indeks index \
  --zh sciezka/translate_words_map_zh_cn sciezka/translate_words_map_zh_cn_diff \
  --mapa Package/HD/oversea/locale/translate_words_map_en sciezka/pkg_en \
  --mapa Package/HD/oversea/locale/translate_words_map_en_diff sciezka/pkg_en_diff \
  --mapa LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff sciezka/patch_en_diff \
  --build-gry 25906190 \
  --zakres ui+prolog \
  --wyj-zip dist/WWM_LATKA_TEST_PL.zip
```

Zakres można też zawęzić przez `--zakres ui` (samo menu) albo `--zakres prolog`
(same napisy cutscenki otwarcia).

Testowane napisy UI obejmują komplet polskich znaków:
- `Settings` → `Ustawienia [PL: ą ć ę ł ń ó ś ź ż]`
- `Audio` → `Dźwięk [Ą Ć Ę Ł Ń Ó Ś Ź Ż]`
- `Controls` → `Sterowanie [PL]`
- `Display` → `Wyświetlanie [PL]`
- `Language` → `Język [ąęółńśźż]`
- `Storage` → `Pamięć i pliki [PL]`
- `Text Magnification` → `Powiększenie tekstu [PL]`
- `Parental Controls` → `Kontrola rodzicielska [PL]`
- `New Game` → `Nowa gra [PL]`
- `Exit` → `Wyjście [PL]`

Testowane kwestie prologu (dopasowanie `(EN, ZH)` z `text_msg` / `text_msg__grey`):
- `It's you.` (`是你`) → `To ty [PL: ą ć ę ł ń ó ś ź ż].`
- `Yes. Coming to catch you.` (`是啊 来抓你`) → `Tak. Przyszliśmy cię pojmać [Ą Ć Ę Ł Ń Ó Ś Ź Ż].`
- `Even at the end of the road,` (`穷途末路`) → `Nawet u kresu drogi [ą ć ę ł ń ó ś ź ż],`
- `a drink to wet your throat.` (`尚有一饮入喉`) → `łyk trunku zwilży gardło [Ą Ć Ę Ł Ń Ó Ś Ź Ż].`
- `Well? How is it?` (`如何`) → `I jak? Smakuje [ą ć ę ł ń ó ś ź ż]?`
- `Bland.` (`淡`) → `Mdłe [Ą Ć Ę Ł Ń Ó Ś Ź Ż].`
- `Retrieve the Zhenguan Jade!` (`夺下镇冠珏`) → `Odbierzcie Nefryt Zhenguan [ąęółńśźż]!`

---

## Krok 2: Instalacja i kopia zapasowa (Windows, gra zamknięta)

1. Zamknij grę i upewnij się, że Steam nie pobiera aktualizacji.
2. Rozpakuj `WWM_LATKA_TEST_PL.zip` do nowego folderu poza katalogiem gry (np. na Pulpicie).
3. Opcjonalnie kliknij `SPRAWDZ_STAN.bat`, aby zobaczyć stan przed zmianą (`ORYGINAL`).
4. Kliknij dwa razy `ZAINSTALUJ.bat` (albo przeciągnij na niego główny folder gry).
   - Skrypt sprawdzi, czy gra jest wyłączona, czy `buildid` ze Steam pasuje do łatki
     oraz czy każdy plik w grze ma dokładny oryginalny skrót SHA-256.
   - Zapisze oryginały poza folderem gry w `%LOCALAPPDATA%\WhereWindsMeetPL\kopia`.
   - Dopiero potem skopiuje zmienione mapy i sprawdzi ich SHA-256 po zapisie.
   - Jeśli dowolny krok się nie powiedzie, automatycznie cofnie zmienione pliki.

---

## Krok 3: Szybka kontrola w grze (2–3 minuty)

1. Uruchom grę normalnie przez Steam (język gry ustawiony na angielski).
2. Zatrzymaj się na **ekranie tytułowym** i otwórz **Ustawienia (`Settings`)**:
   - sprawdź, czy klient uruchomił się bez komunikatu o uszkodzonych plikach,
   - sprawdź, czy nie pobrał ponownie plików w trakcie startu,
   - przejrzyj zakładki (`Settings`, `Audio`, `Controls`, `Display`, `Language`),
   - zwróć uwagę, czy widać wszystkie litery `ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`
     oraz czy żadna etykieta nie została ucięta.
3. Kliknij **Nowa gra** (lub obejrzyj otwierający filmik prologu):
   - sprawdź napisy z pierwszych scen (`To ty...`, `Nawet u kresu drogi...`,
     `łyk trunku zwilży gardło...`),
   - zweryfikuj, czy **czcionka napisów filmowych/dialogowych** (która może być
     inna niż czcionka menu!) również wyświetla komplet polskich liter bez
     pustych ramek (`□`).
4. Zrób zrzut ekranu (albo zanotuj dokładnie, które litery brakują / wyglądają inaczej)
   i wyjdź z gry.

---

## Krok 4: Obowiązkowe przywrócenie oryginału i weryfikacja

1. Po zamknięciu gry kliknij dwa razy `PRZYWROC.bat` w folderze łatki.
2. Kliknij `SPRAWDZ_STAN.bat` i upewnij się, że przy każdym pliku jest `gra=ORYGINAL`.
3. (Alternatywnie w każdej chwili działa także „Sprawdź spójność plików gry” w Steam.)

---

## Co przekazać po próbie

- Czy `ZAINSTALUJ.bat` i `PRZYWROC.bat` przeszły bez błędu.
- Czy gra uruchomiła się z podmienionymi mapami i nie nadpisała ich przy starcie.
- Czy wszystkie polskie znaki (`ą ć ę ł ń ó ś ź ż Ą Ć Ę Ł Ń Ó Ś Ź Ż`) wyświetliły
  się poprawnie (zrzut ekranu / opis brakujących glifów, jeśli czcionka nie ma
  rozszerzenia Latin Extended).
