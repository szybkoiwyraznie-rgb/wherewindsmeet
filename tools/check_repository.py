#!/usr/bin/env python3
"""Check the Git index for common private artifacts and oversized files.

This is a guardrail, not a content or secrets scanner. It inspects staged blob
sizes instead of working-tree sizes so local edits cannot hide a staged file.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = 10 * 1024 * 1024

# These deliberately mirror the protective parts of .gitignore. A reviewer must
# still inspect every staged file: its contents may be private under any name.
BLOCKED_DIRECTORIES = frozenset(
    {
        "local", "google_drive", "build", "dist", "out", "artifacts", "downloads",
        ".venv", "venv", ".direnv", "__pycache__", ".pytest_cache", ".mypy_cache",
        ".ruff_cache", ".cache", "coverage", "node_modules",
    }
)
BLOCKED_SUFFIXES = frozenset(
    {
        ".pem", ".key", ".p12", ".pfx", ".pak", ".ucas", ".utoc", ".pck",
        ".bundle", ".assetbundle", ".assets", ".ba2", ".bsa", ".bin", ".dat",
        ".exe", ".dll", ".so", ".dylib", ".iso", ".img", ".sav", ".save",
        ".dmp", ".bak", ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz",
        ".bz2", ".xz", ".zst", ".log", ".pyc", ".pyo", ".pyd",
    }
)
BLOCKED_FILENAMES = frozenset({".coverage", ".ds_store", "thumbs.db"})


@dataclass(frozen=True)
class IndexEntry:
    path: str
    mode: str
    oid: str
    stage: int


@dataclass(frozen=True)
class ScanResult:
    entries: int
    violations: tuple[str, ...]


def _git(repo: Path, *args: str, input_data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repo, input=input_data, capture_output=True, check=False
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def read_index(repo: Path) -> list[IndexEntry]:
    raw = _git(repo, "ls-files", "--stage", "-z")
    entries = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, raw_path = item.split(b"\t", 1)
        mode, oid, stage = header.split(b" ")
        entries.append(
            IndexEntry(
                path=os.fsdecode(raw_path),
                mode=mode.decode("ascii"),
                oid=oid.decode("ascii"),
                stage=int(stage),
            )
        )
    return entries


def blob_sizes(repo: Path, entries: list[IndexEntry]) -> dict[str, int]:
    # A submodule is a gitlink, not a blob, and its object may not be present in
    # this repository. It is reported as a policy violation separately below.
    oids = sorted({entry.oid for entry in entries if entry.mode != "160000"})
    if not oids:
        return {}
    raw = _git(
        repo,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        input_data=("\n".join(oids) + "\n").encode("ascii"),
    )
    lines = raw.decode("ascii").splitlines()
    if len(lines) != len(oids):
        raise RuntimeError("git cat-file returned an incomplete index size report")
    sizes = {}
    for requested, line in zip(oids, lines):
        parts = line.split()
        if len(parts) != 3 or parts[0] != requested or parts[1] != "blob":
            raise RuntimeError(f"index object is missing or not a blob: {line}")
        sizes[requested] = int(parts[2])
    return sizes


def entry_violations(
    entry: IndexEntry, size: int | None, max_file_bytes: int = MAX_FILE_BYTES
) -> list[str]:
    # ascii() also keeps output safe for unusual filenames and Windows consoles.
    shown = ascii(entry.path)
    parts = PurePosixPath(entry.path).parts
    name = parts[-1].casefold()
    violations = []
    blocked_dirs = [part for part in parts[:-1] if part.casefold() in BLOCKED_DIRECTORIES]
    if blocked_dirs:
        violations.append(f"{shown}: protected directory {ascii(blocked_dirs[0])}")
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        violations.append(f"{shown}: environment file may contain secrets")
    elif name in BLOCKED_FILENAMES:
        violations.append(f"{shown}: local-only filename")
    suffix = PurePosixPath(name).suffix
    if suffix in BLOCKED_SUFFIXES:
        violations.append(f"{shown}: protected extension {suffix}")
    if entry.mode == "160000":
        violations.append(f"{shown}: submodule requires an explicit policy review")
    if entry.stage != 0:
        violations.append(f"{shown}: unresolved Git index conflict (stage {entry.stage})")
    if size is not None and size > max_file_bytes:
        violations.append(f"{shown}: staged blob is {size} B, limit is {max_file_bytes} B")
    return violations


def scan_index(repo: Path, max_file_bytes: int = MAX_FILE_BYTES) -> ScanResult:
    entries = read_index(repo)
    sizes = blob_sizes(repo, entries)
    violations = []
    for entry in entries:
        violations.extend(entry_violations(entry, sizes.get(entry.oid), max_file_bytes))
    return ScanResult(entries=len(entries), violations=tuple(violations))


def main() -> int:
    try:
        result = scan_index(ROOT)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Repository check failed to run: {exc}", file=sys.stderr)
        return 2
    if result.violations:
        print("Repository check failed (inspect the Git index):", file=sys.stderr)
        for violation in result.violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1
    print(f"Repository check OK: {result.entries} index entries, limit {MAX_FILE_BYTES} B/file.")
    print("This is not a content or secrets scan; review the staged diff manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
