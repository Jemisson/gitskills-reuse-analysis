#!/usr/bin/env python3

"""Find exact-patch adoption candidates across observed repositories."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNATURES = ROOT / "outputs/rq2/patch_signatures_v1/patch_signatures.csv"
DEFAULT_OBSERVATIONS = ROOT / "outputs/rq2/patch_signatures_v1/occurrence_observation.csv"
DEFAULT_OUTPUT = ROOT / "outputs/rq2/adoption_candidates_v3"
CANDIDATE_COLUMNS = [
    "anchor_file_sha", "patch_signature", "source_diff_id", "source_occurrence_id",
    "source_repo", "source_commit", "source_committed_at", "source_matching_events",
    "source_matching_occurrences", "target_diff_id", "target_occurrence_id", "target_repo",
    "target_commit", "target_committed_at", "target_matching_events",
    "target_matching_occurrences", "temporal_order", "delay_days", "same_old_blob",
    "same_new_blob", "same_commit", "change_operation",
]
COVERAGE_COLUMNS = [
    "source_diff_id", "anchor_file_sha", "patch_signature", "source_repo",
    "source_committed_at", "other_observed_family_occurrences",
    "temporally_observable_occurrences", "temporally_observable_repositories",
    "context_eligible_denominator_known",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signatures", default=str(DEFAULT_SIGNATURES))
    parser.add_argument("--observations", default=str(DEFAULT_OBSERVATIONS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def repository_episodes(signatures: pd.DataFrame) -> pd.DataFrame:
    usable = signatures.loc[
        signatures["signature_eligible"].eq(True)
        & signatures["is_post_anchor_divergence"].eq(True)
        & signatures["committed_at"].notna()
    ].copy()
    usable["committed_at"] = pd.to_datetime(usable["committed_at"], utc=True)
    keys = ["anchor_file_sha", "patch_signature", "repo_full_name"]
    usable = usable.sort_values(keys + ["committed_at", "diff_id"])
    counts = (
        usable.groupby(keys, sort=True)
        .agg(
            matching_event_count=("diff_id", "size"),
            matching_occurrence_count=("occurrence_id", "nunique"),
        )
        .reset_index()
    )
    first = usable.drop_duplicates(keys, keep="first")
    return first.merge(counts, on=keys, how="left", validate="one_to_one")


def build_candidates(signatures: pd.DataFrame) -> pd.DataFrame:
    usable = repository_episodes(signatures)
    rows: list[dict[str, object]] = []
    keys = ["anchor_file_sha", "patch_signature"]
    for _, group in usable.groupby(keys, sort=True):
        records = list(group.sort_values(["committed_at", "repo_full_name", "diff_id"]).to_dict("records"))
        for left_index, left in enumerate(records):
            for right in records[left_index + 1 :]:
                if left["repo_full_name"] == right["repo_full_name"]:
                    continue
                left_time = pd.Timestamp(left["committed_at"])
                right_time = pd.Timestamp(right["committed_at"])
                if left_time == right_time:
                    source, target = left, right
                    ordering = "timestamp_tie_direction_indeterminate"
                    delay = 0.0
                else:
                    source, target = (left, right) if left_time < right_time else (right, left)
                    ordering = "strictly_later"
                    delay = abs((right_time - left_time).total_seconds()) / 86400
                rows.append(
                    {
                        "anchor_file_sha": source["anchor_file_sha"],
                        "patch_signature": source["patch_signature"],
                        "source_diff_id": source["diff_id"],
                        "source_occurrence_id": source["occurrence_id"],
                        "source_repo": source["repo_full_name"],
                        "source_commit": source["commit"],
                        "source_committed_at": source["committed_at"],
                        "source_matching_events": source["matching_event_count"],
                        "source_matching_occurrences": source["matching_occurrence_count"],
                        "target_diff_id": target["diff_id"],
                        "target_occurrence_id": target["occurrence_id"],
                        "target_repo": target["repo_full_name"],
                        "target_commit": target["commit"],
                        "target_committed_at": target["committed_at"],
                        "target_matching_events": target["matching_event_count"],
                        "target_matching_occurrences": target["matching_occurrence_count"],
                        "temporal_order": ordering,
                        "delay_days": delay,
                        "same_old_blob": str(source["old_blob_sha"]) == str(target["old_blob_sha"]),
                        "same_new_blob": str(source["new_blob_sha"]) == str(target["new_blob_sha"]),
                        "same_commit": str(source["commit"]) == str(target["commit"]),
                        "change_operation": source["change_operation"],
                    }
                )
    return pd.DataFrame(rows, columns=CANDIDATE_COLUMNS)


def build_coverage(signatures: pd.DataFrame, observations: pd.DataFrame) -> pd.DataFrame:
    sources = repository_episodes(signatures)
    observations = observations.loc[observations["anchor_resolution_status"].eq("resolved")].copy()
    observations["anchor_committed_at"] = pd.to_datetime(observations["anchor_committed_at"], utc=True)
    observations["observed_last_commit_at"] = pd.to_datetime(observations["observed_last_commit_at"], utc=True)
    rows = []
    for _, source in sources.sort_values("diff_id").iterrows():
        source_time = pd.Timestamp(source["committed_at"])
        if source_time.tzinfo is None:
            source_time = source_time.tz_localize("UTC")
        family = observations.loc[
            observations["anchor_file_sha"].eq(source["anchor_file_sha"])
            & ~observations["repo_full_name"].eq(source["repo_full_name"])
        ]
        temporal = family.loc[
            family["anchor_committed_at"].le(source_time)
            & family["observed_last_commit_at"].gt(source_time)
        ]
        rows.append(
            {
                "source_diff_id": source["diff_id"],
                "anchor_file_sha": source["anchor_file_sha"],
                "patch_signature": source["patch_signature"],
                "source_repo": source["repo_full_name"],
                "source_committed_at": source_time,
                "other_observed_family_occurrences": len(family),
                "temporally_observable_occurrences": len(temporal),
                "temporally_observable_repositories": temporal["repo_full_name"].nunique(),
                "context_eligible_denominator_known": False,
            }
        )
    return pd.DataFrame(rows, columns=COVERAGE_COLUMNS)


def main() -> None:
    args = parse_args()
    signatures_path = Path(args.signatures).expanduser().resolve()
    observations_path = Path(args.observations).expanduser().resolve()
    if not signatures_path.is_file() or not observations_path.is_file():
        raise FileNotFoundError("Assinaturas ou observações não encontradas")
    output_dir = Path(args.output_dir).expanduser().resolve()
    candidates_path = output_dir / "adoption_candidates.csv"
    coverage_path = output_dir / "search_coverage.csv"
    manifest_path = output_dir / "adoption_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([candidates_path, coverage_path, manifest_path], args.overwrite)
    signatures = pd.read_csv(signatures_path)
    observations = pd.read_csv(observations_path)
    candidates = build_candidates(signatures)
    coverage = build_coverage(signatures, observations)
    atomic_csv(candidates, candidates_path)
    atomic_csv(coverage, coverage_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(signatures_path), file_record(observations_path)]
    manifest["candidate_rule"] = (
        "Same exact normalized patch signature, same exact-content anchor family, distinct repositories, "
        "and both events are observed post-anchor divergences. Repeated paths/commits are collapsed to the "
        "first repository-level episode. Timestamp ties retain indeterminate direction."
    )
    manifest["results"] = {
        "candidate_pairs": len(candidates),
        "strictly_ordered_pairs": int(candidates.get("temporal_order", pd.Series(dtype=str)).eq("strictly_later").sum()),
        "timestamp_ties": int(candidates.get("temporal_order", pd.Series(dtype=str)).eq("timestamp_tie_direction_indeterminate").sum()),
        "source_events_with_temporal_opportunity": int((coverage["temporally_observable_repositories"] > 0).sum()),
    }
    manifest["limitations"] = [
        "Candidate identity does not prove copying or ancestry.",
        "Repository-level collapse prevents repeated paths or branch events from creating pseudoreplication.",
        "The search universe is the analytic complete-case corpus, not GitHub.",
        "Temporal opportunity is not context eligibility; no propagation rate denominator is claimed.",
    ]
    manifest["outputs"] = [file_record(candidates_path), file_record(coverage_path)]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
