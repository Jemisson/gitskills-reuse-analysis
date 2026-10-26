#!/usr/bin/env python3

"""Generate article-ready RQ3 tables and figures from the frozen descriptive analysis."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "outputs/rq3/association_results_v4"
DEFAULT_OUTPUT = ROOT / "outputs/rq3/article_artifacts_v3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def save_figure(fig: plt.Figure, path: Path) -> None:
    temporary = path.with_name(f".{path.stem}.{os.getpid()}.tmp{path.suffix}")
    fig.savefig(temporary, dpi=200, bbox_inches="tight")
    plt.close(fig)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    results_dir = Path(args.results_dir).expanduser().resolve()
    input_paths = {
        "prevalence": results_dir / "rq3_outcome_prevalence.csv",
        "diagnostics": results_dir / "rq3_model_diagnostics.csv",
        "associations": results_dir / "rq3_descriptive_associations.csv",
        "sensitivity": results_dir / "rq3_scenario_sensitivity.csv",
    }
    if any(not p.is_file() for p in input_paths.values()):
        raise FileNotFoundError("Resultados RQ3 não encontrados")
    output_dir = Path(args.output_dir).expanduser().resolve()
    prevalence_table_path = output_dir / "table_rq3_prevalence.csv"
    patterns_path = output_dir / "table_rq3_descriptive_patterns.csv"
    decisions_path = output_dir / "table_rq3_model_decisions.csv"
    prevalence_figure_path = output_dir / "figure_rq3_prevalence.png"
    sensitivity_figure_path = output_dir / "figure_rq3_scenario_sensitivity.png"
    manifest_path = output_dir / "rq3_article_artifacts_manifest.json"
    outputs = [prevalence_table_path, patterns_path, decisions_path, prevalence_figure_path, sensitivity_figure_path, manifest_path]
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(outputs, args.overwrite)

    prevalence = pd.read_csv(input_paths["prevalence"])
    diagnostics = pd.read_csv(input_paths["diagnostics"])
    associations = pd.read_csv(input_paths["associations"])
    sensitivity = pd.read_csv(input_paths["sensitivity"])
    prevalence_table = prevalence.loc[prevalence["positive_events"].gt(0)].copy()
    prevalence_table = prevalence_table.sort_values(["positive_events", "outcome"], ascending=[False, True])
    patterns = associations.merge(
        prevalence[["outcome", "positive_events", "positive_repositories"]], on="outcome", how="left"
    )
    patterns = patterns.loc[
        ~patterns["exposure"].isin(["x_merge_comparison", "x_diff_10plus_lines"])
        & patterns["positive_events"].ge(10)
        & patterns["exposed_repositories"].ge(3)
        & patterns["unexposed_repositories"].ge(3)
    ].copy()
    patterns["multiplicity_adjusted"] = False
    patterns["article_interpretation"] = "unadjusted exploratory pattern; do not infer causality or statistical significance"
    patterns = patterns.sort_values(["outcome", "exposure"])
    atomic_csv(prevalence_table, prevalence_table_path)
    atomic_csv(patterns, patterns_path)
    atomic_csv(diagnostics, decisions_path)

    plot = prevalence_table.sort_values("proportion_unweighted")
    labels = plot["outcome"].str.replace("_", " ")
    y = np.arange(len(plot))
    fig, ax = plt.subplots(figsize=(9, max(5, 0.35 * len(plot))))
    x = plot["proportion_unweighted"].to_numpy()
    lower = x - plot["wilson_low"].to_numpy()
    upper = plot["wilson_high"].to_numpy() - x
    ax.errorbar(x, y, xerr=np.vstack([lower, upper]), fmt="o", color="#2f5d8a", label="Não ponderado (IC Wilson 95%)")
    ax.scatter(plot["proportion_weighted_conditional"], y, marker="x", color="#b24a3b", label="Ponderado condicional")
    ax.set_yticks(y, labels)
    ax.set_xlabel("Proporção de comparações pós-âncora")
    ax.set_xlim(left=0)
    ax.grid(axis="x", alpha=0.25)
    ax.legend(loc="lower right")
    save_figure(fig, prevalence_figure_path)

    scenario_plot = sensitivity.loc[
        sensitivity["strict_events"].add(sensitivity["broad_events"]).gt(0)
    ].sort_values("jaccard_strict_broad")
    fig, ax = plt.subplots(figsize=(9, max(4, 0.4 * len(scenario_plot))))
    ax.barh(
        scenario_plot["outcome_base"].str.replace("_", " "),
        scenario_plot["jaccard_strict_broad"],
        color="#5f8f6f",
    )
    ax.set_xlabel("Jaccard entre eventos estritos e amplos")
    ax.set_xlim(0, 1)
    ax.grid(axis="x", alpha=0.25)
    save_figure(fig, sensitivity_figure_path)

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(p) for p in input_paths.values()]
    manifest["results"] = {
        "nonzero_outcomes": len(prevalence_table),
        "descriptive_pattern_rows": len(patterns),
        "model_decision_rows": len(diagnostics),
        "figures": 2,
    }
    manifest["limitations"] = [
        "The weighted points are conditional estimates and the plotted Wilson intervals are unweighted.",
        "The descriptive-pattern table is unadjusted and not multiplicity-corrected.",
        "Figures visualize automated candidates, not validated behavior or causal effects.",
    ]
    manifest["outputs"] = [file_record(p) for p in outputs[:-1]]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
