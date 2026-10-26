#!/usr/bin/env python3

"""Generate exploratory post-anchor RQ2/RQ3 results with explicit denominators."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FLOW = ROOT / "outputs" / "rq2" / "analytic_recovery_v1" / "analytic_recovery_flow.csv"
DEFAULT_HISTORY_DIR = ROOT / "outputs" / "rq2" / "history_analytic_v1"
DEFAULT_DIFFS = ROOT / "outputs" / "rq2" / "diff_analytic_v1" / "diff_events.csv"
DEFAULT_STRUCTURED = (
    ROOT / "outputs" / "rq2" / "structured_diff_analytic_v1" / "structured_diff_events.csv"
)
DEFAULT_RQ3 = ROOT / "outputs" / "rq3" / "behavioral_analytic_v2" / "rq3_behavioral_events.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "exploratory_results_v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow", default=str(DEFAULT_FLOW))
    parser.add_argument("--history-dir", default=str(DEFAULT_HISTORY_DIR))
    parser.add_argument("--diffs", default=str(DEFAULT_DIFFS))
    parser.add_argument("--structured", default=str(DEFAULT_STRUCTURED))
    parser.add_argument("--rq3", default=str(DEFAULT_RQ3))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return math.nan, math.nan
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    half = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return max(0.0, center - half), min(1.0, center + half)


def history_dates(history_path: Path) -> dict[str, pd.Timestamp]:
    dates: dict[str, pd.Timestamp] = {}
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        dates[str(event["commit"])] = pd.Timestamp(event["committed_at"])
    return dates


def build_longitudinal_outcomes(
    flow: pd.DataFrame,
    diffs: pd.DataFrame,
    history_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = flow.loc[flow["analysis_eligible"].eq(True)].copy()
    outcomes: list[dict[str, object]] = []
    post_ids: list[dict[str, object]] = []
    for _, occurrence in eligible.sort_values("occurrence_id").iterrows():
        occurrence_id = str(occurrence["occurrence_id"])
        anchor_sha = str(occurrence["anchor_file_sha"])
        date_map = history_dates(history_dir / str(occurrence["history_jsonl"]))
        occurrence_diffs = diffs.loc[
            diffs["occurrence_id"].eq(occurrence_id)
            & diffs["is_change_event"].eq(True)
        ].copy()
        occurrence_diffs["committed_at"] = occurrence_diffs["commit"].map(date_map)
        anchor_rows = occurrence_diffs.loc[
            occurrence_diffs["new_blob_sha"].fillna("").eq(anchor_sha)
            & occurrence_diffs["committed_at"].notna()
        ]
        if len(anchor_rows):
            anchor_time = anchor_rows["committed_at"].min()
            anchor_commits = sorted(
                anchor_rows.loc[anchor_rows["committed_at"].eq(anchor_time), "commit"].unique()
            )
            anchor_commit = anchor_commits[0]
            anchor_status = "resolved"
            post = occurrence_diffs.loc[
                occurrence_diffs["committed_at"].notna()
                & occurrence_diffs["committed_at"].gt(anchor_time)
            ].copy()
            divergent = post.loc[
                ~post["new_blob_sha"].fillna("").eq(anchor_sha)
            ].copy()
            first_divergence = (
                divergent["committed_at"].min() if len(divergent) else pd.NaT
            )
            days_to_divergence = (
                (first_divergence - anchor_time).total_seconds() / 86400
                if pd.notna(first_divergence)
                else math.nan
            )
            for _, event in post.iterrows():
                post_ids.append(
                    {
                        "diff_id": event["diff_id"],
                        "occurrence_id": occurrence_id,
                        "committed_at": event["committed_at"],
                        "anchor_commit": anchor_commit,
                        "anchor_committed_at": anchor_time,
                        "selection_stratum": occurrence["selection_stratum"],
                        "sampling_weight_conditional": occurrence[
                            "sampling_weight_conditional"
                        ],
                        "is_divergence_from_anchor": not (
                            str(event.get("new_blob_sha", "")) == anchor_sha
                        ),
                    }
                )
        else:
            anchor_time = pd.NaT
            anchor_commit = None
            anchor_status = "unresolved"
            post = occurrence_diffs.iloc[0:0]
            divergent = post
            first_divergence = pd.NaT
            days_to_divergence = math.nan
        outcomes.append(
            {
                "occurrence_id": occurrence_id,
                "repo_full_name": occurrence["repo_full_name"],
                "path": occurrence["path"],
                "anchor_file_sha": anchor_sha,
                "selection_stratum": occurrence["selection_stratum"],
                "selection_probability_conditional": occurrence[
                    "selection_probability_conditional"
                ],
                "sampling_weight_conditional": occurrence["sampling_weight_conditional"],
                "anchor_resolution_status": anchor_status,
                "anchor_commit": anchor_commit,
                "anchor_committed_at": anchor_time,
                "post_anchor_parent_comparisons": len(post),
                "post_anchor_unique_commits": post["commit"].nunique(),
                "post_anchor_divergence_comparisons": len(divergent),
                "diverged_after_anchor": bool(len(divergent)) if anchor_status == "resolved" else pd.NA,
                "first_divergence_at": first_divergence,
                "days_to_first_divergence": days_to_divergence,
                "head_path_status": occurrence["head_path_status"],
            }
        )
    return pd.DataFrame(outcomes), pd.DataFrame(post_ids)


def weighted_rate(frame: pd.DataFrame, outcome: str) -> float:
    weights = frame["sampling_weight_conditional"].astype(float)
    values = frame[outcome].astype(float)
    return float(np.average(values, weights=weights))


def stratified_cluster_bootstrap(
    frame: pd.DataFrame,
    outcome: str,
    replicates: int,
    seed: int,
) -> tuple[float, float]:
    if replicates < 1 or frame.empty:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    working = frame.copy()
    working["_weighted_outcome"] = (
        working["sampling_weight_conditional"].astype(float)
        * working[outcome].astype(float)
    )
    repository_totals = (
        working.groupby(["selection_stratum", "repo_full_name"], sort=True)
        .agg(
            numerator=("_weighted_outcome", "sum"),
            denominator=("sampling_weight_conditional", "sum"),
        )
        .reset_index()
    )
    bootstrap_numerator = np.zeros(replicates)
    bootstrap_denominator = np.zeros(replicates)
    for _, group in repository_totals.groupby("selection_stratum", sort=True):
        numerators = group["numerator"].to_numpy(dtype=float)
        denominators = group["denominator"].to_numpy(dtype=float)
        indexes = rng.integers(0, len(group), size=(replicates, len(group)))
        bootstrap_numerator += numerators[indexes].sum(axis=1)
        bootstrap_denominator += denominators[indexes].sum(axis=1)
    estimates = bootstrap_numerator / bootstrap_denominator
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


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
    if args.bootstrap_replicates < 1:
        raise ValueError("--bootstrap-replicates deve ser positivo")
    flow_path = Path(args.flow).expanduser().resolve()
    history_dir = Path(args.history_dir).expanduser().resolve()
    diffs_path = Path(args.diffs).expanduser().resolve()
    structured_path = Path(args.structured).expanduser().resolve()
    rq3_path = Path(args.rq3).expanduser().resolve()
    inputs = [flow_path, diffs_path, structured_path, rq3_path]
    if any(not path.is_file() for path in inputs) or not history_dir.is_dir():
        raise FileNotFoundError("Entrada analítica não encontrada")
    output_dir = Path(args.output_dir).expanduser().resolve()
    outcomes_path = output_dir / "rq2_occurrence_outcomes.csv"
    post_events_path = output_dir / "post_anchor_events.csv"
    rq2_summary_path = output_dir / "rq2_exploratory_summary.csv"
    rq3_summary_path = output_dir / "rq3_exploratory_summary.csv"
    manifest_path = output_dir / "exploratory_results_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [outcomes_path, post_events_path, rq2_summary_path, rq3_summary_path, manifest_path],
        args.overwrite,
    )

    flow = pd.read_csv(flow_path)
    diffs = pd.read_csv(diffs_path)
    structured_events = pd.read_csv(structured_path)
    rq3_events = pd.read_csv(rq3_path)
    outcomes, post_index = build_longitudinal_outcomes(flow, diffs, history_dir)
    rq3_only_columns = ["diff_id"] + [
        column
        for column in rq3_events.columns
        if column != "diff_id" and column not in structured_events.columns
    ]
    post_events = post_index.merge(
        structured_events,
        on=["diff_id", "occurrence_id"],
        how="left",
        validate="one_to_one",
    ).merge(
        rq3_events[rq3_only_columns],
        on="diff_id",
        how="left",
        validate="one_to_one",
    )

    resolved = outcomes.loc[outcomes["anchor_resolution_status"].eq("resolved")].copy()
    diverged_count = int(resolved["diverged_after_anchor"].astype(bool).sum())
    wilson_low, wilson_high = wilson_interval(diverged_count, len(resolved))
    weighted_divergence = weighted_rate(resolved, "diverged_after_anchor") if len(resolved) else math.nan
    bootstrap_low, bootstrap_high = stratified_cluster_bootstrap(
        resolved,
        "diverged_after_anchor",
        args.bootstrap_replicates,
        args.seed,
    )
    rq2_rows = [
        {"metric": "selected_repositories", "numerator": flow["repo_full_name"].nunique(), "denominator": pd.NA, "estimate": pd.NA, "ci_low": pd.NA, "ci_high": pd.NA, "method": "count"},
        {"metric": "selected_occurrences", "numerator": len(flow), "denominator": pd.NA, "estimate": pd.NA, "ci_low": pd.NA, "ci_high": pd.NA, "method": "count"},
        {"metric": "eligible_occurrences", "numerator": int(flow["analysis_eligible"].sum()), "denominator": len(flow), "estimate": float(flow["analysis_eligible"].mean()), "ci_low": pd.NA, "ci_high": pd.NA, "method": "sample_flow"},
        {"metric": "anchor_resolved_occurrences", "numerator": len(resolved), "denominator": len(outcomes), "estimate": len(resolved) / len(outcomes) if len(outcomes) else math.nan, "ci_low": pd.NA, "ci_high": pd.NA, "method": "eligible_complete_case"},
        {"metric": "diverged_after_anchor_unweighted", "numerator": diverged_count, "denominator": len(resolved), "estimate": diverged_count / len(resolved) if len(resolved) else math.nan, "ci_low": wilson_low, "ci_high": wilson_high, "method": "Wilson_95_unweighted"},
        {"metric": "diverged_after_anchor_weighted_conditional", "numerator": diverged_count, "denominator": len(resolved), "estimate": weighted_divergence, "ci_low": bootstrap_low, "ci_high": bootstrap_high, "method": f"design_weighted_cluster_bootstrap_{args.bootstrap_replicates}"},
        {"metric": "post_anchor_parent_comparisons", "numerator": len(post_events), "denominator": len(resolved), "estimate": len(post_events) / len(resolved) if len(resolved) else math.nan, "ci_low": pd.NA, "ci_high": pd.NA, "method": "descriptive"},
    ]
    for operation, group in post_events.groupby("change_operation", sort=True):
        indicator = f"_operation_{operation}"
        post_events[indicator] = post_events["change_operation"].eq(operation)
        weighted_operation = weighted_rate(post_events, indicator)
        operation_low, operation_high = stratified_cluster_bootstrap(
            post_events, indicator, args.bootstrap_replicates, args.seed
        )
        rq2_rows.append(
            {"metric": f"post_anchor_operation_{operation}", "numerator": len(group), "denominator": len(post_events), "estimate": len(group) / len(post_events) if len(post_events) else math.nan, "ci_low": pd.NA, "ci_high": pd.NA, "method": "event_comparison_descriptive"}
        )
        rq2_rows.append(
            {"metric": f"post_anchor_operation_{operation}_weighted_conditional", "numerator": len(group), "denominator": len(post_events), "estimate": weighted_operation, "ci_low": operation_low, "ci_high": operation_high, "method": f"design_weighted_cluster_bootstrap_{args.bootstrap_replicates}"}
        )
    rq2_summary = pd.DataFrame(rq2_rows)

    rq3_rows = []
    target_directions = {
        "command": ["added", "deleted"],
        "external_access": ["added", "deleted"],
        "script_reference": ["added", "deleted"],
        "executable_sibling": ["added", "removed", "modified", "moved_or_copied"],
    }
    for scenario in ("strict", "broad"):
        for target, directions in target_directions.items():
            for direction in directions:
                column = f"{target}_{direction}_{scenario}"
                if column not in post_events:
                    continue
                numerator = int(post_events[column].fillna(False).astype(bool).sum())
                low, high = wilson_interval(numerator, len(post_events))
                post_events[column] = post_events[column].fillna(False).astype(bool)
                weighted = weighted_rate(post_events, column)
                bootstrap_target_low, bootstrap_target_high = stratified_cluster_bootstrap(
                    post_events,
                    column,
                    args.bootstrap_replicates,
                    args.seed,
                )
                rq3_rows.append(
                    {
                        "scenario": scenario,
                        "target": target,
                        "direction": direction,
                        "numerator_events": numerator,
                        "denominator_post_anchor_parent_comparisons": len(post_events),
                        "proportion_unweighted": numerator / len(post_events) if len(post_events) else math.nan,
                        "ci_low_wilson": low,
                        "ci_high_wilson": high,
                        "proportion_weighted_conditional": weighted,
                        "ci_low_cluster_bootstrap": bootstrap_target_low,
                        "ci_high_cluster_bootstrap": bootstrap_target_high,
                    }
                )
    rq3_summary = pd.DataFrame(rq3_rows)

    atomic_csv(outcomes, outcomes_path)
    atomic_csv(post_events, post_events_path)
    atomic_csv(rq2_summary, rq2_summary_path)
    atomic_csv(rq3_summary, rq3_summary_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(path) for path in inputs]
    manifest["temporal_rule"] = (
        "Anchor is the earliest observed commit-time at which the child blob equals the "
        "snapshot anchor SHA. Only comparisons with strictly later commit-time are post-anchor."
    )
    manifest["estimand_scope"] = (
        "Exploratory complete-case results for the probe-conditioned analytic sample; "
        "design weights do not correct nonresponse or probe selection bias."
    )
    manifest["results"] = {
        "eligible_occurrences": len(outcomes),
        "anchor_resolved_occurrences": len(resolved),
        "anchor_unresolved_occurrences": int(len(outcomes) - len(resolved)),
        "post_anchor_parent_comparisons": len(post_events),
        "diverged_occurrences": diverged_count,
    }
    manifest["limitations"] = [
        "Commit timestamps order observations but do not prove authorship or transmission.",
        "Equal timestamps are not ordered and are excluded by the strict-later rule.",
        "Parent comparisons in merges are dependent and are not independent events.",
        "Wilson intervals ignore repository/family dependence; the weighted divergence interval uses a stratified repository bootstrap.",
        "Automated RQ3 labels have no independent semantic validation.",
        "Results do not generalize beyond the conditioned frame without additional assumptions.",
    ]
    manifest["outputs"] = [
        file_record(outcomes_path),
        file_record(post_events_path),
        file_record(rq2_summary_path),
        file_record(rq3_summary_path),
    ]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
