#!/usr/bin/env python3
"""Report metadata for a fixed set of candidate locale files, without opening them.

Community-documented filenames are only leads, not proof of format or version.
The supplied directory and OS error details are deliberately omitted from output.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys


CANDIDATES = (
    "translate_words_map_en",
    "translate_words_map_en_diff",
    "translate_words_map_en__small",
    "translate_words_map_en__small_diff",
    "translate_words_map_en_mobile",
    "translate_words_map_zh_cn",
    "translate_words_map_zh_cn_diff",
    "translate_words_map_zh_cn__small",
    "translate_words_map_zh_cn__small_diff",
)
FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


class InventoryError(Exception):
    """The selected directory cannot safely be inspected."""


def _lstat(path: Path):
    return os.lstat(path)


def _is_link_or_reparse(metadata) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
    )


def inspect_directory(directory: Path) -> dict:
    """Stat known names only; never read file contents or reveal the input path."""
    directory = Path(directory)
    try:
        root = _lstat(directory)
    except OSError as exc:
        raise InventoryError("directory is unavailable") from exc
    if _is_link_or_reparse(root) or not stat.S_ISDIR(root.st_mode):
        raise InventoryError("directory is not a regular, non-link directory")

    entries = []
    for name in CANDIDATES:
        try:
            metadata = _lstat(directory / name)
        except FileNotFoundError:
            entries.append({"name": name, "state": "absent"})
            continue
        except OSError:
            # Do not disclose the OS error: it may include the owner's path.
            entries.append({"name": name, "state": "inaccessible"})
            continue
        if _is_link_or_reparse(metadata):
            entries.append({"name": name, "state": "link_skipped"})
        elif not stat.S_ISREG(metadata.st_mode):
            entries.append({"name": name, "state": "not_regular"})
        else:
            entries.append({"name": name, "state": "present", "size_bytes": metadata.st_size})

    # A removed/replaced directory can otherwise make ENOENT look like nine
    # absent files. Compare identities again, fail closed and discard candidate
    # observations if the root no longer matches. This is not an atomic scan.
    try:
        final_root = _lstat(directory)
        root_changed = (
            _is_link_or_reparse(final_root)
            or not stat.S_ISDIR(final_root.st_mode)
            or (root.st_dev, root.st_ino) != (final_root.st_dev, final_root.st_ino)
        )
    except OSError:
        root_changed = True

    if root_changed:
        entries = [{"name": name, "state": "unknown"} for name in CANDIDATES]
        result = "incomplete"
    else:
        states = {entry["state"] for entry in entries}
        if states - {"present", "absent"}:
            result = "incomplete"
        elif "present" in states:
            result = "candidates_found"
        else:
            result = "no_candidates"
    return {
        "schema": 1,
        "result": result,
        "scope": "known_filenames_in_one_directory",
        "directory_state": "changed_or_inaccessible" if root_changed else "matched_start_end",
        "contents_read": False,
        "hashes_computed": False,
        "input_path_included": False,
        "candidates": entries,
        "limitations": [
            "Names are community-reported leads, not proof of game version or format.",
            "This report cannot establish provenance, completeness or permission to modify the game.",
            "It is not an atomic snapshot; links in parent directories may be followed by the OS.",
        ],
    }


class RedactingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's usual error can echo an unknown argument, including paths.
        self.print_usage(sys.stderr)
        self.exit(2, "ERROR: invalid arguments; use --help for syntax.\n")


def main(argv: list[str] | None = None) -> int:
    parser = RedactingArgumentParser(
        prog="inspect_localization",
        description=(
            "Inspect metadata for known locale filenames only. "
            "No file contents are opened, and no files are modified. "
            "The script makes no direct network calls, but a filesystem may be remote. "
            "Review the game terms and obtain any necessary permission before use."
        ),
    )
    parser.add_argument("--locale-dir", required=True, type=Path, help="directory to inspect")
    args = parser.parse_args(argv)
    try:
        report = inspect_directory(args.locale_dir)
    except InventoryError:
        print("ERROR: directory unavailable, not a directory, or a link/reparse point.", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if report["result"] == "incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
