#!/usr/bin/env python3
"""Model restore decisions from invented hashes, without accessing game files.

This is not an installer or an uninstaller. Hashes, scope and build labels are
caller-supplied; the model does not authenticate or measure them, inspect a
running game, lock files, create backups, or authorize any actual write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from . import translation_bundle as bundles
else:
    import translation_bundle as bundles


ROOT_KEYS = frozenset({"schema", "scope_id", "build_id", "files"})
RECORDED_KEYS = frozenset({"id", "original_sha256", "patched_sha256"})
OBSERVED_KEYS = frozenset({"id", "current_sha256", "backup_sha256"})
MAX_FILES = 512


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise bundles.BundleError(message)


def _object(value: Any, keys: frozenset[str], where: str) -> None:
    _require(type(value) is dict and set(value) == keys, f"{where}: invalid fields")


def _identifier(value: Any, where: str) -> str:
    _require(
        type(value) is str and bundles.IDENTIFIER.fullmatch(value) is not None,
        f"{where}: invalid identifier",
    )
    return value


def _hash(value: Any, where: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    _require(
        type(value) is str and bundles.HEX_SHA256.fullmatch(value) is not None,
        f"{where}: invalid hash",
    )
    return value


def _input(document: Any, *, recorded: bool) -> tuple[str, str, list[dict[str, Any]]]:
    where = "recorded" if recorded else "observed"
    _object(document, ROOT_KEYS, where)
    _require(type(document["schema"]) is int and document["schema"] == 1, f"{where}: invalid schema")
    scope = _identifier(document["scope_id"], where)
    build = _identifier(document["build_id"], where)
    files = document["files"]
    _require(type(files) is list and 0 < len(files) <= MAX_FILES, f"{where}: invalid files")
    seen: set[str] = set()
    for index, item in enumerate(files):
        item_where = f"{where} file {index + 1}"
        _object(item, RECORDED_KEYS if recorded else OBSERVED_KEYS, item_where)
        identifier = _identifier(item["id"], item_where)
        _require(identifier not in seen, f"{item_where}: duplicate identifier")
        seen.add(identifier)
        if recorded:
            _hash(item["original_sha256"], item_where)
            _hash(item["patched_sha256"], item_where)
        else:
            _hash(item["current_sha256"], item_where, nullable=True)
            _hash(item["backup_sha256"], item_where, nullable=True)
    return scope, build, files


def model_restore(recorded: Any, observed: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a conservative hash-only model and optional per-record details."""
    old_scope, old_build, recorded_files = _input(recorded, recorded=True)
    current_scope, current_build, observed_files = _input(observed, recorded=False)
    observations = {item["id"]: item for item in observed_files}
    expected_ids = {item["id"] for item in recorded_files}
    _require(set(observations) == expected_ids, "observed: file set mismatch")

    counts = {
        "files": len(recorded_files),
        "current_matches_recorded_original": 0,
        "current_matches_recorded_patch": 0,
        "current_unrecognized": 0,
        "current_unavailable": 0,
        "backup_matches_recorded_original": 0,
        "backup_mismatch": 0,
        "backup_unavailable": 0,
    }
    details = []
    for entry in recorded_files:
        observation = observations[entry["id"]]
        current = observation["current_sha256"]
        backup = observation["backup_sha256"]
        if current is None:
            current_state = "current_unavailable"
        elif current == entry["original_sha256"]:
            current_state = "current_matches_recorded_original"
        elif current == entry["patched_sha256"]:
            current_state = "current_matches_recorded_patch"
        else:
            current_state = "current_unrecognized"
        if backup is None:
            backup_state = "backup_unavailable"
        elif backup == entry["original_sha256"]:
            backup_state = "backup_matches_recorded_original"
        else:
            backup_state = "backup_mismatch"
        counts[current_state] += 1
        counts[backup_state] += 1
        details.append({"id": entry["id"], "current_state": current_state, "backup_state": backup_state})

    scope_matches = old_scope == current_scope
    build_matches = old_build == current_build
    conflicts = sum(counts[key] for key in (
        "current_unrecognized", "current_unavailable", "backup_mismatch", "backup_unavailable"
    ))
    if not scope_matches:
        decision = "blocked_scope_mismatch"
    elif not build_matches:
        decision = "blocked_build_mismatch"
    elif conflicts:
        decision = "blocked_conflicts"
    elif counts["current_matches_recorded_patch"]:
        decision = "needs_further_preflight"
    else:
        decision = "no_patched_bytes_observed"

    common = {
        "schema": 1,
        "scope": "synthetic_restore_model_v1",
        "decision": decision,
        "scope_labels_match": scope_matches,
        "build_labels_match": build_matches,
        "labels_and_hashes_verified": False,
        "filesystem_or_process_checks_performed": False,
        "writes_performed": False,
        "write_authorized": False,
    }
    return {**common, "counts": counts}, {**common, "items": details}


def main(argv: list[str] | None = None) -> int:
    parser = bundles.RedactingArgumentParser(
        prog="model_restore_preflight",
        description=(
            "Synthetic hash-only restore model, not an uninstaller. "
            "It does not check actual files, authenticate inputs or authorize writes."
        ),
    )
    parser.add_argument("--recorded", type=Path, required=True)
    parser.add_argument("--observed", type=Path, required=True)
    parser.add_argument("--details", action="store_true", help="also show supplied logical IDs")
    args = parser.parse_args(argv)
    try:
        recorded = bundles.load_json(args.recorded, max_bytes=bundles.MAX_SOURCE_BYTES)
        observed = bundles.load_json(args.observed, max_bytes=bundles.MAX_SOURCE_BYTES)
        report, details = model_restore(recorded, observed)
        output = json.dumps(details if args.details else report, ensure_ascii=True, indent=2)
    except bundles.BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
