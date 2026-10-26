#!/usr/bin/env python3

"""Produce conservative descriptive RQ3 associations and model-feasibility diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record
from importlib import import_module


exploratory = import_module("16_generate_exploratory_rq2_rq3_results")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "outputs/rq3/association_dataset_v2/rq3_association_events.csv"
DEFAULT_OUTPUT = ROOT / "outputs/rq3/association_results_v4"
ANALYSIS_VERSION = "rq3-descriptive-associations-v1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def model_is_supported(
    events: int, positive_events: int, positive_repositories: int,
    negative_repositories: int, total_repositories: int,
) -> bool:
    return bool(
        events >= 50
        and positive_events >= 10
        and positive_repositories >= 5
        and negative_repositories >= 5
        and total_repositories >= 30
    )


def add_exposures(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    frame["x_parent_100plus_lines"] = frame["parent_line_count"].ge(100)
    frame["x_anchor_age_90plus_days"] = frame["days_since_anchor"].ge(90)
    frame["x_prior_divergence"] = frame["prior_divergence_events"].gt(0)
    frame["x_family_reuse_11plus"] = frame["reuse_count"].ge(11)
    frame["x_location_other"] = frame["location_class"].eq("other")
    frame["x_parent_blob_present"] = frame["parent_blob_present"].astype(bool)
    for target in ("command", "external_access", "script_reference"):
        for scenario in ("strict", "broad"):
            source = f"parent_has_{target}_{scenario}"
            frame[f"x_{source}"] = frame[source].astype(bool)
    frame["x_merge_comparison"] = frame["is_merge"].astype(bool)
    frame["x_diff_10plus_lines"] = frame["diff_changed_lines"].ge(10)
    return frame


def weighted_prevalence(frame: pd.DataFrame, outcome: str) -> float:
    if frame.empty:
        return math.nan
    return float(
        np.average(
            frame[outcome].astype(float),
            weights=frame["sampling_weight_conditional"].astype(float),
        )
    )


def risk_ratio(frame: pd.DataFrame, outcome: str, exposure: str) -> tuple[float, float, float]:
    exposed = weighted_prevalence(frame.loc[frame[exposure].eq(True)], outcome)
    unexposed = weighted_prevalence(frame.loc[frame[exposure].eq(False)], outcome)
    ratio = exposed / unexposed if unexposed > 0 and math.isfinite(exposed) else math.nan
    return exposed, unexposed, ratio


def eligible_for_exposure(frame: pd.DataFrame, exposure: str) -> pd.DataFrame:
    if exposure.startswith("x_parent_") and exposure != "x_parent_blob_present":
        return frame.loc[frame["parent_blob_present"].eq(True)].copy()
    return frame


def cluster_bootstrap_rr(
    frame: pd.DataFrame, outcome: str, exposure: str, replicates: int, seed: int
) -> tuple[float, float, int]:
    working = frame.copy()
    working["_w_y"] = working["sampling_weight_conditional"].astype(float) * working[outcome].astype(float)
    working["_w"] = working["sampling_weight_conditional"].astype(float)
    repositories = []
    for (stratum, repo), group in working.groupby(["selection_stratum", "repo_full_name"], sort=True):
        row = {"selection_stratum": stratum, "repo_full_name": repo}
        for exposed in (False, True):
            subset = group.loc[group[exposure].eq(exposed)]
            suffix = "1" if exposed else "0"
            row[f"num_{suffix}"] = subset["_w_y"].sum()
            row[f"den_{suffix}"] = subset["_w"].sum()
        repositories.append(row)
    repo_frame = pd.DataFrame(repositories)
    rng = np.random.default_rng(seed)
    keys = ("num_0", "den_0", "num_1", "den_1")
    totals = {key: np.zeros(replicates) for key in keys}
    for _, group in repo_frame.groupby("selection_stratum", sort=True):
        indexes = rng.integers(0, len(group), size=(replicates, len(group)))
        for key in keys:
            values = group[key].to_numpy(dtype=float)
            totals[key] += values[indexes].sum(axis=1)
    valid = (totals["den_0"] > 0) & (totals["den_1"] > 0) & (totals["num_0"] > 0)
    estimates = (
        (totals["num_1"][valid] / totals["den_1"][valid])
        / (totals["num_0"][valid] / totals["den_0"][valid])
    )
    if len(estimates) < max(100, replicates // 4):
        return math.nan, math.nan, len(estimates)
    low, high = np.quantile(estimates, [0.025, 0.975])
    return float(low), float(high), len(estimates)


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    if args.bootstrap_replicates < 1:
        raise ValueError("--bootstrap-replicates deve ser positivo")
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_dir = Path(args.output_dir).expanduser().resolve()
    prevalence_path = output_dir / "rq3_outcome_prevalence.csv"
    diagnostics_path = output_dir / "rq3_model_diagnostics.csv"
    associations_path = output_dir / "rq3_descriptive_associations.csv"
    sensitivity_path = output_dir / "rq3_scenario_sensitivity.csv"
    cooccurrence_path = output_dir / "rq3_broad_cooccurrence.csv"
    manifest_path = output_dir / "rq3_association_manifest.json"
    paths = [prevalence_path, diagnostics_path, associations_path, sensitivity_path, cooccurrence_path, manifest_path]
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(paths, args.overwrite)

    data = add_exposures(pd.read_csv(input_path))
    outcome_columns = sorted(
        c for c in data
        if (c.endswith("_strict") or c.endswith("_broad"))
        and not c.startswith(("parent_has_", "x_"))
    )
    exposure_columns = sorted(c for c in data if c.startswith("x_"))
    total_repositories = data["repo_full_name"].nunique()
    prevalence_rows = []
    diagnostic_rows = []
    association_rows = []
    for outcome in outcome_columns:
        data[outcome] = data[outcome].astype(bool)
        positives = int(data[outcome].sum())
        positive_repos = data.loc[data[outcome], "repo_full_name"].nunique()
        negative_repos = data.loc[~data[outcome], "repo_full_name"].nunique()
        low, high = exploratory.wilson_interval(positives, len(data))
        prevalence_rows.append(
            {
                "outcome": outcome,
                "positive_events": positives,
                "events": len(data),
                "positive_repositories": positive_repos,
                "repositories": total_repositories,
                "proportion_unweighted": positives / len(data),
                "wilson_low": low,
                "wilson_high": high,
                "proportion_weighted_conditional": weighted_prevalence(data, outcome),
            }
        )
        supported = model_is_supported(len(data), positives, positive_repos, negative_repos, total_repositories)
        diagnostic_rows.append(
            {
                "outcome": outcome,
                "positive_events": positives,
                "positive_repositories": positive_repos,
                "negative_repositories": negative_repos,
                "total_repositories": total_repositories,
                "multivariable_model_supported": supported,
                "decision": "model_allowed" if supported else "descriptive_only",
                "reason": "thresholds_met" if supported else "fewer_than_30_repository_clusters_or_sparse_outcome",
            }
        )
        for exposure in exposure_columns:
            analysis_data = eligible_for_exposure(data, exposure)
            exposed = analysis_data.loc[analysis_data[exposure]]
            unexposed = analysis_data.loc[~analysis_data[exposure]]
            exp_prev, unexp_prev, rr = risk_ratio(analysis_data, outcome, exposure)
            derived_seed = args.seed + int(hashlib.sha256(f"{outcome}|{exposure}".encode()).hexdigest()[:8], 16)
            ci_low, ci_high, finite = cluster_bootstrap_rr(
                analysis_data, outcome, exposure, args.bootstrap_replicates, derived_seed
            )
            association_rows.append(
                {
                    "outcome": outcome,
                    "exposure": exposure,
                    "eligible_events": len(analysis_data),
                    "exposed_events": len(exposed),
                    "unexposed_events": len(unexposed),
                    "exposed_repositories": exposed["repo_full_name"].nunique(),
                    "unexposed_repositories": unexposed["repo_full_name"].nunique(),
                    "positive_exposed": int(exposed[outcome].sum()),
                    "positive_unexposed": int(unexposed[outcome].sum()),
                    "weighted_prevalence_exposed": exp_prev,
                    "weighted_prevalence_unexposed": unexp_prev,
                    "weighted_risk_ratio": rr,
                    "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high,
                    "finite_bootstrap_replicates": finite,
                    "interpretation_status": "exploratory_descriptive_only",
                }
            )

    prevalence = pd.DataFrame(prevalence_rows)
    diagnostics = pd.DataFrame(diagnostic_rows)
    associations = pd.DataFrame(association_rows)
    sensitivity_rows = []
    for strict in sorted(c for c in outcome_columns if c.endswith("_strict")):
        base = strict[: -len("_strict")]
        broad = f"{base}_broad"
        if broad not in data:
            continue
        strict_set = set(data.loc[data[strict], "diff_id"])
        broad_set = set(data.loc[data[broad], "diff_id"])
        sensitivity_rows.append(
            {
                "outcome_base": base,
                "strict_events": len(strict_set),
                "broad_events": len(broad_set),
                "broad_only_events": len(broad_set - strict_set),
                "strict_subset_of_broad": strict_set <= broad_set,
                "jaccard_strict_broad": len(strict_set & broad_set) / len(strict_set | broad_set) if strict_set | broad_set else 1.0,
            }
        )
    sensitivity = pd.DataFrame(sensitivity_rows)
    broad_positive = [c for c in outcome_columns if c.endswith("_broad") and data[c].any()]
    cooccurrence = pd.DataFrame(
        [[int((data[left] & data[right]).sum()) for right in broad_positive] for left in broad_positive],
        index=broad_positive,
        columns=broad_positive,
    ).reset_index(names="outcome")
    atomic_csv(prevalence, prevalence_path)
    atomic_csv(diagnostics, diagnostics_path)
    atomic_csv(associations, associations_path)
    atomic_csv(sensitivity, sensitivity_path)
    atomic_csv(cooccurrence, cooccurrence_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(input_path)]
    manifest["analysis_version"] = ANALYSIS_VERSION
    manifest["model_gate"] = {
        "minimum_events": 50,
        "minimum_positive_events": 10,
        "minimum_positive_repositories": 5,
        "minimum_negative_repositories": 5,
        "minimum_repository_clusters": 30,
    }
    manifest["results"] = {
        "events": len(data),
        "repositories": total_repositories,
        "outcomes": len(outcome_columns),
        "exposures": len(exposure_columns),
        "outcomes_supporting_multivariable_model": int(diagnostics["multivariable_model_supported"].sum()),
        "descriptive_associations": len(associations),
    }
    manifest["interpretation"] = (
        "Risk ratios and bootstrap intervals are descriptive, design-weighted associations in the "
        "conditioned complete-case sample; they are not adjusted, causal, or population-generalizable."
    )
    manifest["missingness_rule"] = (
        "Parent-content exposures are evaluated only where the parent blob exists; file additions are not coded as absence of a parent feature."
    )
    manifest["limitations"] = [
        "Only 18 repositories contribute post-anchor events and one repository contributes 29 of 75 events.",
        "No outcome passes the pre-specified 30-cluster model gate.",
        "Automated outcomes have no independent semantic validation.",
        "Bootstrap intervals may be unavailable when resamples have zero outcomes in a comparison group.",
        "No p-values or FDR are produced because no inferential regression family is fitted.",
    ]
    manifest["outputs"] = [file_record(p) for p in paths[:-1]]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
