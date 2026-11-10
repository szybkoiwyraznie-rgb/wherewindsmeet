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
tekstów gry, kluczy, formatów ani szczegółowych decyzji SRW Y. Wybór języka
źródłowego i techniki tłumaczenia tej gry nie został jeszcze dokonany.

## Where Winds Meet

Badanie wcześniejszych narzędzi, formatów oraz zasad gry **nie zostało jeszcze
przeprowadzone**. Przyszłe ustalenia, źródła, licencje i daty zapisywać tutaj
z rozróżnieniem faktów i hipotez.
