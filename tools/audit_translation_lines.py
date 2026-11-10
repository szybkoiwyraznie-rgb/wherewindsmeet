#!/usr/bin/env python3
"""Select new or changed *synthetic atomic lines*, not entire scenes.

The inputs are normalized JSON invented by the caller, not game files. The
caller asserts comparable scope and stable line IDs; neither is verified.
Repeated text on a new ID, empty fields, metadata-only changes and old
incomplete work are separate from the delta. No translation is transferred
and no files are written.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from . import audit_translation_update as audit
    from . import translation_bundle as bundles
else:
    import audit_translation_update as audit
    import translation_bundle as bundles


LINE_SEPARATORS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")


def _atomic_lines(source: dict[str, Any]) -> None:
    for index, record in enumerate(source["records"], 1):
        if any(character in LINE_SEPARATORS for character in record["source"]):
            raise bundles.BundleError(f"source record {index}: not a single synthetic line")


def audit_lines(
    old_source: Any,
    new_source: Any,
    old_bundle: Any = None,
    *,
    assume_comparable: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return summary, delta bundle, review, and separate old-work backlog.

    ``old_bundle`` is optional and validated against the old full snapshot.
    No status in this prototype means the previous translation was approved.
    A new ID with a previously seen exact source is withheld for human review,
    not automatically reused or sent for translation. A change only in context
    or token declarations also requires review rather than automatic carryover.
    """
    base_report, _, _ = audit.audit_update(
        old_source, new_source, old_bundle, assume_comparable=assume_comparable
    )
    old = bundles.normalize_source(old_source)
    new = bundles.normalize_source(new_source)
    _atomic_lines(old)
    _atomic_lines(new)
    template = bundles.prepare_bundle(new)

    old_by_id = {record["id"]: record for record in old["records"]}
    new_by_id = {record["id"]: record for record in new["records"]}
    old_by_text: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in old["records"]:
        old_by_text[record["source"]].append(record)
    old_items = {item["id"]: item for item in old_bundle["items"]} if old_bundle is not None else {}

    delta_reasons: dict[str, str] = {}
    backlog_reasons: dict[str, str] = {}
    review_items = []
    counts = {
        "old_lines": len(old_by_id),
        "new_lines": len(new_by_id),
        "new_id_new_source_text": 0,
        "same_id_changed_source_text": 0,
        "new_id_existing_source_review": 0,
        "empty_or_whitespace_source_review": 0,
        "same_id_metadata_only_review": 0,
        "unchanged_unreviewed_candidate": 0,
        "unchanged_explicit_null_backlog": 0,
        "unchanged_unknown_backlog": 0,
        "id_only_in_old": len(old_by_id.keys() - new_by_id.keys()),
    }
    for record in new["records"]:
        identifier = record["id"]
        prior = old_by_id.get(identifier)
        if not record["source"].strip():
            # An empty field may be meaningful layout data or a deletion; it
            # is not a useful sentence to send blindly for translation.
            changed = [field for field in audit.FIELDS if prior and prior[field] != record[field]]
            counts["empty_or_whitespace_source_review"] += 1
            review_items.append(audit._review_item(
                "empty_or_whitespace_source", prior, record, old_items, changed_fields=changed
            ))
            continue
        if prior is None:
            matches = old_by_text.get(record["source"], [])
            if matches:
                counts["new_id_existing_source_review"] += 1
                # Never select among duplicate sources. One hit is a hint, not
                # proof the record moved or that its context is equivalent.
                match = matches[0] if len(matches) == 1 else None
                review_items.append(audit._review_item(
                    "new_id_source_seen_before", match, record, old_items,
                    matching_old_records=len(matches),
                ))
            else:
                counts["new_id_new_source_text"] += 1
                delta_reasons[identifier] = "new_id_new_source_text"
            continue

        changed = [field for field in audit.FIELDS if prior[field] != record[field]]
        if "source" in changed:
            counts["same_id_changed_source_text"] += 1
            delta_reasons[identifier] = "same_id_changed_source_text"
            review_items.append(audit._review_item(
                "changed_line_reference", prior, record, old_items, changed_fields=changed
            ))
        elif changed:
            counts["same_id_metadata_only_review"] += 1
            review_items.append(audit._review_item(
                "context_or_tokens_only", prior, record, old_items, changed_fields=changed
            ))
        else:
            state, _ = audit._prior_translation(old_items, identifier)
            if state == "supplied_unreviewed":
                counts["unchanged_unreviewed_candidate"] += 1
                review_items.append(audit._review_item(
                    "unchanged_translation_candidate", prior, record, old_items
                ))
            elif state == "explicit_null":
                counts["unchanged_explicit_null_backlog"] += 1
                backlog_reasons[identifier] = "prior_explicit_null"
            else:
                counts["unchanged_unknown_backlog"] += 1
                backlog_reasons[identifier] = "prior_unknown"

    delta = {**template, "items": [item for item in template["items"] if item["id"] in delta_reasons]}
    backlog = {**template, "items": [item for item in template["items"] if item["id"] in backlog_reasons]}
    counts["delta_lines"] = len(delta["items"])
    counts["backlog_lines"] = len(backlog["items"])
    counts["review_entries"] = len(review_items)
    common = {key: value for key, value in base_report.items() if key != "counts"}
    common["scope"] = "prototype_synthetic_atomic_line_delta_v1"
    report = {**common, "counts": counts}
    review = {
        **common,
        "delta_reasons": [
            {"id": record["id"], "reason": delta_reasons[record["id"]]}
            for record in new["records"] if record["id"] in delta_reasons
        ],
        "backlog_reasons": [
            {"id": record["id"], "reason": backlog_reasons[record["id"]]}
            for record in new["records"] if record["id"] in backlog_reasons
        ],
        "ids_only_in_old": [record["id"] for record in old["records"] if record["id"] not in new_by_id],
        "items": review_items,
    }
    return report, delta, review, backlog


def main(argv: list[str] | None = None) -> int:
    parser = bundles.RedactingArgumentParser(
        prog="audit_translation_lines",
        description=(
            "Invented single-line JSON snapshots only. No game files or writes. "
            "Delta, review and backlog modes print source text."
        ),
    )
    parser.add_argument("--old-source", type=Path, required=True)
    parser.add_argument("--new-source", type=Path, required=True)
    parser.add_argument("--old-bundle", type=Path)
    parser.add_argument("--mode", choices=("report", "delta", "review", "backlog"), default="report")
    parser.add_argument("--assume-comparable", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        old = bundles.load_json(args.old_source, max_bytes=bundles.MAX_SOURCE_BYTES)
        new = bundles.load_json(args.new_source, max_bytes=bundles.MAX_SOURCE_BYTES)
        prior = None
        if args.old_bundle is not None:
            prior = bundles.load_json(args.old_bundle, max_bytes=bundles.MAX_BUNDLE_BYTES)
            if prior is None:
                raise bundles.BundleError("bundle: invalid fields")
        report, delta, review, backlog = audit_lines(old, new, prior, assume_comparable=True)
        result = {"report": report, "delta": delta, "review": review, "backlog": backlog}[args.mode]
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
