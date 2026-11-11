#!/usr/bin/env python3
"""Reproduce an external-tool experiment using ONLY an invented test fixture.

The upstream tool is not distributed here. A matching SHA-256 identifies the
exact version studied; it is not a security audit or sandbox. The only input
passed to the upstream script is generated here, not a game file. See
advice and prerequisites in docs/EXPERIMENT_LOG.md.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests.synthetic_locmap import build_sample  # noqa: E402


# oratakashi/where-winds-meet-indonesian-patch at 2289aacd..., GPL-3.0.
UPSTREAM_SHA256 = "84568408ac48a2eff9b11172c001e023f52892f925715dc6ae2fb92d0615f819"
FIXTURE_SHA256 = "74727d2426308ce1cbe3bf45041add58a7a9280688ac0e749a8aa9f18a91cd34"
UPSTREAM_SIZE = 13934
ZSTANDARD_VERSION = "0.24.0"


class ExperimentError(Exception):
    """A prerequisite or an expected observation did not hold."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExperimentError(message)


def read_pinned_tool(path: Path) -> bytes:
    """Check the name, size and digest before accepting the external script."""
    try:
        info = path.lstat()
        require(path.name == "wwm_locmap.py", "external script must be named wwm_locmap.py")
        is_reparse = bool(
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
        )
        require(stat.S_ISREG(info.st_mode) and not is_reparse, "external script must be a regular non-link file")
        require(info.st_size == UPSTREAM_SIZE, "external script size differs")
        with path.open("rb") as source:
            data = source.read(UPSTREAM_SIZE + 1)
    except OSError as exc:
        raise ExperimentError("cannot read the external script") from exc
    require(len(data) == UPSTREAM_SIZE, "external script size changed")
    require(hashlib.sha256(data).hexdigest() == UPSTREAM_SHA256, "external script hash differs")
    return data


def experiment(tool: bytes) -> None:
    try:
        installed = metadata.version("zstandard")
    except metadata.PackageNotFoundError as exc:
        raise ExperimentError(f"zstandard=={ZSTANDARD_VERSION} is not installed") from exc
    require(installed == ZSTANDARD_VERSION, f"zstandard=={ZSTANDARD_VERSION} is required")
    with tempfile.TemporaryDirectory(prefix="wwm-synthetic-") as tmp:
        root = Path(tmp)
        executable = root / "wwm_locmap.py"
        executable.write_bytes(tool)
        source = root / "synthetic.locmap"
        sample = build_sample()
        require(hashlib.sha256(sample).hexdigest() == FIXTURE_SHA256, "fixture hash differs")
        source.write_bytes(sample)

        def run(command: str, *paths: Path, expect_success: bool = True):
            try:
                result = subprocess.run(
                    [sys.executable, "-B", str(executable), command, *map(str, paths)],
                    cwd=root,
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ExperimentError(f"could not run {command} on the synthetic fixture") from exc
            require(
                (result.returncode == 0) == expect_success,
                f"unexpected {command} exit code {result.returncode}; check zstandard dependency",
            )
            return result

        def dump(input_file: Path, name: str) -> list[dict]:
            output = root / name
            run("dump", input_file, output)
            try:
                records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            except (OSError, ValueError) as exc:
                raise ExperimentError("cannot parse the synthetic dump") from exc
            require(all(isinstance(row, dict) for row in records), "synthetic dump rows are not objects")
            return records

        def edit_file(name: str, edits: list[dict]) -> Path:
            path = root / name
            path.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in edits),
                encoding="utf-8",
            )
            return path

        run("info", source)
        rows = dump(source, "dump.jsonl")
        require(
            [row.get("v") for row in rows] == ["Hello, {hero}!", "Another line."],
            "unexpected synthetic records",
        )
        first = rows[0]
        require(all(key in first for key in ("b", "s", "h")), "synthetic record lacks identity fields")

        partial = edit_file("partial.jsonl", [{**first, "v": "Witaj, {hero}!"}])
        partial_output = root / "partial.locmap"
        run("patch", source, partial, partial_output)
        require(
            [row.get("v") for row in dump(partial_output, "partial-dump.jsonl")]
            == ["Witaj, {hero}!", "Another line."],
            "partial edit or untouched record differs",
        )

        wrong_hash = edit_file("wrong-hash.jsonl", [{**first, "h": "ffffffffffffffff"}])
        rejected_output = root / "rejected.locmap"
        rejected = run("patch", source, wrong_hash, rejected_output, expect_success=False)
        require(b"keyHash" in rejected.stderr and not rejected_output.exists(), "hash rejection differs")

        duplicate = edit_file(
            "duplicate.jsonl", [{**first, "v": "First"}, {**first, "v": "Last"}]
        )
        duplicate_output = root / "duplicate.locmap"
        run("patch", source, duplicate, duplicate_output)
        require(
            [row.get("v") for row in dump(duplicate_output, "duplicate-dump.jsonl")]
            == ["Last", "Another line."],
            "duplicate did not produce the expected last value",
        )

        no_hash = edit_file(
            "no-hash.jsonl", [{"b": first["b"], "s": first["s"], "v": "No hash"}]
        )
        no_hash_output = root / "no-hash.locmap"
        run("patch", source, no_hash, no_hash_output)
        require(
            [row.get("v") for row in dump(no_hash_output, "no-hash-dump.jsonl")]
            == ["No hash", "Another line."],
            "edit without hash did not produce the expected value",
        )

    print("Fixture: 404 B, 2 invented records; SHA-256:", FIXTURE_SHA256)
    print("Partial edit and unchanged record: OK; wrong hash: rejected without output.")
    print("Duplicate edit: accepted, last wins; edit without hash: accepted and applied.")
    print("Synthetic experiment only; no claim about any game build or account safety.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-tool", type=Path, required=True, help="path to the pinned script")
    args = parser.parse_args(argv)
    try:
        experiment(read_pinned_tool(args.upstream_tool))
    except ExperimentError as exc:
        print(f"Synthetic experiment failed: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("Synthetic experiment failed: temporary files are unavailable.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
