# Sniffer paczek `.mpk` — jak obejść brakujące powiązania bez ruszania gry

## 1. Najpierw odpowiedź na pytanie o „sniffer runtime”

Pomysł jest dobry, ale **nie polecam dotykania procesu gry**. Powody:

- gra jest sieciowa (NetEase), więc prawie na pewno ma anty-cheat; czytanie
  pamięci obcego procesu to dokładnie ta czynność, którą takie programy
  wykrywają. Kara spada na Twoje konto, nie na moje,
- z pamięci i tak nie odczytalibyśmy „tabeli powiązań”, tylko **stos bajtów
  w nieznanym formacie**: trzeba by robić zrzuty w dwóch scenach, porównywać
  adresy i zgadywać, co jest identyfikatorem, a co przypadkową liczbą,
- to samo, czego szukamy, leży **w plikach** — a pliki można czytać bez ryzyka.

Dlatego proponuję drogę offline: **sondowanie paczek `.mpk`**, a nie pamięci.

## 2. Co robi `collector/sniffer_mpk.ps1`

Nie rozpakowuje paczki w całości. Dla każdego pliku `.mpk`:

1. czyta **nagłówek** (pierwsze 4 KB) i **ogon** (ostatnie 512 B) i zapisuje je
   jako zrzut hex + tekst — po tym poznam format kontenera i to, czy indeks leży
   na początku czy na końcu,
2. liczy **entropię** nagłówka (0 = same zera, 8 = dane spakowane/losowe),
3. rozpoznaje **magię kompresji** (`zstd`, `lz4`, `gzip`, `zip`, `xz`, `7z`,
   `oodle`),
4. przegląda bajty paczki i szuka **jawnych nazw ścieżek**: `client/dialogs`,
   `client\dialogs`, `.etsb`, `.dialog`, `storyline` — w kodowaniu `latin1`
   i `utf16le` (nazwy w paczkach bywają zapisane szeroko),
5. przy każdym trafieniu zapisuje **okienko** (domyślnie 32 KB) wokół offsetu —
   z tego odczytam strukturę indeksu: gdzie są offsety, długości, flagi,
6. robi `RAPORT.json`, `PODSUMOWANIE.txt` i pakuje wszystko do
   `sniffer_mpk_wynik.zip` (kilka MB, nie gigabajty).

**Czego nie robi:** nie uruchamia gry, nie czyta pamięci, nie modyfikuje plików
gry (otwiera je tylko do odczytu), nie wysyła nic do sieci, nie kopiuje całej
paczki.

## 3. Jak uruchomić

- Dwuklik: `collector/SNIFFER_MPK.bat` (zapyta o folder gry).
- Albo z parametrami:

```
powershell -ExecutionPolicy Bypass -File .\sniffer_mpk.ps1 -Szybki
powershell -ExecutionPolicy Bypass -File .\sniffer_mpk.ps1 -Plik "D:\...\pak0.mpk"
powershell -ExecutionPolicy Bypass -File .\sniffer_mpk.ps1 -Gra "D:\Steam\steamapps\common\Where Winds Meet" -LimitPlikow 5
```

Tryby:

| tryb | co przegląda | kiedy |
|---|---|---|
| `-Szybki` | pierwsze 32 MiB i ostatnie 32 MiB każdej paczki | **na pierwszy raz** — indeks często leży na końcu |
| domyślny | całą paczkę, kawałkami po 8 MiB | gdy szybki nic nie znajdzie |

Najlepiej zacząć od `-Szybki`, na 3 paczkach. Jeśli w którejś są nazwy ścieżek —
wiemy, że format da się ruszyć i wtedy warto puścić całość na większej liczbie
plików. Jeśli wszystkie są wysokoentropijne (entropia ok. 7,9–8,0) i bez nazw —
paczki są spakowane/zaszyfrowane w całości i zostaje tylko plan B.

## 4. Co mi odesłać

Tylko `sniffer_mpk_wynik.zip` (kilka MB). Nie wysyłaj paczek `.mpk` — 1 GB
sztuka nic tu nie da, a dane gry nie mogą wychodzić w całości.

## 5. Co z tym zrobię

- **Nazwy ścieżek widoczne** → z okienek odczytam rekord indeksu (offset,
  długość, ścieżka) i napiszę po swojej stronie wycinarkę: dostanę **tylko**
  pliki `client/dialogs/**.etsb` (kilka-Kilkanaście KB każdy), a z nich
  następstwo scen.
- **Widoczna tylko magia `zstd`/`lz4`** → dopiszę dekompresor (mam `zstandard`);
  wtedy potrzebne będą okienka z początku i końca, żeby ustalić układ bloków.
- **Entropia 8,0 i zero nazw** → paczki są szyfrowane; wtedy uczciwie
  powiem, że ta droga jest zamknięta, i wrócimy do rozmowy o planie B.

## 6. Plan B: sniffer pamięci (tylko jeśli zdecydujesz świadomie)

Technicznie da się: PowerShell + `Add-Type` z C# (bez Pythona, bez kompilatora —
`csc` jest w Windows), `OpenProcess` + `ReadProcessMemory`, przegląd regionów
pamięci gry pod kątem znanych identyfikatorów scen (np. `4700001`), zapis
512-bajtowych kontekstów wokół trafień. Zrzut z dwóch scen + porównanie adresów
daje kandydatów na pole „następna scena”.

Czego to **nie** rozwiązuje: nie ma gwarancji, że następstwo w ogóle jest
w pamięci jako liczba (może być wczytywane leniwie z pliku `.etsb`), a ryzyko
dla konta jest realne. Dlatego zrobię to dopiero, gdy:

1. napiszesz, że w folderze gry **nie ma** anty-cheata (albo że akceptujesz
   ryzyko), oraz
2. skończymy plan A — bo taniej i bezpieczniej.

## 7. Stan narzędzia

- `collector/sniffer_mpk.ps1` — czysto ASCII, CRLF, BOM, tylko `FileAccess.Read`,
  bez `Set-ExecutionPolicy`; sprawdzane statycznie przez
  `tests/test_sniffer_mpk.py` (7 testów),
- `collector/SNIFFER_MPK.bat` — dwuklik,
- na Windows nie było jeszcze uruchamiane — pierwszy przebieg u Ciebie.
