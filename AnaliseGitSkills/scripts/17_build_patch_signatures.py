#!/usr/bin/env python3

"""Build deterministic exact patch signatures for the observed RQ2 change events."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS = ROOT / "outputs/rq2/structured_diff_analytic_v1/structured_diff_events.csv"
DEFAULT_POST = ROOT / "outputs/exploratory_results_v2/post_anchor_events.csv"
DEFAULT_OUTCOMES = ROOT / "outputs/exploratory_results_v2/rq2_occurrence_outcomes.csv"
DEFAULT_FLOW = ROOT / "outputs/rq2/analytic_recovery_v1/analytic_recovery_flow.csv"
DEFAULT_HISTORY = ROOT / "outputs/rq2/history_analytic_v1"
DEFAULT_DIFF_ROOT = ROOT / "outputs/rq2/diff_analytic_v1"
DEFAULT_OUTPUT = ROOT / "outputs/rq2/patch_signatures_v1"
SIGNATURE_VERSION = "exact-normalized-patch-v1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", default=str(DEFAULT_EVENTS))
    parser.add_argument("--post-anchor-events", default=str(DEFAULT_POST))
    parser.add_argument("--outcomes", default=str(DEFAULT_OUTCOMES))
    parser.add_argument("--flow", default=str(DEFAULT_FLOW))
    parser.add_argument("--history-dir", default=str(DEFAULT_HISTORY))
    parser.add_argument("--diff-root", default=str(DEFAULT_DIFF_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalize_changed_line(value: str) -> str:
    value = unicodedata.normalize("NFC", value.rstrip("\r\n"))
    return re.sub(r"\s+", " ", value.strip())


def changed_lines(diff_text: str) -> tuple[list[str], list[str]]:
    added: list[str] = []
    deleted: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            normalized = normalize_changed_line(line[1:])
            if normalized:
                added.append(normalized)
        elif line.startswith("-"):
            normalized = normalize_changed_line(line[1:])
            if normalized:
                deleted.append(normalized)
    return added, deleted


def patch_signature(operation: str, added: list[str], deleted: list[str]) -> str:
    payload = json.dumps(
        {"operation": operation, "deleted": deleted, "added": added},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def history_bounds(path: Path) -> tuple[pd.Timestamp, pd.Timestamp, dict[str, pd.Timestamp]]:
    dates: dict[str, pd.Timestamp] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            event = json.loads(line)
            dates[str(event["commit"])] = pd.Timestamp(event["committed_at"])
    values = list(dates.values())
    return min(values), max(values), dates


def main() -> None:
    args = parse_args()
    events_path = Path(args.events).expanduser().resolve()
    post_path = Path(args.post_anchor_events).expanduser().resolve()
    outcomes_path = Path(args.outcomes).expanduser().resolve()
    flow_path = Path(args.flow).expanduser().resolve()
    history_dir = Path(args.history_dir).expanduser().resolve()
    diff_root = Path(args.diff_root).expanduser().resolve()
    inputs = [events_path, post_path, outcomes_path, flow_path]
    if any(not path.is_file() for path in inputs) or not history_dir.is_dir():
        raise FileNotFoundError("Entrada para assinaturas não encontrada")
    output_dir = Path(args.output_dir).expanduser().resolve()
    signatures_path = output_dir / "patch_signatures.csv"
    observations_path = output_dir / "occurrence_observation.csv"
    groups_path = output_dir / "signature_groups.csv"
    manifest_path = output_dir / "signature_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [signatures_path, observations_path, groups_path, manifest_path], args.overwrite
    )

    events = pd.read_csv(events_path)
    post = pd.read_csv(post_path)
    outcomes = pd.read_csv(outcomes_path).set_index("occurrence_id")
    flow = pd.read_csv(flow_path)
    eligible = flow.loc[flow["analysis_eligible"].eq(True)].copy()
    post_index = post.set_index("diff_id")
    observations: list[dict[str, object]] = []
    commit_dates: dict[str, dict[str, pd.Timestamp]] = {}
    for _, row in eligible.sort_values("occurrence_id").iterrows():
        start, end, date_map = history_bounds(history_dir / str(row["history_jsonl"]))
        occurrence_id = str(row["occurrence_id"])
        commit_dates[occurrence_id] = date_map
        outcome = outcomes.loc[occurrence_id]
        anchor_time = outcome["anchor_committed_at"] if outcome["anchor_resolution_status"] == "resolved" else ""
        observations.append(
            {
                "occurrence_id": occurrence_id,
                "repo_full_name": row["repo_full_name"],
                "path": row["path"],
                "anchor_file_sha": row["anchor_file_sha"],
                "selection_stratum": row["selection_stratum"],
                "sampling_weight_conditional": row["sampling_weight_conditional"],
                "anchor_resolution_status": outcome["anchor_resolution_status"],
                "anchor_committed_at": anchor_time,
                "observed_first_commit_at": start,
                "observed_last_commit_at": end,
            }
        )
    observation = pd.DataFrame(observations)
    metadata = observation.set_index("occurrence_id")

    rows: list[dict[str, object]] = []
    for _, event in events.sort_values("diff_id").iterrows():
        occurrence_id = str(event["occurrence_id"])
        raw_path = diff_root / str(event["raw_diff_file"])
        if not raw_path.is_file():
            raise FileNotFoundError(raw_path)
        added, deleted = changed_lines(raw_path.read_text(encoding="utf-8", errors="replace"))
        operation = str(event["change_operation"])
        eligible_signature = bool(added or deleted) and operation != "movement"
        signature = patch_signature(operation, added, deleted) if eligible_signature else ""
        meta = metadata.loc[occurrence_id]
        is_post = event["diff_id"] in post_index.index
        is_divergence = bool(post_index.loc[event["diff_id"], "is_divergence_from_anchor"]) if is_post else False
        rows.append(
            {
                "diff_id": event["diff_id"],
                "occurrence_id": occurrence_id,
                "repo_full_name": event["repo_full_name"],
                "path": meta["path"],
                "anchor_file_sha": meta["anchor_file_sha"],
                "commit": event["commit"],
                "parent": event["parent"],
                "committed_at": commit_dates[occurrence_id].get(str(event["commit"]), pd.NaT),
                "change_operation": operation,
                "old_blob_sha": event.get("old_blob_sha", ""),
                "new_blob_sha": event.get("new_blob_sha", ""),
                "normalized_added_lines": len(added),
                "normalized_deleted_lines": len(deleted),
                "patch_signature": signature,
                "signature_eligible": eligible_signature,
                "is_post_anchor_event": is_post,
                "is_post_anchor_divergence": is_post and is_divergence,
                "signature_version": SIGNATURE_VERSION,
            }
        )
    signatures = pd.DataFrame(rows)
    usable = signatures.loc[signatures["signature_eligible"]].copy()
    groups = (
        usable.groupby(["anchor_file_sha", "patch_signature"], sort=True)
        .agg(events=("diff_id", "size"), repositories=("repo_full_name", "nunique"), occurrences=("occurrence_id", "nunique"), post_anchor_sources=("is_post_anchor_divergence", "sum"))
        .reset_index()
    )
    atomic_csv(signatures, signatures_path)
    atomic_csv(observation, observations_path)
    atomic_csv(groups, groups_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(path) for path in inputs]
    manifest["signature_definition"] = {
        "version": SIGNATURE_VERSION,
        "normalization": "Unicode NFC; trim; collapse whitespace; omit blank changed lines",
        "identity": "SHA-256 of ordered deleted/added normalized lines plus operation",
        "exclusions": "empty patches and pure movements",
    }
    manifest["results"] = {
        "events": len(signatures),
        "eligible_signatures": int(signatures["signature_eligible"].sum()),
        "cross_repository_signature_groups": int((groups["repositories"] > 1).sum()),
        "post_anchor_divergent_sources": int(signatures["is_post_anchor_divergence"].sum()),
        "observed_occurrences": len(observation),
    }
    manifest["limitations"] = [
        "Exact normalized patch identity is a retrieval rule, not proof of transmission.",
        "Whitespace normalization can merge superficially distinct patches.",
        "Only histories already recovered for the analytic complete cases are searched.",
    ]
    manifest["outputs"] = [file_record(p) for p in [signatures_path, observations_path, groups_path]]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
