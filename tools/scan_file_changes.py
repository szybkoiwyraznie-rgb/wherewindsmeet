#!/usr/bin/env python3
"""Read-only, generic SHA-256 file inventory; not a Where Winds Meet parser.

Only explicit directories are read. A private result can be retained outside
that directory and compared to a later scan. No file is created or changed by
this program. The scan is not an atomic filesystem snapshot, and it cannot
establish game/build identity, a publisher origin, or write authorization.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import sys
from typing import Any

if __package__:
    from . import translation_bundle as bundles
else:
    import translation_bundle as bundles


CHUNK_BYTES = 1024 * 1024
MAX_NODES = 250_000
MAX_DOCUMENT_BYTES = 64 * 1024 * 1024
MAX_RELATIVE_PATH_CHARS = 32_767
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
MANIFEST_KIND = "generic_read_only_sha256_manifest_v1"
PRIVATE_RESULT_KIND = "generic_read_only_sha256_result_v1"
REPORT_KIND = "generic_read_only_sha256_report_v1"
ISSUE_REASONS = frozenset({
    "link_or_reparse_skipped", "unsupported_entry", "entry_unavailable",
    "file_unavailable", "file_changed", "directory_unavailable",
    "directory_changed", "node_limit_exceeded", "unrepresentable_path",
})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise bundles.BundleError(message)


def _is_link_or_reparse(info: os.stat_result) -> bool:
    return bool(stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & REPARSE_POINT)


def _same_observation(first: os.stat_result, second: os.stat_result) -> bool:
    """Compare available identity and change metadata, deliberately not atime.

    Some Windows APIs return zero for device or inode; do not mistake zero for
    an identity guarantee. This is only a best-effort change detector, not a
    filesystem lock or proof that bytes were unchanged throughout the scan.
    """
    if _is_link_or_reparse(first) or _is_link_or_reparse(second):
        return False
    for field in ("st_dev", "st_ino"):
        old, new = getattr(first, field, 0), getattr(second, field, 0)
        if old and new and old != new:
            return False
    return (
        stat.S_IFMT(first.st_mode) == stat.S_IFMT(second.st_mode)
        and first.st_size == second.st_size
        and first.st_mtime_ns == second.st_mtime_ns
        and first.st_ctime_ns == second.st_ctime_ns
    )


def _root_directory(root: Path) -> tuple[Path, os.stat_result]:
    """Reject links/reparse points in the chosen path, including its parents."""
    try:
        absolute = Path(os.path.abspath(os.fspath(root)))
        root_info = os.lstat(absolute)
        for component in (absolute, *absolute.parents):
            info = root_info if component == absolute else os.lstat(component)
            if _is_link_or_reparse(info) or not stat.S_ISDIR(info.st_mode):
                raise bundles.BundleError("scan root must be a directory without links or reparse points")
    except (OSError, ValueError) as exc:
        if isinstance(exc, bundles.BundleError):
            raise
        raise bundles.BundleError("cannot inspect scan root") from exc
    return absolute, root_info


def _scope_fingerprint(root: Path) -> str:
    # A deterministic pseudonymous location token, not authentication. The
    # private manifest may still identify the installation through its contents.
    identity = b"generic-inventory-scope-v1\0" + os.name.encode("ascii") + b"\0"
    identity += os.fsencode(os.path.normcase(os.fspath(root)))
    return hashlib.sha256(identity).hexdigest()


def _relative_path_valid(path: Any, *, root_allowed: bool = False) -> bool:
    if (
        type(path) is not str or len(path) > MAX_RELATIVE_PATH_CHARS
        or "\0" in path or "\\" in path
    ):
        return False
    if path == "":
        return root_allowed
    if PurePosixPath(path).is_absolute() or PureWindowsPath(path).drive:
        return False
    return all(part not in ("", ".", "..") for part in path.split("/"))


def _hash_regular_file(path: Path, initial: os.stat_result) -> tuple[str | None, os.stat_result | None, str | None]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    # Avoid hanging if a regular file is swapped for a FIFO just before open.
    flags |= getattr(os, "O_NONBLOCK", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not _same_observation(initial, opened):
            return None, None, "file_changed"
        digest = hashlib.sha256()
        total = 0
        while True:
            block = os.read(descriptor, CHUNK_BYTES)
            if not block:
                break
            digest.update(block)
            total += len(block)
        finished = os.fstat(descriptor)
        named = os.lstat(path)
        if (
            total != finished.st_size
            or not _same_observation(opened, finished)
            or not _same_observation(finished, named)
        ):
            return None, None, "file_changed"
        return digest.hexdigest(), finished, None
    except OSError:
        return None, None, "file_unavailable"
    finally:
        if descriptor is not None:
            os.close(descriptor)


def scan_tree(root: Path) -> dict[str, Any]:
    """Inventory a directory, without writing; incomplete scans cannot be compared.

    Links, reparse points, non-regular files, unreadable entries, observed
    changes and the node ceiling are reported as issues, not silently ignored.
    Checks before/after reads are best effort and do not give an atomic view.
    Do not use this prototype on hostile or concurrently changing directories.
    """
    root, root_info = _root_directory(root)
    pending: list[tuple[Path, str, os.stat_result]] = [(root, "", root_info)]
    directories: list[tuple[Path, str, os.stat_result]] = []
    checked_files: dict[str, tuple[Path, os.stat_result, dict[str, Any]]] = {}
    issues: set[tuple[str, str]] = set()
    observed_nodes = 0
    ceiling_hit = False

    while pending and not ceiling_hit:
        directory, relative_directory, initial_directory = pending.pop()
        try:
            current = os.lstat(directory)
        except OSError:
            issues.add((relative_directory, "directory_unavailable"))
            continue
        if not stat.S_ISDIR(current.st_mode) or not _same_observation(initial_directory, current):
            issues.add((relative_directory, "directory_changed"))
            continue
        directories.append((directory, relative_directory, current))
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if observed_nodes >= MAX_NODES:
                        issues.add((relative_directory, "node_limit_exceeded"))
                        ceiling_hit = True
                        break
                    observed_nodes += 1
                    relative = f"{relative_directory}/{entry.name}" if relative_directory else entry.name
                    if not _relative_path_valid(relative):
                        # Do not put an unrepresentable or unsafe name in output.
                        issues.add((relative_directory, "unrepresentable_path"))
                        continue
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except OSError:
                        issues.add((relative, "entry_unavailable"))
                        continue
                    if _is_link_or_reparse(info):
                        issues.add((relative, "link_or_reparse_skipped"))
                    elif stat.S_ISDIR(info.st_mode):
                        pending.append((Path(entry.path), relative, info))
                    elif stat.S_ISREG(info.st_mode):
                        digest, checked, problem = _hash_regular_file(Path(entry.path), info)
                        if problem is not None:
                            issues.add((relative, problem))
                        else:
                            assert digest is not None and checked is not None
                            record = {"path": relative, "size": checked.st_size, "sha256": digest}
                            checked_files[relative] = (Path(entry.path), checked, record)
                    else:
                        issues.add((relative, "unsupported_entry"))
        except OSError:
            issues.add((relative_directory, "directory_unavailable"))

    # Recheck all observed paths, including files hashed early in a long scan.
    # These metadata checks still cannot prevent changes after the last check.
    for path, relative, initial in directories:
        try:
            current = os.lstat(path)
            if not stat.S_ISDIR(current.st_mode) or not _same_observation(initial, current):
                issues.add((relative, "directory_changed"))
        except OSError:
            issues.add((relative, "directory_unavailable"))
    for relative, (path, initial, _) in list(checked_files.items()):
        try:
            current = os.lstat(path)
            stable = stat.S_ISREG(current.st_mode) and _same_observation(initial, current)
        except OSError:
            stable = False
        if not stable:
            del checked_files[relative]
            issues.add((relative, "file_changed"))

    return {
        "schema": 1,
        "kind": MANIFEST_KIND,
        "scope_fingerprint": _scope_fingerprint(root),
        "scan_status": "incomplete" if issues else "complete",
        "atomic_snapshot_verified": False,
        "file_origin_verified": False,
        "files": [checked_files[key][2] for key in sorted(checked_files)],
        "issues": [{"path": path, "reason": reason} for path, reason in sorted(issues)],
    }


def _validate_manifest(document: Any) -> None:
    keys = {
        "schema", "kind", "scope_fingerprint", "scan_status", "atomic_snapshot_verified",
        "file_origin_verified", "files", "issues",
    }
    _require(type(document) is dict and set(document) == keys, "inventory: invalid fields")
    _require(type(document["schema"]) is int and document["schema"] == 1, "inventory: unsupported schema")
    _require(document["kind"] == MANIFEST_KIND, "inventory: invalid kind")
    fingerprint = document["scope_fingerprint"]
    _require(type(fingerprint) is str and bundles.HEX_SHA256.fullmatch(fingerprint) is not None,
             "inventory: invalid scope fingerprint")
    _require(document["scan_status"] in ("complete", "incomplete"), "inventory: invalid status")
    _require(document["atomic_snapshot_verified"] is False and document["file_origin_verified"] is False,
             "inventory: unsupported verification claim")
    files, issues = document["files"], document["issues"]
    _require(type(files) is list and len(files) <= MAX_NODES, "inventory: invalid files")
    _require(type(issues) is list and len(issues) <= 2 * MAX_NODES + 1, "inventory: invalid issues")
    _require((document["scan_status"] == "complete") == (not issues), "inventory: inconsistent status")
    paths: set[str] = set()
    for item in files:
        _require(type(item) is dict and set(item) == {"path", "size", "sha256"}, "inventory: invalid file")
        path = item["path"]
        _require(_relative_path_valid(path) and path not in paths, "inventory: invalid or duplicate path")
        paths.add(path)
        _require(type(item["size"]) is int and item["size"] >= 0, "inventory: invalid size")
        digest = item["sha256"]
        _require(type(digest) is str and bundles.HEX_SHA256.fullmatch(digest) is not None,
                 "inventory: invalid hash")
    seen_issues: set[tuple[str, str]] = set()
    for item in issues:
        _require(type(item) is dict and set(item) == {"path", "reason"}, "inventory: invalid issue")
        _require(_relative_path_valid(item["path"], root_allowed=True), "inventory: invalid issue path")
        _require(type(item["reason"]) is str and item["reason"] in ISSUE_REASONS, "inventory: invalid issue reason")
        key = (item["path"], item["reason"])
        _require(key not in seen_issues, "inventory: duplicate issue")
        seen_issues.add(key)


def compare_manifests(current: Any, previous: Any = None) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Compare exact paths/hashes only; previous data is never authenticated."""
    _validate_manifest(current)
    if previous is None:
        return {"status": "no_baseline", "counts": None}, []
    _validate_manifest(previous)
    if current["scope_fingerprint"] != previous["scope_fingerprint"]:
        return {"status": "blocked_scope_mismatch", "counts": None}, []
    if current["scan_status"] != "complete" or previous["scan_status"] != "complete":
        return {"status": "blocked_incomplete_scan", "counts": None}, []
    before = {item["path"]: item for item in previous["files"]}
    after = {item["path"]: item for item in current["files"]}
    counts = {"unchanged": 0, "changed": 0, "added": 0, "removed": 0}
    changes: list[dict[str, str]] = []
    for path in sorted(before.keys() | after.keys()):
        if path not in before:
            state = "added"
        elif path not in after:
            state = "removed"
        elif before[path]["size"] == after[path]["size"] and before[path]["sha256"] == after[path]["sha256"]:
            state = "unchanged"
        else:
            state = "changed"
        counts[state] += 1
        if state != "unchanged":
            changes.append({"path": path, "change": state})
    return {"status": "compared", "counts": counts}, changes


def make_report(manifest: dict[str, Any], previous: Any = None) -> tuple[dict[str, Any], list[dict[str, str]]]:
    comparison, changes = compare_manifests(manifest, previous)
    issue_counts = Counter(item["reason"] for item in manifest["issues"])
    return {
        "schema": 1,
        "kind": REPORT_KIND,
        "scan_status": manifest["scan_status"],
        "files_hashed": len(manifest["files"]),
        "issue_counts": dict(sorted(issue_counts.items())),
        "comparison": comparison,
        "atomic_snapshot_verified": False,
        "file_origin_verified": False,
        "game_or_launcher_state_verified": False,
        "baseline_authenticated": False,
        "writes_performed": False,
    }, changes


def _previous_manifest(document: Any) -> Any:
    _require(type(document) is dict and set(document) == {"schema", "kind", "report", "manifest", "changes"},
             "previous result: invalid fields")
    _require(type(document["schema"]) is int and document["schema"] == 1,
             "previous result: unsupported schema")
    _require(document["kind"] == PRIVATE_RESULT_KIND, "previous result: invalid kind")
    _require(type(document["report"]) is dict and type(document["changes"]) is list,
             "previous result: invalid data")
    _validate_manifest(document["manifest"])
    return document["manifest"]


def _previous_outside_root(root: Path, previous: Path) -> None:
    try:
        root_real = os.path.normcase(os.path.realpath(os.path.abspath(root)))
        previous_real = os.path.normcase(os.path.realpath(os.path.abspath(previous)))
        try:
            inside = os.path.commonpath((root_real, previous_real)) == root_real
        except ValueError:  # Different Windows drives.
            inside = False
    except (OSError, ValueError) as exc:
        raise bundles.BundleError("cannot inspect baseline location") from exc
    _require(not inside, "baseline must be outside the scanned directory")


def main(argv: list[str] | None = None) -> int:
    parser = bundles.RedactingArgumentParser(
        prog="scan_file_changes",
        description=(
            "Read-only generic SHA-256 inventory, not a game parser. "
            "Private mode exposes relative paths and hashes; do not publish it."
        ),
    )
    parser.add_argument("--root", type=Path, required=True, help="directory to scan")
    parser.add_argument("--previous", type=Path, help="previous private result, outside the scan root")
    parser.add_argument("--mode", choices=("report", "private"), default="report")
    args = parser.parse_args(argv)
    try:
        previous = None
        if args.previous is not None:
            _previous_outside_root(args.root, args.previous)
            previous = _previous_manifest(bundles.load_json(args.previous, max_bytes=MAX_DOCUMENT_BYTES))
        manifest = scan_tree(args.root)
        report, changes = make_report(manifest, previous)
        result = report if args.mode == "report" else {
            "schema": 1,
            "kind": PRIVATE_RESULT_KIND,
            "report": report,
            "manifest": manifest,
            "changes": changes,
        }
        output = json.dumps(result, ensure_ascii=True, indent=2)
        # Account for text-mode CRLF expansion on Windows, and the final newline.
        encoded_size = len(output.encode("ascii")) + output.count("\n") + 2
        _require(encoded_size <= MAX_DOCUMENT_BYTES, "output is too large for this prototype")
    except bundles.BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(output)
    if report["scan_status"] != "complete" or report["comparison"]["status"].startswith("blocked_"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
