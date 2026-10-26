#!/usr/bin/env python3

"""Apply Benjamini-Hochberg within each RQ1 model component."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "outputs"
    / "rq1"
    / "models_full"
    / "two_part_clustered"
    / "two_part_coefficients_cluster_robust.csv"
)
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq1" / "reproduced_fdr"


def benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    values = p_values.to_numpy(dtype=float)
    if np.any(~np.isfinite(values)) or np.any((values < 0) | (values > 1)):
        raise ValueError("p-values devem ser finitos e pertencer a [0, 1]")
    order = np.argsort(values, kind="stable")
    ranked = values[order]
    adjusted_ranked = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted_ranked = np.minimum.accumulate(adjusted_ranked[::-1])[::-1]
    adjusted = np.empty_like(adjusted_ranked)
    adjusted[order] = np.minimum(adjusted_ranked, 1.0)
    return pd.Series(adjusted, index=p_values.index)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 < args.alpha < 1:
        raise ValueError("--alpha deve estar entre 0 e 1")

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_path = output_dir / "two_part_coefficients_cluster_robust_fdr.csv"
    manifest_path = output_dir / "fdr_manifest.json"
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([output_path, manifest_path], args.overwrite)

    frame = pd.read_csv(input_path)
    required = {"component", "term", "p_value"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    if frame.duplicated(["component", "term"]).any():
        raise ValueError("Há pares component/term duplicados")

    frame["q_value_bh"] = frame.groupby("component", sort=False)[
        "p_value"
    ].transform(benjamini_hochberg)
    frame["significant_fdr_05"] = frame["q_value_bh"] < args.alpha

    temporary = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    try:
        frame.to_csv(temporary, index=False)
        temporary.replace(output_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["input"] = file_record(input_path)
    manifest["method"] = {
        "name": "Benjamini-Hochberg",
        "family": "within each component",
        "alpha": args.alpha,
    }
    manifest["components"] = {
        str(component): {
            "tests": len(group),
            "significant": int(group["significant_fdr_05"].sum()),
        }
        for component, group in frame.groupby("component", sort=True)
    }
    manifest["outputs"] = [file_record(output_path)]
    atomic_json(manifest_path, manifest)
    print(manifest["components"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
