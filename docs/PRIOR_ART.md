# Źródła i przeniesione praktyki

## Projekt właściciela: mtgcrawler / SRW Y

Wzorzec wskazany przez właściciela:
[`szybkoiwyraznie-rgb/mtgcrawler`](https://github.com/szybkoiwyraznie-rgb/mtgcrawler).
Przejrzany stan `main`: commit
[`76f8471d13f2cef8700c703ab109de1962e7b8e8`](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/commit/76f8471d13f2cef8700c703ab109de1962e7b8e8),
2026-11-10. Odnośniki poniżej są przypięte do tego stanu.

| Źródło | Co adaptujemy tutaj |
|---|---|
| [Główne AGENTS.md](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/AGENTS.md) i [AGENTS SRW Y](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/AGENTS.md) | Roboczy PR i częste checkpointy, oddzielenie danych gry, notatki dla następnej sesji, uczciwe rozróżnianie wyników i niepewności. |
| [FEASIBILITY.md](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/docs/FEASIBILITY.md) | Rozpoznanie od metadanych, małe próbki, kryteria powodzenia, odrębny test glifów i instalacji. |
| [IMPORTER_Y.md](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/docs/IMPORTER_Y.md) | Wiązanie zwrotki ze źródłem, weryfikacja struktury i tokenów, częściowe partie oraz odmowa zapisu przy błędach. |
| [READING_Y.md](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/srw-y-translation/docs/READING_Y.md) | Czytanka oparta na danych, raportowanie luk i brak zgadywania kolejności. |
| [CI importera](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/.github/workflows/srw-y-import.yml) i [workflow wydania](https://github.com/szybkoiwyraznie-rgb/mtgcrawler/blob/76f8471d13f2cef8700c703ab109de1962e7b8e8/.github/workflows/release-y.yml) | Testy repo-only, rozdzielenie kontroli PR od publikacji, sumy kontrolne i ochrona prywatnych informacji w opisach wydań. |

W przejrzanym drzewie wzorca nie było pliku `ENVIRONMENT`; tutejszy
`ENVIRONMENT.md` jest nową instrukcją dla tego projektu. Nie kopiujemy kodu,
tekstów gry, kluczy, formatów ani szczegółowych decyzji SRW Y. Właściciel
preferuje niezależne tłumaczenie z dobrym modelem; język źródłowy i konkretny
model nie zostały jeszcze wybrane.

## Where Winds Meet

Pierwszy przegląd oficjalnych warunków i wcześniejszych narzędzi zapisano w
[FEASIBILITY.md](FEASIBILITY.md), wraz z przypiętymi commitami, licencjami,
ograniczeniami i rozróżnieniem deklaracji społeczności od naszych testów.
Analizę kodu instalatora Arimy i klienta Kaption, wraz z ograniczeniami licencji
oraz rekomendacją Windows/Steam, zawiera [WINDOWS_OPTIONS.md](WINDOWS_OPTIONS.md).
Osobne [badanie aktualizacji, warstw i backupów](UPDATES_AND_RESTORE.md)
porównuje przypięty kod projektów indonezyjskiego, wietnamskiego i Arimy z
podejściem SRW. To analiza, nie test działania tych rozwiązań w grze.
Żadne cudze narzędzie ani dane gry nie zostały skopiowane do repozytorium.

## Format tabeli — co wzięliśmy z istniejących narzędzi

Format kontenera i tabeli jest już rozpracowany przez społeczność; nie ma sensu
prowadzić śledztwa od zera. Sprawdzone źródła (kod czytany, nie kopiowany):

| Projekt | Co potwierdza |
|---|---|
| [`dest1yo/wwm_utils`](https://github.com/dest1yo/wwm_utils) — `src/core.rs`, `src/structs.rs` | Pełny układ: `MapHeader` 12 B, tabela przesunięć `u32[count+1]`, `BlockHeader` 9 B, `TableHeader` 24 B, `buckets` = `max(entry_count+17, 24)`, `TableEntry` 16 B, pozycja tekstu `entries_pos + 16*index + 8 + offset`, przeliczanie offsetów przy zapisie, `0xFF` = zaślepka. |
| [`lehieugch68/WWM-Locale-Editor`](https://github.com/lehieugch68/WWM-Locale-Editor) — `WWMLocale.cs` | Ten sam format w C#, potwierdza niezależnie. |
| [`oratakashi/where-winds-meet-indonesian-patch`](https://github.com/oratakashi/where-winds-meet-indonesian-patch) | Że pełny patch tłumaczeniowy jest wykonalny. |
| [`arimacold/wwm-spolszczenie`](https://github.com/arimacold/wwm-spolszczenie) | Polski patcher jako punkt odniesienia dla instalacji. |

Wszystkie ustalenia powtórzyliśmy na własnych danych (parsowanie 1 122 784 wpisów
i przepakowanie 8549 chunków bez straty), więc nie opieramy się na deklaracjach.
Kodu i tekstów tych projektów nie kopiujemy.

## Najpełniejsza specyfikacja formatu: projekt indonezyjski

[`oratakashi/where-winds-meet-indonesian-patch`](https://github.com/oratakashi/where-winds-meet-indonesian-patch)
zawiera `Obsidian-Vault/knowladge/Format-Spec.md` — opis formatu dokładniejszy niż
w `wwm_utils`. Ustalenia, które zmieniają nasze rozumienie pliku:

| Element | Co mówi specyfikacja | Zgadza się z naszymi danymi |
|---|---|---|
| `capacity` w nagłówku tabeli | 511 = rozmiar tablicy slotów, nie liczba tekstów | tak (`entry_count` 511, `value_count` 244) |
| `ctrl` | `u8[capacity]`: `0x80` = pusty slot, `0xFE` = usunięty, `< 0x80` = zajęty | tak (gęste `0x80` w „indeksie”) |
| dopełnienie | `ctrl` + `0xFF` + 15 B kopii + padding do 8 → 511+1+15+pad = **528** | tak: `max(capacity + 17, 24)` |
| `relOffset` | liczony **od adresu własnego pola**, nie od początku bloku | tak — dlatego suma długości nigdy nie pasowała |
| `seed` | `0x595896DC` wspólny dla całego pliku | tak (i to on wyglądał jak „magic”) |
| sharding | `blok = (keyHash % liczba_bloków_danych) + 1` | spójne z 4386 blokami danych |
| klucz | przechowywany jest tylko `u64 keyHash`; **tekstu klucza nie ma w pliku** | tak |

**Konsekwencja dla patchowania:** zmiana samej wartości istniejącego klucza nie
wymaga przeliczania shardów ani `ctrl` — trzeba tylko przepisać sloty i bloby.
Nasz patcher robi dokładnie to, więc jest zgodny z tą specyfikacją.

**Czego tam nie ma:** mówców, scen ani chronologii. Projekt indonezyjski tłumaczy
płaską listę tekstów (pliki `idx-XXXXXX-YYYYYY.md` to zakresy indeksów), podobnie
`wwm_utils` i `WWM-Locale-Editor` obracają wyłącznie mapą tekstów. Nikt z nich nie
odczytał powiązań tekstów z dialogami.
