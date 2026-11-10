#!/usr/bin/env python3
"""Compare two invented normalized snapshots, never a game installation.

The caller must assert that both snapshots cover the same complete scope with
stable IDs. This prototype cannot verify that assertion. Matching records are
review candidates only; no translations are carried over or files written.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from . import translation_bundle as bundles
else:
    import translation_bundle as bundles


COMPARISON = "same_complete_scope_and_stable_ids_user_asserted"
FIELDS = ("source", "context", "protected_tokens")
Signature = tuple[str, str, tuple[str, ...]]


def _signature(record: dict[str, Any]) -> Signature:
    return (record["source"], record["context"], tuple(record["protected_tokens"]))


def _prior_translation(
    old_items: dict[str, dict[str, Any]], identifier: str
) -> tuple[str, str | None]:
    item = old_items.get(identifier)
    if item is None:
        return "not_in_supplied_bundle", None
    if item["translation"] is None:
        return "explicit_null", None
    return "supplied_unreviewed", item["translation"]


def _review_item(
    category: str,
    old_record: dict[str, Any] | None,
    new_record: dict[str, Any],
    old_items: dict[str, dict[str, Any]],
    *,
    changed_fields: list[str] | None = None,
    matching_old_records: int | None = None,
) -> dict[str, Any]:
    old_id = old_record["id"] if old_record else None
    state, translation = (
        _prior_translation(old_items, old_id) if old_id else ("not_assigned", None)
    )
    return {
        "category": category,
        "old_record": old_record,
        "new_record": new_record,
        "changed_fields": changed_fields or [],
        "matching_old_records": matching_old_records,
        "previous_translation_state": state,
        "previous_translation": translation,
        "review_required": True,
        "reused_automatically": False,
    }


def audit_update(
    old_source: Any,
    new_source: Any,
    old_bundle: Any = None,
    *,
    assume_comparable: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return a count report, a new-snapshot task bundle and review references.

    The optional old bundle can be partial. Omission means unknown, not that a
    record or its translation was deleted. Results are conditional on the
    caller's asserted scope and identity; they never verify a real build.
    """
    if assume_comparable is not True:
        raise bundles.BundleError("comparison requires a same-scope and stable-ID assertion")

    old = bundles.normalize_source(old_source)
    new = bundles.normalize_source(new_source)
    old_template = bundles.prepare_bundle(old)
    new_template = bundles.prepare_bundle(new)
    old_bundle_report = None
    old_items: dict[str, dict[str, Any]] = {}
    if old_bundle is not None:
        old_bundle_report = bundles.validate_bundle(old, old_bundle)
        old_items = {item["id"]: item for item in old_bundle["items"]}

    old_records = {record["id"]: record for record in old["records"]}
    new_records = {record["id"]: record for record in new["records"]}
    old_only = old_records.keys() - new_records.keys()
    new_only = new_records.keys() - old_records.keys()

    old_signatures: dict[Signature, list[str]] = defaultdict(list)
    new_signatures: dict[Signature, list[str]] = defaultdict(list)
    for record in old["records"]:
        old_signatures[_signature(record)].append(record["id"])
    for record in new["records"]:
        new_signatures[_signature(record)].append(record["id"])

    # Equal content may be a duplicate, not a moved record. Even the unique
    # case is only a human-review hint, never an automatic ID mapping or reuse.
    possible_moves: dict[str, str] = {}
    ambiguous_counts: dict[str, int] = {}
    for record in new["records"]:
        identifier = record["id"]
        if identifier not in new_only:
            continue
        signature = _signature(record)
        matches = old_signatures.get(signature, [])
        if not matches:
            continue
        if len(matches) == 1 and len(new_signatures[signature]) == 1 and matches[0] in old_only:
            possible_moves[identifier] = matches[0]
        else:
            ambiguous_counts[identifier] = len(matches)

    todo_reasons: dict[str, str] = {}
    review_items = []
    counts = {
        "old_records": len(old_records),
        "new_records": len(new_records),
        "same_id_same_fields": 0,
        "same_id_changed": 0,
        "id_only_in_new": len(new_only),
        "id_only_in_old": len(old_only),
        "changed_source": 0,
        "changed_context": 0,
        "changed_protected_tokens": 0,
        "unchanged_prior_translation_candidates": 0,
        "unchanged_prior_explicit_null": 0,
        "unchanged_prior_unknown": 0,
        "possible_id_changes_exact_unique": len(possible_moves),
        "ambiguous_new_ids_with_equal_record": len(ambiguous_counts),
    }
    for new_record in new["records"]:
        identifier = new_record["id"]
        old_record = old_records.get(identifier)
        if old_record is None:
            todo_reasons[identifier] = "id_only_in_new"
            if identifier in possible_moves:
                review_items.append(_review_item(
                    "possible_id_change", old_records[possible_moves[identifier]], new_record, old_items
                ))
            elif identifier in ambiguous_counts:
                review_items.append(_review_item(
                    "ambiguous_equal_record", None, new_record, old_items,
                    matching_old_records=ambiguous_counts[identifier],
                ))
            continue

        changed = [field for field in FIELDS if old_record[field] != new_record[field]]
        if changed:
            counts["same_id_changed"] += 1
            for field in changed:
                counts[f"changed_{field}"] += 1
            todo_reasons[identifier] = "changed_record"
            review_items.append(_review_item(
                "changed_record", old_record, new_record, old_items, changed_fields=changed
            ))
            continue

        counts["same_id_same_fields"] += 1
        state, _ = _prior_translation(old_items, identifier)
        if state == "supplied_unreviewed":
            counts["unchanged_prior_translation_candidates"] += 1
            review_items.append(_review_item(
                "unchanged_translation_candidate", old_record, new_record, old_items
            ))
        else:
            if state == "explicit_null":
                counts["unchanged_prior_explicit_null"] += 1
                todo_reasons[identifier] = "prior_explicit_null"
            else:
                counts["unchanged_prior_unknown"] += 1
                todo_reasons[identifier] = "prior_unknown"

    task_bundle = {
        **new_template,
        "items": [item for item in new_template["items"] if item["id"] in todo_reasons],
    }
    counts["task_records"] = len(task_bundle["items"])
    counts["review_records"] = len(review_items)
    common = {
        "schema": 1,
        "scope": "prototype_normalized_update_v1",
        "comparison_assumption": COMPARISON,
        "comparison_assumption_verified": False,
        "game_compatibility_verified": False,
        "old_source_digest": old_template["source_digest"],
        "new_source_digest": new_template["source_digest"],
        "old_bundle_supplied": old_bundle is not None,
        "old_bundle_digest": old_bundle_report["bundle_digest"] if old_bundle_report else None,
    }
    report = {**common, "counts": counts}
    review = {
        **common,
        "task_reasons": [
            {"id": record["id"], "reason": todo_reasons[record["id"]]}
            for record in new["records"] if record["id"] in todo_reasons
        ],
        "ids_only_in_old": [record["id"] for record in old["records"] if record["id"] in old_only],
        "items": review_items,
    }
    return report, task_bundle, review


def main(argv: list[str] | None = None) -> int:
    parser = bundles.RedactingArgumentParser(
        prog="audit_translation_update",
        description=(
            "Prototype for invented JSON snapshots only; no game files or writes. "
            "Todo and review modes print source text and may print translations."
        ),
    )
    parser.add_argument("--old-source", type=Path, required=True)
    parser.add_argument("--new-source", type=Path, required=True)
    parser.add_argument("--old-bundle", type=Path)
    parser.add_argument("--mode", choices=("report", "todo", "review"), default="report")
    parser.add_argument(
        "--assume-comparable", action="store_true", required=True,
        help="assert the same complete scope and stable IDs (not independently verified)",
    )
    args = parser.parse_args(argv)
    try:
        old_source = bundles.load_json(args.old_source, max_bytes=bundles.MAX_SOURCE_BYTES)
        new_source = bundles.load_json(args.new_source, max_bytes=bundles.MAX_SOURCE_BYTES)
        old_bundle = None
        if args.old_bundle is not None:
            old_bundle = bundles.load_json(args.old_bundle, max_bytes=bundles.MAX_BUNDLE_BYTES)
            if old_bundle is None:
                raise bundles.BundleError("bundle: invalid fields")
        report, todo, review = audit_update(
            old_source, new_source, old_bundle, assume_comparable=args.assume_comparable
        )
        result = {"report": report, "todo": todo, "review": review}[args.mode]
        output = json.dumps(result, ensure_ascii=True, indent=2)
        largest_output = len(output.encode("ascii")) + output.count("\n") + 2
        if largest_output > bundles.MAX_BUNDLE_BYTES:
            raise bundles.BundleError("output is too large; split the synthetic inputs")
    except bundles.BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
