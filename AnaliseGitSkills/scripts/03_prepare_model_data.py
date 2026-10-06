#!/usr/bin/env python3

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "outputs" / "rq1" / "rq1_features.parquet"
OUTPUT_FILE = ROOT / "outputs" / "rq1" / "rq1_model_data.parquet"
PARAMETERS_FILE = ROOT / "outputs" / "rq1" / "transformation_parameters.csv"
MISSING_FILE = ROOT / "outputs" / "rq1" / "model_missingness.csv"

SNAPSHOT_DATE = pd.Timestamp(
    "2026-07-22T00:00:00Z"
)

REQUIRED_COLUMNS = [
    "file_sha",
    "reuse_count",
    "is_reused",
    "extra_reuse",
    "text_length",
    "description_length",
    "readability_flesch_english",
    "url_count",
    "code_block_count",
    "heading_count",
    "list_item_count",
    "sibling_count",
    "has_scripts",
    "has_references",
    "composition_truncated",
    "repo_stars",
    "repo_is_fork",
    "repo_language",
    "location_class",
    "repo_created_at",
    "repo_pushed_at",
]

LOG_VARIABLES = [
    "text_length",
    "description_length",
    "url_count",
    "code_block_count",
    "heading_count",
    "list_item_count",
    "sibling_count",
    "repo_stars",
    "repo_age_days",
    "repo_inactivity_days",
]


def winsorize_and_standardize(
    series: pd.Series,
    output_name: str,
):
    lower = float(series.quantile(0.005))
    upper = float(series.quantile(0.995))

    winsorized = series.clip(
        lower=lower,
        upper=upper,
    )

    mean = float(winsorized.mean())
    standard_deviation = float(
        winsorized.std(ddof=0)
    )

    if standard_deviation == 0:
        standardized = pd.Series(
            np.zeros(len(series)),
            index=series.index,
        )
    else:
        standardized = (
            winsorized - mean
        ) / standard_deviation

    parameters = {
        "variable": output_name,
        "lower_limit": lower,
        "upper_limit": upper,
        "mean_after_winsorization": mean,
        "standard_deviation": standard_deviation,
    }

    return standardized, parameters


def main():
    print(f"Lendo {INPUT_FILE}...")

    df = pd.read_parquet(
        INPUT_FILE,
        columns=REQUIRED_COLUMNS,
    )

    print(f"Registros originais: {len(df):,}")

    missingness = pd.DataFrame(
        {
            "variable": REQUIRED_COLUMNS,
            "missing_count": [
                int(df[column].isna().sum())
                for column in REQUIRED_COLUMNS
            ],
        }
    )

    missingness["missing_percentage"] = (
        100.0
        * missingness["missing_count"]
        / len(df)
    )

    missingness.to_csv(
        MISSING_FILE,
        index=False,
    )

    created_at = pd.to_datetime(
        df["repo_created_at"],
        utc=True,
        errors="coerce",
    )
    pushed_at = pd.to_datetime(
        df["repo_pushed_at"],
        utc=True,
        errors="coerce",
    )

    df["repo_age_days"] = (
        SNAPSHOT_DATE - created_at
    ).dt.total_seconds() / 86400.0

    df["repo_inactivity_days"] = (
        SNAPSHOT_DATE - pushed_at
    ).dt.total_seconds() / 86400.0

    df["repo_age_days"] = df[
        "repo_age_days"
    ].clip(lower=0)

    df["repo_inactivity_days"] = df[
        "repo_inactivity_days"
    ].clip(lower=0)

    complete_case_columns = [
        "sibling_count",
        "has_scripts",
        "has_references",
        "composition_truncated",
        "repo_stars",
        "repo_is_fork",
        "repo_age_days",
        "repo_inactivity_days",
    ]

    before_drop = len(df)

    df = df.dropna(
        subset=complete_case_columns
    ).copy()

    removed = before_drop - len(df)

    print(f"Registros removidos por ausência: {removed:,}")
    print(f"Registros no modelo principal: {len(df):,}")

    language_counts = (
        df["repo_language"]
        .value_counts()
    )

    main_languages = set(
        language_counts.head(20).index
    )

    df["repo_language_group"] = np.where(
        df["repo_language"].isin(main_languages),
        df["repo_language"],
        "Other",
    )

    parameter_rows = []

    for variable in LOG_VARIABLES:
        transformed = np.log1p(
            df[variable].astype(float)
        )

        output_name = f"z_log_{variable}"

        standardized, parameters = (
            winsorize_and_standardize(
                transformed,
                output_name,
            )
        )

        df[output_name] = standardized
        parameter_rows.append(parameters)

    readability_standardized, parameters = (
        winsorize_and_standardize(
            df[
                "readability_flesch_english"
            ].astype(float),
            "z_readability_flesch_english",
        )
    )

    df[
        "z_readability_flesch_english"
    ] = readability_standardized

    parameter_rows.append(parameters)

    model_columns = [
        "file_sha",
        "reuse_count",
        "is_reused",
        "extra_reuse",
        "has_scripts",
        "has_references",
        "composition_truncated",
        "repo_is_fork",
        "location_class",
        "repo_language_group",
        "z_log_text_length",
        "z_log_description_length",
        "z_log_url_count",
        "z_log_code_block_count",
        "z_log_heading_count",
        "z_log_list_item_count",
        "z_log_sibling_count",
        "z_log_repo_stars",
        "z_log_repo_age_days",
        "z_log_repo_inactivity_days",
        "z_readability_flesch_english",
    ]

    model_df = df[model_columns].copy()

    integer_columns = [
        "reuse_count",
        "is_reused",
        "extra_reuse",
        "has_scripts",
        "has_references",
        "composition_truncated",
        "repo_is_fork",
    ]

    for column in integer_columns:
        model_df[column] = model_df[
            column
        ].astype("int64")

    if model_df.isna().any().any():
        missing_after = (
            model_df.isna()
            .sum()
            .loc[lambda values: values > 0]
        )

        raise ValueError(
            "Valores ausentes após preparação:\n"
            f"{missing_after}"
        )

    if model_df["file_sha"].duplicated().any():
        raise ValueError(
            "Hashes duplicados no dataset do modelo."
        )

    model_df.to_parquet(
        OUTPUT_FILE,
        index=False,
        compression="zstd",
    )

    pd.DataFrame(parameter_rows).to_csv(
        PARAMETERS_FILE,
        index=False,
    )

    print(f"Dataset salvo em: {OUTPUT_FILE}")
    print(f"Parâmetros salvos em: {PARAMETERS_FILE}")
    print("Preparação concluída.")


if __name__ == "__main__":
    main()
