#!/usr/bin/env python3
"""Model latest-original backup rotation using invented hashes, without writes.

The old manifest, observations and new-build reference are caller-supplied.
This model does not hash files, authenticate references, lock the game, stage
backups, install patches or delete anything. It never authorizes a write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from . import model_restore_preflight as restore
    from . import translation_bundle as bundles
else:
    import model_restore_preflight as restore
    import translation_bundle as bundles


def model_refresh(
    recorded: Any,
    observed: Any,
    new_reference: Any,
    *,
    assume_trusted_new_reference: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Classify a refresh; every action is hypothetical and conditional.

    The asserted reference has the desired new patch hash and the original
    hash for the exact new build. The prototype cannot verify this assertion,
    file bytes, semantic dependencies, a process lock, or recovery readiness.
    The previous manifest must have an intact backup for every listed file.
    """
    if assume_trusted_new_reference is not True:
        raise bundles.BundleError("refresh requires a trusted new-reference assertion")
    old_scope, old_build, old_files = restore._input(recorded, recorded=True)
    current_scope, current_build, current_files = restore._input(observed, recorded=False)
    ref_scope, ref_build, ref_files = restore._input(new_reference, recorded=True)
    current_by_id = {item["id"]: item for item in current_files}
    ref_by_id = {item["id"]: item for item in ref_files}
    old_ids = {item["id"] for item in old_files}
    if set(current_by_id) != old_ids or set(ref_by_id) != old_ids:
        raise bundles.BundleError("refresh: file set mismatch")

    counts = {
        "files": len(old_files),
        "unchanged_clean": 0,
        "unchanged_patch": 0,
        "install_from_clean": 0,
        "replace_previous_patch": 0,
        "backup_retained": 0,
        "backup_retained_old_build_only": 0,
        "backup_stage_new_after_verification": 0,
        "blocked_invalid_previous_backup": 0,
        "blocked_current_unavailable": 0,
        "blocked_stale_patch": 0,
        "blocked_unknown_current": 0,
    }
    items = []
    for old_file in old_files:
        identifier = old_file["id"]
        current = current_by_id[identifier]
        new = ref_by_id[identifier]
        old_original = old_file["original_sha256"]
        old_patch = old_file["patched_sha256"]
        new_original = new["original_sha256"]
        new_patch = new["patched_sha256"]
        current_hash = current["current_sha256"]
        backup_hash = current["backup_sha256"]
        backup_action = None
        if backup_hash != old_original:
            state = "blocked_invalid_previous_backup"
        elif current_hash is None:
            state = "blocked_current_unavailable"
        elif current_hash == old_patch and old_patch != old_original:
            # Never take the recorded patched bytes as a fresh backup, even if
            # the supplied new reference claims those same bytes are original.
            if new_original != old_original:
                state = "blocked_stale_patch"
            else:
                state = "unchanged_patch" if current_hash == new_patch else "replace_previous_patch"
                backup_action = "backup_retained"
        elif current_hash == new_original:
            if current_hash == new_patch:
                state = "unchanged_clean"
                backup_action = (
                    "backup_retained" if backup_hash == new_original
                    else "backup_retained_old_build_only"
                )
            else:
                state = "install_from_clean"
                backup_action = (
                    "backup_retained" if backup_hash == new_original
                    else "backup_stage_new_after_verification"
                )
        else:
            state = "blocked_unknown_current"
        counts[state] += 1
        if backup_action:
            counts[backup_action] += 1
        items.append({
            "id": identifier,
            "hypothetical_file_state": state,
            "hypothetical_backup_action": backup_action,
        })

    scope_matches = old_scope == current_scope == ref_scope
    reference_matches_build = current_build == ref_build
    conflicts = sum(counts[key] for key in (
        "blocked_invalid_previous_backup", "blocked_current_unavailable",
        "blocked_stale_patch", "blocked_unknown_current",
    ))
    if not scope_matches:
        decision = "blocked_scope_mismatch"
    elif not reference_matches_build:
        decision = "blocked_new_reference_build_mismatch"
    elif conflicts:
        decision = "blocked_conflicts"
    else:
        decision = "needs_further_preflight"
    common = {
        "schema": 1,
        "scope": "synthetic_backup_refresh_model_v1",
        "decision": decision,
        "build_label_changed": old_build != current_build,
        "scope_labels_match": scope_matches,
        "new_reference_build_label_matches": reference_matches_build,
        "new_reference_asserted_trusted": True,
        "new_reference_or_hashes_verified": False,
        "filesystem_or_process_checks_performed": False,
        "semantic_dependencies_verified": False,
        "writes_performed": False,
        "write_authorized": False,
        "old_backup_deletion_authorized": False,
    }
    return {**common, "counts": counts}, {**common, "items": items}


def main(argv: list[str] | None = None) -> int:
    parser = bundles.RedactingArgumentParser(
        prog="model_backup_refresh",
        description=(
            "Synthetic backup rotation model, not a patcher. "
            "It reads supplied JSON only and never writes or deletes files."
        ),
    )
    parser.add_argument("--recorded", type=Path, required=True)
    parser.add_argument("--observed", type=Path, required=True)
    parser.add_argument("--new-reference", type=Path, required=True)
    parser.add_argument("--assume-trusted-new-reference", action="store_true", required=True)
    parser.add_argument("--details", action="store_true", help="also show supplied logical IDs")
    args = parser.parse_args(argv)
    try:
        recorded = bundles.load_json(args.recorded, max_bytes=bundles.MAX_SOURCE_BYTES)
        observed = bundles.load_json(args.observed, max_bytes=bundles.MAX_SOURCE_BYTES)
        reference = bundles.load_json(args.new_reference, max_bytes=bundles.MAX_SOURCE_BYTES)
        report, details = model_refresh(recorded, observed, reference, assume_trusted_new_reference=True)
        output = json.dumps(details if args.details else report, ensure_ascii=True, indent=2)
    except bundles.BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
