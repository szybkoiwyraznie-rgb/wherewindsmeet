#!/usr/bin/env python3
"""Prepare and validate a format-neutral translation bundle, not game files.

The input is a small, normalized JSON document supplied by an eventual extractor.
No Where Winds Meet extractor or installer exists yet. Validation covers only
explicitly declared literal tokens; it does not prove game-format compatibility,
placeholder completeness, legal permission, or safety of a modified game file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA = 1
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_BUNDLE_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 10000
MAX_TEXT_CHARS = 100000
MAX_TOKENS = 256
MAX_TOKEN_CHARS = 256
# Bound repeated literal scans even for compact, adversarial JSON inputs.
MAX_TOKEN_CHECK_WORK = 16 * 1024 * 1024
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z")
HEX_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SOURCE_KEYS = frozenset({"schema", "source_id", "records"})
RECORD_KEYS = frozenset({"id", "source", "context", "protected_tokens"})
BUNDLE_KEYS = frozenset({"schema", "source_id", "source_digest", "items"})
ITEM_KEYS = RECORD_KEYS | {"source_sha256", "translation"}


class BundleError(ValueError):
    """Invalid document or bundle; messages never include user text or paths."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleError(message)


def _exact_object(value: Any, keys: frozenset[str], where: str) -> None:
    _require(type(value) is dict and set(value) == keys, f"{where}: invalid fields")


def _schema(value: Any, where: str) -> None:
    _require(type(value) is int and value == SCHEMA, f"{where}: unsupported schema")


def _identifier(value: Any, where: str) -> str:
    _require(type(value) is str and IDENTIFIER.fullmatch(value) is not None, f"{where}: invalid identifier")
    return value


def _text(value: Any, where: str, *, allow_empty: bool = True) -> str:
    _require(type(value) is str and len(value) <= MAX_TEXT_CHARS, f"{where}: invalid text")
    if not allow_empty:
        _require(bool(value.strip()), f"{where}: empty translation")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise BundleError(f"{where}: invalid Unicode") from exc
    return value


def _literal_count(text: str, token: str) -> int:
    """Count literal occurrences, including overlaps, without interpreting syntax."""
    # A proper suffix equal to a prefix permits overlaps (e.g. "aba" in
    # "ababa"). A token without such a border can use the faster str.count.
    overlaps_itself = any(token.startswith(token[shift:]) for shift in range(1, len(token)))
    if not overlaps_itself:
        return text.count(token)
    count = 0
    offset = 0
    while True:
        index = text.find(token, offset)
        if index < 0:
            return count
        count += 1
        offset = index + 1


def _tokens(value: Any, source: str, where: str) -> list[str]:
    _require(type(value) is list and len(value) <= MAX_TOKENS, f"{where}: invalid tokens")
    checked: list[str] = []
    for token in value:
        token = _text(token, where)
        _require(0 < len(token) <= MAX_TOKEN_CHARS, f"{where}: invalid token")
        _require(token in source, f"{where}: token absent from source")
        checked.append(token)
    _require(len(set(checked)) == len(checked), f"{where}: duplicate token")
    return sorted(checked)


def normalize_source(document: Any) -> dict[str, Any]:
    """Validate a v1 normalized source and return a fresh canonical structure."""
    _exact_object(document, SOURCE_KEYS, "source")
    _schema(document["schema"], "source")
    source_id = _identifier(document["source_id"], "source")
    records = document["records"]
    _require(type(records) is list and 0 < len(records) <= MAX_RECORDS, "source: invalid records")
    seen: set[str] = set()
    normalized = []
    token_work = 0
    for index, record in enumerate(records):
        where = f"source record {index + 1}"
        _exact_object(record, RECORD_KEYS, where)
        identifier = _identifier(record["id"], where)
        _require(identifier not in seen, f"{where}: duplicate identifier")
        seen.add(identifier)
        text = _text(record["source"], where)
        context = _text(record["context"], where)
        tokens = _tokens(record["protected_tokens"], text, where)
        token_work += len(text) * len(tokens)
        _require(token_work <= MAX_TOKEN_CHECK_WORK, "source: token check limit exceeded")
        normalized.append({"id": identifier, "source": text, "context": context, "protected_tokens": tokens})
    return {"schema": SCHEMA, "source_id": source_id, "records": normalized}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_digest(document: dict[str, Any]) -> str:
    # Object key order and whitespace are irrelevant; array order is significant.
    data = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(data.encode("utf-8"))


def _snapshot_digest(normalized: dict[str, Any]) -> str:
    # Record order is significant. Keys and token-list order are normalized.
    return _canonical_digest(normalized)


def prepare_bundle(source: Any) -> dict[str, Any]:
    """Return a translation template containing the source text and context."""
    normalized = normalize_source(source)
    items = []
    for record in normalized["records"]:
        items.append({
            **record,
            "source_sha256": _sha256(record["source"].encode("utf-8")),
            "translation": None,
        })
    return {
        "schema": SCHEMA,
        "source_id": normalized["source_id"],
        "source_digest": _snapshot_digest(normalized),
        "items": items,
    }


def validate_bundle(source: Any, bundle: Any) -> dict[str, Any]:
    """Validate a complete or partial return without changing any input or file."""
    normalized = normalize_source(source)
    _exact_object(bundle, BUNDLE_KEYS, "bundle")
    _schema(bundle["schema"], "bundle")
    _require(bundle["source_id"] == normalized["source_id"], "bundle: source identifier mismatch")
    digest = bundle["source_digest"]
    _require(
        type(digest) is str and HEX_SHA256.fullmatch(digest) is not None,
        "bundle: invalid source digest",
    )
    _require(digest == _snapshot_digest(normalized), "bundle: source snapshot mismatch")
    items = bundle["items"]
    _require(type(items) is list and len(items) <= len(normalized["records"]), "bundle: invalid items")
    by_id = {record["id"]: record for record in normalized["records"]}
    seen: set[str] = set()
    translated = 0
    token_work = 0
    for index, item in enumerate(items):
        where = f"bundle item {index + 1}"
        _exact_object(item, ITEM_KEYS, where)
        identifier = _identifier(item["id"], where)
        _require(identifier not in seen, f"{where}: duplicate identifier")
        seen.add(identifier)
        _require(identifier in by_id, f"{where}: unknown identifier")
        original = by_id[identifier]
        _require(item["source"] == original["source"], f"{where}: source text changed")
        _require(item["context"] == original["context"], f"{where}: context changed")
        # Strict equality also rejects changed order and duplicate token declarations.
        _require(item["protected_tokens"] == original["protected_tokens"], f"{where}: token list changed")
        item_hash = item["source_sha256"]
        _require(
            type(item_hash) is str and HEX_SHA256.fullmatch(item_hash) is not None,
            f"{where}: invalid source hash",
        )
        expected_hash = _sha256(original["source"].encode("utf-8"))
        _require(item_hash == expected_hash, f"{where}: source hash mismatch")
        translation = item["translation"]
        if translation is None:
            continue
        translation = _text(translation, where, allow_empty=False)
        token_work += (len(original["source"]) + len(translation)) * len(original["protected_tokens"])
        _require(token_work <= MAX_TOKEN_CHECK_WORK, "bundle: token check limit exceeded")
        for token in original["protected_tokens"]:
            expected = _literal_count(original["source"], token)
            actual = _literal_count(translation, token)
            _require(actual == expected, f"{where}: protected token count changed")
        translated += 1
    return {
        "valid": True,
        "scope": "prototype_normalized_json_v1",
        "source_digest": digest,
        "bundle_digest": _canonical_digest(bundle),
        "source_records": len(normalized["records"]),
        "bundle_items": len(items),
        "translated": translated,
        "untranslated": len(items) - translated,
        "omitted_from_bundle": len(normalized["records"]) - len(items),
        "complete": translated == len(normalized["records"]),
        "token_check": "declared_literals_only",
        "game_compatibility_verified": False,
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise BundleError("JSON: duplicate object key")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise BundleError("JSON: non-standard numeric value")


def load_json(path: Path, *, max_bytes: int = MAX_SOURCE_BYTES) -> Any:
    """Read bounded UTF-8 JSON (optionally with BOM), without disclosing paths."""
    path = Path(path)
    _require(path.suffix.lower() == ".json", "input must be a .json document")
    try:
        with path.open("rb") as file:
            raw = file.read(max_bytes + 1)
    except OSError as exc:
        raise BundleError("cannot read JSON input") from exc
    _require(len(raw) <= max_bytes, "JSON input is too large")
    try:
        return json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, BundleError):
            raise
        raise BundleError("invalid UTF-8 JSON input") from exc


class RedactingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, "ERROR: invalid arguments; use --help for syntax.\n")


def main(argv: list[str] | None = None) -> int:
    parser = RedactingArgumentParser(
        prog="translation_bundle",
        description=(
            "Prototype for invented normalized JSON, not game files. "
            "No files are written. The prepare command prints source text to stdout."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="print a template with source text")
    prepare.add_argument("--source", type=Path, required=True)
    validate = commands.add_parser("validate", help="print a content-free validation report")
    validate.add_argument("--source", type=Path, required=True)
    validate.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        source = load_json(args.source, max_bytes=MAX_SOURCE_BYTES)
        if args.command == "prepare":
            result = prepare_bundle(source)
        else:
            returned = load_json(args.bundle, max_bytes=MAX_BUNDLE_BYTES)
            result = validate_bundle(source, returned)
        output = json.dumps(result, ensure_ascii=True, indent=2)
        if args.command == "prepare":
            # A successful template must be readable later by the validator.
            # Text-mode output may turn each LF into CRLF on Windows.
            largest_output = len(output.encode("ascii")) + output.count("\n") + 2
            _require(largest_output <= MAX_BUNDLE_BYTES, "prepared bundle is too large")
    except BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
