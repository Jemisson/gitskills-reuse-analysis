#!/usr/bin/env python3

"""Build the auditable recovery flow and eligible history subset for RQ2/RQ3."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTED = ROOT / "outputs" / "rq2" / "analytic_sample_v1" / "selected_occurrences.csv"
DEFAULT_HISTORY_DIR = ROOT / "outputs" / "rq2" / "history_analytic_v1"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "analytic_recovery_v1"
COMPLETE_STATUSES = {"collected", "collected_cache_size_limit_exceeded"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", default=str(DEFAULT_SELECTED))
    parser.add_argument("--history-dir", default=str(DEFAULT_HISTORY_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def build_recovery_flow(
    selected: pd.DataFrame,
    histories: pd.DataFrame,
    repository_status: pd.DataFrame,
) -> pd.DataFrame:
    if repository_status["repo_full_name"].duplicated().any():
        raise ValueError("Status duplicado por repositório")
    history_columns = [
        "occurrence_id",
        "repo_full_name",
        "path",
        "anchor_blob_available",
        "head_path_status",
        "history_commit_count",
        "history_jsonl",
    ]
    flow = selected.merge(
        repository_status.rename(
            columns={
                "status": "repository_collection_status",
                "error": "repository_collection_error",
            }
        ),
        on="repo_full_name",
        how="left",
        validate="many_to_one",
    ).merge(
        histories[history_columns],
        on=["repo_full_name", "path"],
        how="left",
        validate="one_to_one",
    )
    flow["repository_collection_complete"] = flow[
        "repository_collection_status"
    ].isin(COMPLETE_STATUSES)
    flow["occurrence_processed"] = flow["occurrence_id"].notna()
    flow["analysis_eligible"] = (
        flow["repository_collection_complete"]
        & flow["occurrence_processed"]
        & flow["anchor_blob_available"].fillna(False).astype(bool)
        & flow["history_commit_count"].fillna(0).gt(0)
    )
    reasons = []
    for _, row in flow.iterrows():
        if not row["repository_collection_complete"]:
            reasons.append("repository_collection_incomplete")
        elif not row["occurrence_processed"]:
            reasons.append("occurrence_not_processed")
        elif not bool(row["anchor_blob_available"]):
            reasons.append("anchor_blob_unavailable")
        elif float(row["history_commit_count"]) <= 0:
            reasons.append("empty_history")
        else:
            reasons.append("eligible")
    flow["eligibility_reason"] = reasons
    return flow


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_csv(temporary, index=False)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    args = parse_args()
    selected_path = Path(args.selected).expanduser().resolve()
    history_dir = Path(args.history_dir).expanduser().resolve()
    history_path = history_dir / "history_recovery_summary.csv"
    status_path = history_dir / "repository_collection_status.csv"
    inputs = [selected_path, history_path, status_path]
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("Entrada de recuperação não encontrada")
    output_dir = Path(args.output_dir).expanduser().resolve()
    flow_path = output_dir / "analytic_recovery_flow.csv"
    eligible_path = output_dir / "eligible_history_summary.csv"
    strata_path = output_dir / "recovery_by_stratum.csv"
    manifest_path = output_dir / "analytic_recovery_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([flow_path, eligible_path, strata_path, manifest_path], args.overwrite)

    selected = pd.read_csv(selected_path)
    histories = pd.read_csv(history_path)
    repository_status = pd.read_csv(status_path)
    flow = build_recovery_flow(selected, histories, repository_status)
    eligible_ids = set(flow.loc[flow["analysis_eligible"], "occurrence_id"])
    eligible = histories.loc[histories["occurrence_id"].isin(eligible_ids)].copy()
    eligible = eligible.sort_values(["repo_full_name", "path", "occurrence_id"])
    strata = (
        flow.groupby("selection_stratum", sort=True)
        .agg(
            selected_repositories=("repo_full_name", "nunique"),
            selected_occurrences=("path", "size"),
            complete_repositories=(
                "repo_full_name",
                lambda values: values[
                    flow.loc[values.index, "repository_collection_complete"]
                ].nunique(),
            ),
            eligible_occurrences=("analysis_eligible", "sum"),
        )
        .reset_index()
    )
    strata["repository_recovery_fraction"] = (
        strata["complete_repositories"] / strata["selected_repositories"]
    )
    strata["occurrence_recovery_fraction"] = (
        strata["eligible_occurrences"] / strata["selected_occurrences"]
    )
    atomic_csv(flow, flow_path)
    atomic_csv(eligible, eligible_path)
    atomic_csv(strata, strata_path)

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(path) for path in inputs]
    manifest["eligibility_rule"] = (
        "Repository collection status is complete; occurrence was processed; anchor blob "
        "is available; path history is non-empty. All partial rows from failed repositories "
        "are excluded without replacement."
    )
    manifest["results"] = {
        "selected_repositories": int(flow["repo_full_name"].nunique()),
        "selected_occurrences": len(flow),
        "complete_repositories": int(
            flow.loc[flow["repository_collection_complete"], "repo_full_name"].nunique()
        ),
        "eligible_occurrences": int(flow["analysis_eligible"].sum()),
        "excluded_occurrences": int((~flow["analysis_eligible"]).sum()),
        "eligibility_reason_counts": {
            str(key): int(value)
            for key, value in flow["eligibility_reason"].value_counts().sort_index().items()
        },
    }
    manifest["limitations"] = [
        "No failed repository was replaced.",
        "Recovery fractions describe the selected sample, not the GitSkills population.",
        "Partial rows from failed repositories are preserved in the raw collector output but excluded analytically.",
    ]
    manifest["outputs"] = [file_record(flow_path), file_record(eligible_path), file_record(strata_path)]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
