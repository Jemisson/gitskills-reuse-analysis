#!/usr/bin/env python3

"""Generate reproducible RQ3 boxplots from post-anchor event-level data."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
DEFAULT_INPUT = ROOT / "outputs/rq3/association_dataset_v2/rq3_association_events.csv"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "IEEE_Conference_Template/figures"
OPERATIONS = ["addition", "modification", "movement", "removal"]
COLORS = ["#4477AA", "#EE6677", "#228833", "#CCBB44"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def save_figure(fig: plt.Figure, path: Path, *, dpi: int | None = None) -> None:
    temporary = path.with_name(f".{path.stem}.{os.getpid()}.tmp{path.suffix}")
    options: dict[str, object] = {"bbox_inches": "tight"}
    if dpi is not None:
        options["dpi"] = dpi
    fig.savefig(temporary, **options)
    temporary.replace(path)


def add_boxplot(
    frame: pd.DataFrame,
    column: str,
    ylabel: str,
    output_stem: Path,
    rng: np.random.Generator,
) -> dict[str, int]:
    groups = [
        frame.loc[frame["change_operation"].eq(operation), column].dropna().to_numpy(dtype=float)
        for operation in OPERATIONS
    ]
    counts = {operation: int(len(values)) for operation, values in zip(OPERATIONS, groups)}
    if any(count == 0 for count in counts.values()):
        missing = [operation for operation, count in counts.items() if count == 0]
        raise ValueError(f"Operation groups without observations for {column}: {missing}")

    transformed = [np.log1p(values) for values in groups]
    fig, ax = plt.subplots(figsize=(3.45, 2.75))
    boxes = ax.boxplot(
        transformed,
        tick_labels=[f"{operation.capitalize()}\n(n={counts[operation]})" for operation in OPERATIONS],
        patch_artist=True,
        widths=0.58,
        whis=1.5,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 1.2},
        whiskerprops={"color": "#444444", "linewidth": 0.8},
        capprops={"color": "#444444", "linewidth": 0.8},
        boxprops={"edgecolor": "#333333", "linewidth": 0.8},
    )
    for patch, color in zip(boxes["boxes"], COLORS):
        patch.set_facecolor(color)
        patch.set_alpha(0.72)

    for position, (values, color) in enumerate(zip(transformed, COLORS), start=1):
        jitter = rng.uniform(-0.16, 0.16, size=len(values))
        ax.scatter(
            np.full(len(values), position) + jitter,
            values,
            s=9,
            facecolors="white",
            edgecolors=color,
            linewidths=0.55,
            alpha=0.8,
            zorder=3,
        )

    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", labelsize=6.8)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.grid(axis="y", color="#cccccc", linewidth=0.5, alpha=0.65)
    ax.set_axisbelow(True)
    fig.tight_layout()

    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    save_figure(fig, png_path, dpi=300)
    save_figure(fig, pdf_path)
    plt.close(fig)
    return counts


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input dataset not found: {input_path}")

    stems = {
        "changed_lines": output_dir / "boxplot_rq3_changed_lines_by_operation",
        "days_since_reference_version": output_dir / "boxplot_rq3_days_since_reference_version_by_operation",
    }
    figure_paths = [
        stem.with_suffix(suffix)
        for stem in stems.values()
        for suffix in (".png", ".pdf")
    ]
    manifest_path = output_dir / "rq3_boxplots_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([*figure_paths, manifest_path], args.overwrite)

    frame = pd.read_csv(input_path)
    required = {"diff_id", "repo_full_name", "change_operation", "diff_changed_lines", "days_since_anchor"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Required columns are missing: {missing}")
    if frame["diff_id"].duplicated().any():
        raise ValueError("The event-level input contains duplicate diff_id values")
    unexpected = sorted(set(frame["change_operation"].dropna()).difference(OPERATIONS))
    if unexpected:
        raise ValueError(f"Unexpected change_operation values: {unexpected}")

    rng = np.random.default_rng(args.seed)
    changed_counts = add_boxplot(
        frame,
        "diff_changed_lines",
        "log1p(changed lines)",
        stems["changed_lines"],
        rng,
    )
    days_counts = add_boxplot(
        frame,
        "days_since_anchor",
        "log1p(days since reference version)",
        stems["days_since_reference_version"],
        rng,
    )

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["analysis_version"] = "rq3-event-boxplots-v1.0"
    manifest["inputs"] = [file_record(input_path)]
    manifest["results"] = {
        "events": int(len(frame)),
        "repositories": int(frame["repo_full_name"].nunique()),
        "operation_counts_changed_lines": changed_counts,
        "operation_counts_days_since_reference_version": days_counts,
        "transform": "log1p",
        "boxplot_definition": "median, Q1/Q3, and whiskers at 1.5 IQR; individual observations overlaid with deterministic jitter",
    }
    manifest["limitations"] = [
        "The 75 comparisons are observations from a conditioned complete-case sample, not a GitHub-wide population.",
        "Events within repositories, occurrences, exact-content families, and merge commits are not statistically independent.",
        "Conventional boxplots are unweighted; sampling weights do not resolve selection bias or dependence.",
        "The log1p transform preserves zeros but changes the visual scale.",
    ]
    manifest["outputs"] = [file_record(path) for path in figure_paths]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
