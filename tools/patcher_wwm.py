#!/usr/bin/env python3
"""Samowystarczalny lokalny patcher Where Winds Meet (standalone, bez binarek w paczce).

Czyta czysty plan tłumaczenia `plan_latki.json` (`wwm-plan-latki-v1`) oraz
oryginalne mapy tekstowe z dysku gracza, tworzy weryfikowaną kopię zapasową
oryginałów poza folderem gry, przepisuje mapy lokalnie w pamięci, sprawdza
każdy wpis i instaluje transakcyjnie (albo bezpiecznie przywraca oryginały).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

try:
    from tools import apply_translation as patcher
    from tools import locale_records as records
    from tools import mapa_tekstow
except ImportError:  # uruchomienie wewnątrz rozpakowanego `narzedzia/` albo z repo `tools/`
    _here = Path(__file__).resolve().parent
    for _candidate in (_here, _here.parent):
        if (_candidate / "tools").is_dir() and str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
    from tools import apply_translation as patcher
    from tools import locale_records as records
    from tools import mapa_tekstow


PLAN_FORMAT = "wwm-plan-latki-v1"
STAN_FORMAT = "wwm-standalone-install-state-v1"
APP_ID = "3564740"
GAME_PROCESSES = ("WhereWindsMeet.exe", "WWM.exe", "WWM_Game.exe", "yysls.exe")
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


class PatcherError(Exception):
    """Błąd blokujący bezpieczną instalację lub przywrócenie łatki."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            h.update(block)
    return h.hexdigest().lower()


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    if os.name == "nt":
        try:
            import ctypes  # noqa: PLC0415

            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1 and (attrs & FILE_ATTRIBUTE_REPARSE_POINT) != 0:
                return True
        except Exception:
            pass
    return False


def assert_no_reparse_ancestors(path: Path) -> None:
    resolved_probe = path
    cur: Path | None = resolved_probe
    while cur is not None:
        if cur.exists() and _is_reparse_point(cur):
            raise PatcherError(f"Ścieżka lub jej katalog nadrzędny jest linkiem/punktem reparse: {cur}")
        parent = cur.parent
        if parent == cur:
            break
        cur = parent


def assert_no_reparse_optional(path: Path) -> None:
    probe = path
    while probe and not probe.exists():
        parent = probe.parent
        if parent == probe:
            break
        probe = parent
    if probe and probe.exists():
        check_dir = probe if probe.is_dir() else probe.parent
        assert_no_reparse_ancestors(check_dir)


def assert_regular_file(path: Path) -> None:
    assert_no_reparse_ancestors(path.parent)
    if not path.exists() or path.is_dir() or _is_reparse_point(path):
        raise PatcherError(f"Brak zwykłego pliku (albo wykryto link): {path}")


def is_game_root(path: Path) -> bool:
    if not path.is_dir() or _is_reparse_point(path):
        return False
    return (path / "Package").is_dir() or (path / "LocalData" / "Patch").is_dir()


def _get_acf_value(path: Path, key: str) -> str:
    try:
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(rf'(?im)^\s*"{re.escape(key)}"\s*"([^"\r\n]*)"', text)
        return match.group(1).strip() if match else ""
    except OSError:
        return ""


def find_steam_candidates(steam_override: str = "") -> list[tuple[Path, str]]:
    steam_dirs: list[Path] = []
    if steam_override.strip():
        steam_dirs.append(Path(steam_override.strip()))
    else:
        if os.name == "nt":
            try:
                import winreg  # noqa: PLC0415

                for root_key, sub in (
                    (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
                ):
                    try:
                        with winreg.OpenKey(root_key, sub) as key:
                            for val_name in ("SteamPath", "InstallPath"):
                                try:
                                    val, _ = winreg.QueryValueEx(key, val_name)
                                    if isinstance(val, str) and val.strip():
                                        p = Path(val.strip())
                                        if p not in steam_dirs:
                                            steam_dirs.append(p)
                                except OSError:
                                    pass
                    except OSError:
                        pass
            except ImportError:
                pass
        for env_var in ("ProgramFiles(x86)", "ProgramFiles"):
            base = os.environ.get(env_var, "")
            if base:
                p = Path(base) / "Steam"
                if p not in steam_dirs:
                    steam_dirs.append(p)

    libraries: list[Path] = []
    for sdir in steam_dirs:
        if sdir not in libraries:
            libraries.append(sdir)
        vdf = sdir / "steamapps" / "libraryfolders.vdf"
        try:
            if vdf.is_file():
                text = vdf.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r'(?im)^\s*"(?:path|[0-9]+)"\s*"([^"\r\n]+)"\s*$', text):
                    lib = Path(match.group(1).replace("\\\\", "\\"))
                    if lib.is_absolute() and lib not in libraries:
                        libraries.append(lib)
        except OSError:
            pass

    found: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for lib in libraries:
        apps = lib / "steamapps"
        acf = apps / f"appmanifest_{APP_ID}.acf"
        install_dir = _get_acf_value(acf, "installdir")
        build = _get_acf_value(acf, "buildid")
        if not re.fullmatch(r"\d+", build):
            build = ""
        names = ["Where Winds Meet"]
        if install_dir and install_dir not in (".", "..") and "/" not in install_dir and "\\" not in install_dir and ":" not in install_dir:
            names = [install_dir, "Where Winds Meet"]
        for name in names:
            cand = apps / "common" / name
            try:
                if is_game_root(cand):
                    assert_no_reparse_ancestors(cand)
                    full = cand.resolve()
                    key = str(full).casefold()
                    if key not in seen:
                        seen.add(key)
                        found.append((full, build))
            except PatcherError:
                pass
    return found


def read_build_for_game(root: Path) -> str:
    try:
        common = root.parent
        if common.name.lower() != "common" or common.parent.name.lower() != "steamapps":
            return ""
        acf = common.parent / f"appmanifest_{APP_ID}.acf"
        install_dir = _get_acf_value(acf, "installdir")
        build = _get_acf_value(acf, "buildid")
        if install_dir.casefold() == root.name.casefold() and re.fullmatch(r"\d+", build):
            return build
    except OSError:
        pass
    return ""


def choose_game_root(explicit: str, steam_root: str, non_interactive: bool) -> Path:
    if explicit.strip():
        cand = Path(explicit.strip())
        if not is_game_root(cand):
            raise PatcherError(f"Niepoprawny folder gry (brak Package/ lub LocalData/Patch/): {explicit}")
        assert_no_reparse_ancestors(cand)
        return cand.resolve()

    candidates = find_steam_candidates(steam_root)
    if len(candidates) == 1:
        return candidates[0][0]
    if len(candidates) > 1:
        if non_interactive:
            raise PatcherError("Znaleziono kilka instalacji Steam. Wskaż konkretny folder gry przez --game.")
        print("Znaleziono kilka instalacji gry. Wybierz numer:")
        for idx, (path, build) in enumerate(candidates, 1):
            binfo = f" (build {build})" if build else ""
            print(f"  {idx}. {path}{binfo}")
        choice = input("Numer instalacji: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            return candidates[int(choice) - 1][0]
        raise PatcherError("Nie wybrano poprawnego numeru instalacji.")

    if non_interactive:
        raise PatcherError("Nie znaleziono automatycznie folderu Where Winds Meet.")

    print("Nie znaleziono gry automatycznie. Wskaż główny folder gry (ten z folderem Package).")
    selected = ""
    try:
        import tkinter as tk  # noqa: PLC0415
        from tkinter import filedialog  # noqa: PLC0415

        root_tk = tk.Tk()
        root_tk.withdraw()
        selected = filedialog.askdirectory(title="Wybierz główny folder Where Winds Meet") or ""
        root_tk.destroy()
    except Exception:
        selected = ""
    if not selected:
        selected = input("Wpisz pełną ścieżkę folderu gry (albo Enter aby przerwać): ").strip().strip('"')
    if not selected:
        raise PatcherError("Anulowano wybór folderu gry.")
    cand = Path(selected)
    if not is_game_root(cand):
        raise PatcherError(f"Niepoprawny folder gry: {selected}")
    assert_no_reparse_ancestors(cand)
    return cand.resolve()


def _check_game_not_running() -> None:
    if os.name != "nt":
        return
    import subprocess  # noqa: PLC0415

    try:
        res = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
            check=False,
        )
        out = res.stdout.lower()
        for proc in GAME_PROCESSES:
            if f'"{proc.lower()}"' in out:
                raise PatcherError(f"Wygląda na to, że gra działa ({proc}). Zamknij grę przed kontynuacją.")
    except OSError:
        pass


def default_backup_dir(game_root: Path, explicit_backup: str) -> Path:
    if explicit_backup.strip():
        cand = Path(explicit_backup.strip())
    else:
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        tag = hashlib.sha256(str(game_root).casefold().encode("utf-8")).hexdigest()[:12]
        cand = Path(base) / "WhereWindsMeetPL" / f"kopia_standalone_{tag}"
    assert_no_reparse_optional(cand)
    full = cand.resolve()
    game_resolved = game_root.resolve()
    if full == game_resolved or game_resolved in full.parents:
        raise PatcherError("Katalog kopii zapasowej musi znajdować się poza folderem gry.")
    return full


def discover_locale_layers(game_root: Path, jezyk_celu: str) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]]]:
    """Znajdź warstwy `zh_cn` oraz warstwy docelowego języka na dysku gracza."""
    lang = jezyk_celu.lower()
    variants = ("HD/oversea", "HD/v2")
    zh_layers: list[tuple[str, Path]] = []
    target_layers: list[tuple[str, Path]] = []

    for variant in variants:
        for base_rel in (
            f"Package/{variant}/locale/translate_words_map_zh_cn",
            f"Package/{variant}/locale/translate_words_map_zh_cn_diff",
            f"LocalData/Patch/{variant}/locale/translate_words_map_zh_cn",
            f"LocalData/Patch/{variant}/locale/translate_words_map_zh_cn_diff",
        ):
            p = game_root / base_rel
            if p.exists():
                assert_regular_file(p)
                zh_layers.append((base_rel, p))

        for tgt_rel in (
            f"Package/{variant}/locale/translate_words_map_{lang}",
            f"Package/{variant}/locale/translate_words_map_{lang}_diff",
            f"LocalData/Patch/{variant}/locale/translate_words_map_{lang}",
            f"LocalData/Patch/{variant}/locale/translate_words_map_{lang}_diff",
        ):
            p = game_root / tgt_rel
            if p.exists():
                assert_regular_file(p)
                target_layers.append((tgt_rel, p))

    return zh_layers, target_layers


def load_plan(plan_path: Path) -> dict:
    assert_regular_file(plan_path)
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise PatcherError(f"Nieczytelny plik planu {plan_path.name}: {error}") from error
    if not isinstance(plan, dict) or plan.get("format") != PLAN_FORMAT:
        raise PatcherError(f"Nieobsługiwany format planu: {plan.get('format')!r}")
    return plan


def _dopasuj_kolizje(warianty_zh: list[list[str]], current: str, po_kluczu: dict[str, str]) -> str | None:
    for key, rep_en in warianty_zh:
        if rep_en == current:
            return po_kluczu.get(key)
    best_key: str | None = None
    best_sim = 0.0
    for key, rep_en in warianty_zh:
        score = mapa_tekstow.podobienstwo_en(current, rep_en)
        if score > best_sim:
            best_key, best_sim = key, score
    if best_key is not None and best_sim >= 0.5:
        return po_kluczu.get(best_key)
    return None


def compute_wanted_for_map(
    teksty: dict[int, str],
    zh: dict[int, str],
    plan: dict,
) -> tuple[dict[int, str], dict[str, int]]:
    po_id: dict[str, str] = plan.get("po_id", {})
    po_kluczu: dict[str, str] = plan.get("po_kluczu", {})
    kolizje: dict[str, list[list[str]]] = plan.get("kolizje", {})
    en_jednoznaczne: dict[str, str] = plan.get("en_jednoznaczne", {})

    wanted: dict[int, str] = {}
    stats = {"po_id": 0, "po_zh": 0, "po_en": 0, "bez_zmiany": 0}
    for ident, current in teksty.items():
        hex_id = f"{ident:016x}"
        text = po_id.get(hex_id)
        if text is not None:
            stats["po_id"] += 1
        elif ident in zh:
            zh_text = zh[ident]
            if zh_text in kolizje:
                text = _dopasuj_kolizje(kolizje[zh_text], current, po_kluczu)
            else:
                text = po_kluczu.get(mapa_tekstow.klucz(zh_text))
            if text is not None:
                stats["po_zh"] += 1
        if text is None:
            en_key = mapa_tekstow.klucz(current)
            text = po_kluczu.get(en_key)
            if text is None:
                text = en_jednoznaczne.get(en_key)
            if text is not None:
                stats["po_en"] += 1

        if text and text != current:
            wanted[ident] = text
        elif text is not None:
            stats["bez_zmiany"] += 1
    return wanted, stats


def _write_bytes_atomic(dest: Path, data: bytes, expected_sha: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".wwm-latka-", dir=dest.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if _sha256_file(tmp_path) != expected_sha:
            raise PatcherError(f"Błąd weryfikacji zapisu tymczasowego: {dest.name}")
        os.replace(tmp_path, dest)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _read_state(state_path: Path) -> dict | None:
    if not state_path.is_file():
        return None
    try:
        obj = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise PatcherError(f"Uszkodzony plik stanu instalacji {state_path}: {error}") from error
    if obj.get("format") != STAN_FORMAT:
        raise PatcherError(f"Nieznany format stanu instalacji: {obj.get('format')!r}")
    return obj


def _save_state(state_path: Path, state_obj: dict) -> None:
    raw = (json.dumps(state_obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _write_bytes_atomic(state_path, raw, _sha256_bytes(raw))


def _write_report(backup_dir: Path, lines: list[str]) -> Path:
    report_text = "\n".join(lines) + "\n"
    report_path = backup_dir / "RAPORT_LATKI_PL.txt"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8", newline="\n")
    except OSError:
        pass
    if os.name == "nt":
        desktop = Path.home() / "Desktop"
        if desktop.is_dir():
            try:
                (desktop / "RAPORT_LATKI_PL.txt").write_text(report_text, encoding="utf-8", newline="\n")
            except OSError:
                pass
    return report_path


def run_patcher(
    *,
    akcja: str,
    plan_path: Path,
    game_root_arg: str = "",
    steam_root_arg: str = "",
    backup_dir_arg: str = "",
    poziom: int = 9,
    wymus: bool = False,
    pomin_wersje: bool = False,
    non_interactive: bool = False,
) -> tuple[dict, int]:
    plan = load_plan(plan_path)
    jezyk_celu = str(plan.get("jezyk_celu") or "en").lower()
    wymagany_build = str(plan.get("oczekiwany_build") or "").strip()

    if akcja != "stan":
        _check_game_not_running()

    game_root = choose_game_root(game_root_arg, steam_root_arg, non_interactive)
    if str(game_root) == str(Path(game_root.anchor).resolve()):
        raise PatcherError("Nie wskazuj całego dysku jako folderu gry.")
    backup_dir = default_backup_dir(game_root, backup_dir_arg)
    state_path = backup_dir / "stan_instalacji.json"
    existing_state = _read_state(state_path)
    recorded_by_rel: dict[str, dict] = {
        str(row["relative_path"]).casefold(): row
        for row in (existing_state.get("files", []) if existing_state else [])
    }

    live_build = read_build_for_game(game_root)
    zh_layers, target_layers = discover_locale_layers(game_root, jezyk_celu)
    wydanie = str(plan.get("wydanie") or "").strip()

    log_lines = [
        f"Data (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"Akcja: {akcja}" + (f" (wydanie {wydanie})" if wydanie else ""),
        f"Folder gry: {game_root}" + (f" (build {live_build})" if live_build else ""),
        f"Katalog kopii: {backup_dir}",
    ]

    if akcja == "stan":
        if not target_layers and not recorded_by_rel:
            raise PatcherError(f"Brak plików języka {jezyk_celu} i brak zapisanej kopii.")
        all_rels: dict[str, Path] = {rel.casefold(): path for rel, path in target_layers}
        status_rows = []
        seen_keys: set[str] = set()
        for rel, path in target_layers:
            key = rel.casefold()
            seen_keys.add(key)
            cur_sha = _sha256_file(path)
            rec = recorded_by_rel.get(key)
            if rec is None:
                live_state = "ORYGINAL_NIEZAPISANY"
                bak_state = "BRAK_KOPII"
            else:
                if cur_sha == rec["patched_sha256"]:
                    live_state = "ZAINSTALOWANO_LATKE"
                elif cur_sha == rec["original_sha256"]:
                    live_state = "ORYGINAL"
                else:
                    live_state = "ZMIENIONO_PRZEZ_GRE"
                bak_file = backup_dir / rec["backup_relative"]
                if not bak_file.is_file():
                    bak_state = "BRAK_KOPII"
                elif _sha256_file(bak_file) == rec["original_sha256"]:
                    bak_state = "KOPIA_OK"
                else:
                    bak_state = "KOPIA_USZKODZONA"
            status_rows.append({"sciezka": rel, "gra": live_state, "kopia": bak_state})
            line = f"  {rel}: gra={live_state}, kopia={bak_state}"
            print(line)
            log_lines.append(line)
        for key, rec in recorded_by_rel.items():
            if key not in seen_keys:
                rel = rec["relative_path"]
                bak_file = backup_dir / rec["backup_relative"]
                bak_state = "KOPIA_OK" if (bak_file.is_file() and _sha256_file(bak_file) == rec["original_sha256"]) else "BRAK_KOPII"
                status_rows.append({"sciezka": rel, "gra": "BRAK", "kopia": bak_state})
                line = f"  {rel}: gra=BRAK, kopia={bak_state}"
                print(line)
                log_lines.append(line)
        _write_report(backup_dir, log_lines)
        return {"ok": True, "akcja": "stan", "build": live_build, "pliki": status_rows}, 0

    if akcja == "przywroc":
        if existing_state is None or not existing_state.get("files"):
            raise PatcherError(f"Brak zapisanej kopii zapasowej w: {backup_dir}")
        plan_restore: list[dict] = []
        skipped_external = 0
        skipped_missing = 0
        kept_state_records: list[dict] = []

        for rec in existing_state["files"]:
            rel = str(rec["relative_path"])
            target = game_root / rel
            bak_file = backup_dir / rec["backup_relative"]
            if not target.exists():
                if not wymus:
                    skipped_missing += 1
                    msg = f"Pominięto (plik usunięty w grze przez aktualizację): {rel}"
                    print(msg)
                    log_lines.append(msg)
                    continue
                assert_regular_file(bak_file)
                bak_bytes = bak_file.read_bytes()
                if _sha256_bytes(bak_bytes) != rec["original_sha256"]:
                    raise PatcherError(f"Kopia zapasowa ma błędny SHA-256: {rel}")
                plan_restore.append({"rel": rel, "target": target, "bytes": bak_bytes, "sha": rec["original_sha256"], "skip": False})
                kept_state_records.append(rec)
                continue

            assert_regular_file(target)
            cur_sha = _sha256_file(target)
            if cur_sha == rec["original_sha256"]:
                assert_regular_file(bak_file)
                bak_bytes = bak_file.read_bytes()
                if _sha256_bytes(bak_bytes) != rec["original_sha256"]:
                    raise PatcherError(f"Kopia zapasowa ma błędny SHA-256: {rel}")
                plan_restore.append({"rel": rel, "target": target, "bytes": bak_bytes, "sha": rec["original_sha256"], "skip": True})
                kept_state_records.append(rec)
            elif cur_sha == rec["patched_sha256"] or wymus:
                assert_regular_file(bak_file)
                bak_bytes = bak_file.read_bytes()
                if _sha256_bytes(bak_bytes) != rec["original_sha256"]:
                    raise PatcherError(f"Kopia zapasowa ma błędny SHA-256: {rel}")
                plan_restore.append({"rel": rel, "target": target, "bytes": bak_bytes, "sha": rec["original_sha256"], "skip": False})
                kept_state_records.append(rec)
            else:
                skipped_external += 1
                msg = (
                    f"Pominięto (zaktualizowany/zmieniony przez grę — zostawiam obecną wersję pliku): {rel}"
                )
                print(msg)
                log_lines.append(msg)

        restored = 0
        already_orig = 0
        written_rollback: list[tuple[Path, bytes]] = []
        try:
            for item in plan_restore:
                if item["skip"]:
                    already_orig += 1
                    msg = f"Już oryginał: {item['rel']}"
                    print(msg)
                    log_lines.append(msg)
                    continue
                old_bytes = item["target"].read_bytes() if item["target"].exists() else None
                _write_bytes_atomic(item["target"], item["bytes"], item["sha"])
                if old_bytes is not None:
                    written_rollback.append((item["target"], old_bytes))
                restored += 1
                msg = f"Przywrócono oryginał: {item['rel']}"
                print(msg)
                log_lines.append(msg)
        except Exception:
            for target_path, prev_bytes in reversed(written_rollback):
                try:
                    _write_bytes_atomic(target_path, prev_bytes, _sha256_bytes(prev_bytes))
                except Exception:
                    pass
            raise

        new_state = {
            "format": STAN_FORMAT,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "restored",
            "game_root": str(game_root),
            "build": live_build,
            "files": kept_state_records,
        }
        _save_state(state_path, new_state)
        summary = (
            f"Przywrócono: {restored}, już było oryginalne: {already_orig}, "
            f"pominięto zmienione przez grę: {skipped_external}, usunięte w grze: {skipped_missing}"
        )
        log_lines.append(summary)
        if skipped_external or skipped_missing:
            print(
                "UWAGA: część plików została wcześniej nadpisana/usunięta przez aktualizację gry, "
                "więc została w nowszej wersji z gry; pozostałe pliki łatki przywrócono do oryginału."
            )
        _write_report(backup_dir, log_lines)
        return {
            "ok": True,
            "akcja": "przywroc",
            "przywrocono": restored,
            "juz_oryginal": already_orig,
            "pominieto_zmienione": skipped_external,
            "pominieto_usuniete": skipped_missing,
        }, 0

    # Akcja: instaluj
    if wymagany_build and live_build and live_build != wymagany_build and not pomin_wersje:
        raise PatcherError(
            f"Niezgodny build Steam gry: gra ma {live_build}, łatka oczekuje {wymagany_build}. "
            "(Uruchom z --pomin-wersje, aby mimo to dopasować tłumaczenia po kluczach.)"
        )
    if not target_layers:
        raise PatcherError(f"Nie znaleziono map języka '{jezyk_celu}' w folderze gry: {game_root}")

    if zh_layers:
        active_zh_layers = mapa_tekstow.filtruj_zastapione_diffy(zh_layers)
        zh_map = mapa_tekstow.zloz([path for _, path in active_zh_layers])
        print(f"Wczytano warstwy źródłowe zh_cn z gry: {len(active_zh_layers)} plików ({len(zh_map)} wpisów).")
    else:
        zh_map = {}
        print("UWAGA: brak plików translate_words_map_zh_cn w grze — dopasowanie użyje tylko ID i jednoznacznych tekstów EN.")

    # Przygotowanie oryginałów, staging nowej kopii i przeliczenie nowych plików PRZED zapisem do gry.
    staged_items: list[dict] = []
    backup_stage_files: list[tuple[Path, bytes, str]] = []

    for rel, target in target_layers:
        cur_bytes = target.read_bytes()
        cur_sha = _sha256_bytes(cur_bytes)
        rec = recorded_by_rel.get(rel.casefold())
        bak_rel = f"pliki/{rel}"
        bak_path = backup_dir / bak_rel

        if rec is not None and cur_sha == rec["patched_sha256"]:
            # Gra bez zmian: czytamy wyłącznie z zachowanego czystego oryginału!
            if not bak_path.is_file() or _sha256_file(bak_path) != rec["original_sha256"]:
                raise PatcherError(
                    f"W grze jest już łatka, ale brak poprawnej kopii oryginału dla: {rel}. "
                    "Przywróć pliki przez Steam przed dalszą instalacją."
                )
            orig_bytes = bak_path.read_bytes()
            orig_sha = rec["original_sha256"]
            source_mode = "backup"
        elif rec is not None and cur_sha == rec["original_sha256"]:
            orig_bytes = cur_bytes
            orig_sha = cur_sha
            if not bak_path.is_file() or _sha256_file(bak_path) != orig_sha:
                backup_stage_files.append((bak_path, orig_bytes, orig_sha))
            source_mode = "original"
        else:
            # Pierwsza instalacja ALBO gra zaktualizowała plik po stronie Steam!
            orig_bytes = cur_bytes
            orig_sha = cur_sha
            if bak_path.is_file() and _sha256_file(bak_path) == orig_sha:
                source_mode = "original"
            else:
                backup_stage_files.append((bak_path, orig_bytes, orig_sha))
                source_mode = "updated_game" if rec is not None else "first_install"

        # Dekodowanie oryginału w pamięci z tymczasowego pliku albo bezpośrednio:
        # `mapa_tekstow.wczytaj_warstwe` przyjmuje ścieżkę, więc dla bezpieczeństwa parsujemy z temp lub bak_path.
        teksty = _parse_layer_from_bytes(orig_bytes, rel)
        wanted, match_stats = compute_wanted_for_map(teksty, zh_map, plan)
        if not wanted:
            patched_bytes = orig_bytes
            patched_sha = orig_sha
            changed_count = 0
        else:
            try:
                patched_bytes, apply_stats = patcher.apply_translations(orig_bytes, wanted, level=poziom, text_map={})
                verify_stats = patcher.verify(orig_bytes, patched_bytes, wanted, text_map={})
            except (patcher.PatchError, records.LayoutError) as error:
                raise PatcherError(f"Nie udało się zbudować łatki dla {rel}: {error}") from error
            if verify_stats["changed"] != len(wanted) or apply_stats["ids_not_in_map"]:
                raise PatcherError(
                    f"Weryfikacja łatki dla {rel} nie powiodła się: zmieniono {verify_stats['changed']}, oczekiwano {len(wanted)}"
                )
            patched_sha = _sha256_bytes(patched_bytes)
            changed_count = len(wanted)
        skip_write = (cur_sha == patched_sha)
        staged_items.append({
            "rel": rel,
            "target": target,
            "bak_rel": bak_rel,
            "orig_bytes": orig_bytes,
            "orig_sha": orig_sha,
            "patched_bytes": patched_bytes,
            "patched_sha": patched_sha,
            "cur_bytes": cur_bytes,
            "skip_write": skip_write,
            "source_mode": source_mode,
            "entries": len(teksty),
            "changed": changed_count,
            "match_stats": match_stats,
        })

    # 1. Zapisz/zrotuj kopię oryginałów dopiero wtedy, gdy wszystkie nowe mapy są zbudowane i zweryfikowane.
    backup_rollback: list[tuple[Path, bytes | None]] = []
    archive_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stage_by_bak = {item["bak_rel"]: item for item in staged_items}
    for bak_path, orig_bytes, orig_sha in backup_stage_files:
        rel_for_bak = bak_path.relative_to(backup_dir).as_posix()
        item = stage_by_bak.get(rel_for_bak)
        should_update_bak = (
            not bak_path.exists()
            or (item is not None and item["source_mode"] == "updated_game")
            or (item is not None and not item["skip_write"])
        )
        if should_update_bak:
            prev_bak = bak_path.read_bytes() if bak_path.exists() else None
            if prev_bak is not None and _sha256_bytes(prev_bak) != orig_sha and item is not None:
                arch_path = backup_dir / "kopie_poprzednie" / archive_stamp / item["rel"]
                _write_bytes_atomic(arch_path, prev_bak, _sha256_bytes(prev_bak))
            backup_rollback.append((bak_path, prev_bak))
            _write_bytes_atomic(bak_path, orig_bytes, orig_sha)

    # 2. Transakcyjnie wgraj wszystkie zmienione mapy do gry.
    written_rollback: list[tuple[Path, bytes]] = []
    updated_count = 0
    skipped_count = 0
    try:
        for item in staged_items:
            if item["skip_write"]:
                skipped_count += 1
                msg = (
                    f"Bez zmian (brak dopasowań): {item['rel']}"
                    if item["changed"] == 0
                    else f"Już aktualne: {item['rel']} ({item['changed']} zmienionych wpisów)"
                )
                print(msg)
                log_lines.append(msg)
                continue
            _write_bytes_atomic(item["target"], item["patched_bytes"], item["patched_sha"])
            written_rollback.append((item["target"], item["cur_bytes"]))
            updated_count += 1
            msg = f"Zainstalowano: {item['rel']} (zmieniono {item['changed']} z {item['entries']} wpisów)"
            print(msg)
            log_lines.append(msg)
    except Exception:
        for target_path, prev_bytes in reversed(written_rollback):
            try:
                _write_bytes_atomic(target_path, prev_bytes, _sha256_bytes(prev_bytes))
            except Exception:
                pass
        for bak_path, prev_bak in reversed(backup_rollback):
            try:
                if prev_bak is None:
                    if bak_path.exists():
                        bak_path.unlink()
                else:
                    _write_bytes_atomic(bak_path, prev_bak, _sha256_bytes(prev_bak))
            except Exception:
                pass
        raise

    # 3. Zapisz aktualny stan instalacji.
    state_files = [
        {
            "relative_path": item["rel"],
            "backup_relative": item["bak_rel"],
            "original_sha256": item["orig_sha"],
            "patched_sha256": item["patched_sha"],
            "original_bytes": len(item["orig_bytes"]),
            "patched_bytes": len(item["patched_bytes"]),
        }
        for item in staged_items
    ]
    new_state = {
        "format": STAN_FORMAT,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "installed",
        "game_root": str(game_root),
        "build": live_build,
        "files": state_files,
    }
    _save_state(state_path, new_state)
    _write_report(backup_dir, log_lines)

    return {
        "ok": True,
        "akcja": "instaluj",
        "build": live_build,
        "zaktualizowano": updated_count,
        "juz_aktualne": skipped_count,
        "kopia": str(backup_dir),
        "pliki": [
            {
                "sciezka_w_grze": item["rel"],
                "wpisow": item["entries"],
                "przetlumaczonych": item["changed"],
                "tryb_zrodla": item["source_mode"],
                "sha256_przed": item["orig_sha"],
                "sha256_po": item["patched_sha"],
            }
            for item in staged_items
        ],
    }, 0


def _parse_layer_from_bytes(data: bytes, name: str) -> dict[int, str]:
    try:
        chunks = patcher.read_container(data)
        texts: dict[int, str] = {}
        for chunk in chunks:
            if patcher.is_metadata_chunk(chunk, len(chunks)):
                continue
            kind, payload = patcher.split_chunk(chunk)
            table = records.parse_table(patcher.decompress(kind, payload))
            for entry in table["entries"]:
                if not entry["id"] or not entry["length"] or entry["placeholder"]:
                    continue
                texts[entry["id"]] = entry["text"].decode("utf-8", "replace")
        return texts
    except (patcher.PatchError, records.LayoutError) as error:
        raise PatcherError(f"{name}: uszkodzona mapa tekstów gry: {error}") from error


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--akcja", choices=("instaluj", "przywroc", "stan"), default="instaluj")
    parser.add_argument("--plan", default="plan_latki.json", help="ścieżka planu łatki wwm-plan-latki-v1")
    parser.add_argument("game_pos", nargs="?", default="", help="opcjonalny folder gry (np. z przeciągnięcia na .bat)")
    parser.add_argument("--game", default="", help="główny folder gry")
    parser.add_argument("--steam-root", default="", help="opcjonalny folder Steam")
    parser.add_argument("--backup-dir", default="", help="katalog kopii zapasowej (poza folderem gry)")
    parser.add_argument("--poziom", type=int, default=9, help="poziom kompresji zstd (domyślnie: 9)")
    parser.add_argument("--wymus", action="store_true", help="nadpisz/przywróć mimo zewnętrznej zmiany w grze")
    parser.add_argument("--pomin-wersje", action="store_true", help="ignoruj różnicę buildid Steam")
    parser.add_argument("--non-interactive", action="store_true", help="nie otwieraj okien ani pytań")
    parser.add_argument("--json", action="store_true", help="wypisz podsumowanie także jako JSON")
    args = parser.parse_args(argv)

    game_arg = args.game or args.game_pos
    try:
        report, code = run_patcher(
            akcja=args.akcja,
            plan_path=Path(args.plan),
            game_root_arg=game_arg,
            steam_root_arg=args.steam_root,
            backup_dir_arg=args.backup_dir,
            poziom=args.poziom,
            wymus=args.wymus,
            pomin_wersje=args.pomin_wersje,
            non_interactive=args.non_interactive,
        )
    except (PatcherError, mapa_tekstow.MapaError, OSError, ValueError) as error:
        if args.json:
            print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False, indent=1))
        else:
            print(f"BŁĄD: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
