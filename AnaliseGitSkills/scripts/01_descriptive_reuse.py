#!/usr/bin/env python3

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "outputs" / "rq1" / "reuse_by_content.csv"
OUTPUT_DIR = ROOT / "outputs" / "rq1"


def gini(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=np.float64)

    if len(values) == 0 or np.any(values < 0):
        return float("nan")

    total = values.sum()

    if total == 0:
        return 0.0

    ordered = np.sort(values)
    positions = np.arange(1, len(ordered) + 1)

    return float(
        (2.0 * np.dot(positions, ordered) / (len(ordered) * total))
        - ((len(ordered) + 1.0) / len(ordered))
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Lendo: {INPUT_FILE}")

    df = pd.read_csv(
        INPUT_FILE,
        dtype={
            "file_sha": "string",
            "occurrence_count": "int64",
            "reuse_count": "int64",
        },
    )

    required_columns = {
        "file_sha",
        "occurrence_count",
        "reuse_count",
    }

    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        raise ValueError(
            f"Colunas ausentes: {sorted(missing_columns)}"
        )

    if df["file_sha"].isna().any():
        raise ValueError("Foram encontrados hashes ausentes.")

    if df["file_sha"].duplicated().any():
        raise ValueError("Foram encontrados hashes duplicados.")

    if (df["occurrence_count"] < 1).any():
        raise ValueError("Há occurrence_count menor que 1.")

    if (df["reuse_count"] < 1).any():
        raise ValueError("Há reuse_count menor que 1.")

    if (df["reuse_count"] > df["occurrence_count"]).any():
        raise ValueError(
            "Há reuse_count maior que occurrence_count."
        )

    reuse = df["reuse_count"].to_numpy(dtype=np.int64)
    occurrences = df["occurrence_count"].to_numpy(dtype=np.int64)

    total_contents = len(df)
    unique_contents = int(np.sum(reuse == 1))
    reused_contents = int(np.sum(reuse > 1))

    total_repository_placements = int(reuse.sum())
    total_occurrences = int(occurrences.sum())
    extra_reuse = int(np.maximum(reuse - 1, 0).sum())

    percent_reused = 100.0 * reused_contents / total_contents
    percent_extra_placements = (
        100.0 * extra_reuse / total_repository_placements
    )

    percentile_levels = [
        50,
        75,
        90,
        95,
        99,
        99.5,
        99.9,
    ]

    percentile_values = np.percentile(
        reuse,
        percentile_levels,
        method="linear",
    )

    percentiles = {
        f"p{str(level).replace('.', '_')}": float(value)
        for level, value in zip(
            percentile_levels,
            percentile_values,
        )
    }

    summary = {
        "total_contents": total_contents,
        "unique_contents": unique_contents,
        "reused_contents": reused_contents,
        "percent_reused": round(percent_reused, 6),
        "total_occurrences": total_occurrences,
        "total_repository_placements": total_repository_placements,
        "extra_reuse": extra_reuse,
        "percent_extra_repository_placements": round(
            percent_extra_placements,
            6,
        ),
        "mean_reuse": float(np.mean(reuse)),
        "median_reuse": float(np.median(reuse)),
        "standard_deviation_reuse": float(np.std(reuse)),
        "maximum_reuse": int(np.max(reuse)),
        "gini_reuse": gini(reuse),
        **percentiles,
    }

    with open(
        OUTPUT_DIR / "descriptive_summary.json",
        "w",
        encoding="utf-8",
    ) as output:
        json.dump(
            summary,
            output,
            ensure_ascii=False,
            indent=2,
        )

    pd.DataFrame(
        [
            {"metric": metric, "value": value}
            for metric, value in summary.items()
        ]
    ).to_csv(
        OUTPUT_DIR / "descriptive_summary.csv",
        index=False,
    )

    pd.DataFrame(
        {
            "percentile": percentile_levels,
            "reuse_count": percentile_values,
        }
    ).to_csv(
        OUTPUT_DIR / "reuse_percentiles.csv",
        index=False,
    )

    labels = [
        "1",
        "2",
        "3-5",
        "6-10",
        "11-50",
        "51-100",
        "Mais de 100",
    ]

    categories = pd.cut(
        df["reuse_count"],
        bins=[0, 1, 2, 5, 10, 50, 100, np.inf],
        labels=labels,
        include_lowest=True,
        right=True,
    )

    bin_counts = categories.value_counts(sort=False)

    bins_df = pd.DataFrame(
        {
            "range": labels,
            "count": bin_counts.to_numpy(),
        }
    )

    bins_df["percentage"] = (
        100.0 * bins_df["count"] / total_contents
    )

    bins_df.to_csv(
        OUTPUT_DIR / "reuse_ranges.csv",
        index=False,
    )

    ordered_reuse = np.sort(reuse)[::-1]
    ordered_extra = np.sort(
        np.maximum(reuse - 1, 0)
    )[::-1]

    concentration_rows = []

    for requested_n in [10, 100, 1000]:
        n = min(requested_n, total_contents)

        concentration_rows.append(
            {
                "top_n": requested_n,
                "repository_placement_share_percent": (
                    100.0
                    * ordered_reuse[:n].sum()
                    / total_repository_placements
                ),
                "extra_reuse_share_percent": (
                    100.0
                    * ordered_extra[:n].sum()
                    / extra_reuse
                    if extra_reuse > 0
                    else 0.0
                ),
            }
        )

    pd.DataFrame(concentration_rows).to_csv(
        OUTPUT_DIR / "reuse_concentration.csv",
        index=False,
    )

    df.nlargest(
        100,
        columns=["reuse_count", "occurrence_count"],
    ).to_csv(
        OUTPUT_DIR / "top_100_reused.csv",
        index=False,
    )

    plt.figure(figsize=(10, 6))
    plt.bar(
        bins_df["range"],
        bins_df["percentage"],
        color="#2468A2",
    )
    plt.xlabel("Número de repositórios")
    plt.ylabel("Percentual de conteúdos")
    plt.title("Distribuição do reúso de Agent Skills")
    plt.xticks(rotation=25)
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "reuse_ranges.png",
        dpi=300,
    )
    plt.close()

    frequencies = (
        df["reuse_count"]
        .value_counts()
        .sort_index()
    )

    ccdf = (
        frequencies.iloc[::-1]
        .cumsum()
        .iloc[::-1]
        / total_contents
    )

    plt.figure(figsize=(10, 6))
    plt.loglog(
        frequencies.index,
        ccdf.values,
        marker=".",
        linestyle="none",
        color="#9C2F2F",
        markersize=5,
    )
    plt.xlabel("Número de repositórios por conteúdo")
    plt.ylabel("P(Reuse ≥ x)")
    plt.title("Distribuição de cauda do reúso")
    plt.grid(True, which="both", alpha=0.25)
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "reuse_ccdf_loglog.png",
        dpi=300,
    )
    plt.close()

    print("\nResumo da análise:")
    for metric, value in summary.items():
        print(f"{metric}: {value}")

    print("\nArquivos gerados em:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
