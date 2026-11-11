#!/usr/bin/env python3
"""Inspect known locale filenames in two possible Steam game subdirectories.

This is metadata-only reconnaissance, not an auditor, extractor, or patcher.
Names and layout are public community leads, not an authenticated game build.
The tool does not open candidate-file contents, hash them, or intentionally
write to the selected game tree. It makes no direct network requests. The
selected root path and operating system exception messages are omitted from
its output. Checks are best effort and do not prevent filesystem races.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

if __package__:
    from . import inspect_localization as inventory
else:
    import inspect_localization as inventory


LAYERS = (
    ("package", ("Package", "HD", "oversea", "locale")),
    ("patch", ("LocalData", "Patch", "HD", "oversea", "locale")),
)


def _is_directory(metadata: os.stat_result) -> bool:
    return stat.S_ISDIR(metadata.st_mode) and not inventory._is_link_or_reparse(metadata)


def _unchanged_directory(path: Path, original: os.stat_result) -> bool:
    try:
        now = inventory._lstat(path)
        return _is_directory(now) and (original.st_dev, original.st_ino) == (now.st_dev, now.st_ino)
    except OSError:
        return False


def _checked_root(root: Path) -> tuple[Path, list[tuple[Path, os.stat_result]]]:
    """Check the selected directory and its parents without disclosing paths."""
    try:
        root = Path(os.path.abspath(os.fspath(root)))
        observed = []
        for path in reversed((root, *root.parents)):
            metadata = inventory._lstat(path)
            if not _is_directory(metadata):
                raise inventory.InventoryError("root or parent is not a regular non-link directory")
            observed.append((path, metadata))
        return root, observed
    except (OSError, ValueError) as exc:
        raise inventory.InventoryError("root directory is unavailable") from exc


def _layer(root: Path, role: str, components: tuple[str, ...]) -> dict[str, Any]:
    """Inspect one candidate location and discard observations if it changes."""
    relative = "/".join(components)
    path = root
    checked: list[tuple[Path, os.stat_result]] = []
    directory_state = "available"
    for part in components:
        path = path / part
        try:
            metadata = inventory._lstat(path)
        except FileNotFoundError:
            directory_state = "missing"
            break
        except OSError:
            directory_state = "inaccessible"
            break
        if inventory._is_link_or_reparse(metadata):
            directory_state = "link_skipped"
            break
        if not stat.S_ISDIR(metadata.st_mode):
            directory_state = "not_directory"
            break
        checked.append((path, metadata))

    result: str | None = None
    candidates: list[dict[str, Any]] = []
    if directory_state == "available":
        try:
            report = inventory.inspect_directory(path)
            result = report["result"]
            candidates = report["candidates"]
            if report["directory_state"] != "matched_start_end":
                directory_state = "changed_or_inaccessible"
                result, candidates = None, []
        except inventory.InventoryError:
            directory_state = "changed_or_inaccessible"
    if not all(_unchanged_directory(path, info) for path, info in checked):
        directory_state = "changed_or_inaccessible"
        result, candidates = None, []
    return {
        "role": role,
        "relative_location": relative,
        "directory_state": directory_state,
        "candidate_result": result,
        "candidates": candidates,
    }


def inspect_layout(root: Path) -> dict[str, Any]:
    """Stat fixed candidates in two locations, without reading file contents.

    Missing/inaccessible locations and links are reported separately; a missing
    directory does not mean the individual files are proven absent. Checks are
    best effort and cannot establish a consistent atomic filesystem snapshot.
    """
    root, ancestors = _checked_root(root)
    layers = [_layer(root, role, components) for role, components in LAYERS]
    roots_stable = all(_unchanged_directory(path, info) for path, info in ancestors)
    if not roots_stable:
        layers = [
            {
                "role": role,
                "relative_location": "/".join(components),
                "directory_state": "changed_or_inaccessible",
                "candidate_result": None,
                "candidates": [],
            }
            for role, components in LAYERS
        ]
        result = "incomplete"
    elif any(
        layer["directory_state"] != "available" or layer["candidate_result"] == "incomplete"
        for layer in layers
    ):
        result = "incomplete"
    elif any(layer["candidate_result"] == "candidates_found" for layer in layers):
        result = "candidates_found"
    else:
        result = "no_candidates"
    return {
        "schema": 1,
        "scope": "community_named_candidates_in_two_locations",
        "result": result,
        "root_state": "matched_start_end" if roots_stable else "changed_or_inaccessible",
        "candidate_contents_read": False,
        "hashes_computed": False,
        "game_tree_writes_attempted": False,
        "input_path_included": False,
        "build_or_game_identity_verified": False,
        "atomic_snapshot_verified": False,
        "layers": layers,
        "limitations": [
            "Locations and names are unverified community leads, not proof of the game build or format.",
            "A missing location does not establish the state of its candidate files.",
            "Best-effort link checks cannot prevent races or prove an atomic filesystem snapshot.",
            "The tool makes no direct network calls, but the filesystem can be remote.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = inventory.RedactingArgumentParser(
        prog="inspect_steam_layout",
        description=(
            "Metadata only for two possible Steam locale directories. "
            "No game-file contents or hashes, intentional game-tree writes, or direct network requests."
        ),
    )
    parser.add_argument("--root", required=True, type=Path, help="game root containing Package")
    args = parser.parse_args(argv)
    try:
        report = inspect_layout(args.root)
    except inventory.InventoryError:
        print("ERROR: root or parent unavailable, not a directory, or a link/reparse point.", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if report["result"] == "incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
