#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.discrete.truncated_model import (
    TruncatedLFNegativeBinomialP,
)


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = (
    ROOT
    / "outputs"
    / "rq1"
    / "rq1_model_data_with_repo.parquet"
)

DEFAULT_OUTPUT_DIR = (
    ROOT / "outputs" / "rq1" / "models"
)

RHS_FORMULA = """
    z_log_text_length
    + z_log_description_length
    + z_readability_flesch_english
    + z_log_url_count
    + z_log_code_block_count
    + z_log_heading_count
    + z_log_list_item_count
    + has_scripts
    + has_references
    + z_log_sibling_count
    + z_log_repo_stars
    + z_log_repo_age_days
    + z_log_repo_inactivity_days
    + composition_truncated
    + C(location_class, Treatment(reference='canonical'))
    + C(repo_language_group, Treatment(reference='Unknown'))
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ajusta o hurdle model da RQ1."
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Amostra aleatória utilizada somente para testes.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
    )

    return parser.parse_args()


def coefficient_table(
    result,
    ratio_name,
):
    confidence = result.conf_int()

    table = pd.DataFrame(
        {
            "term": result.params.index,
            "coefficient": result.params.values,
            "standard_error": result.bse.values,
            "p_value": result.pvalues.values,
            "ci_95_lower": confidence.iloc[:, 0].values,
            "ci_95_upper": confidence.iloc[:, 1].values,
        }
    )

    safe_coefficient = np.clip(
        table["coefficient"],
        -700,
        700,
    )
    safe_lower = np.clip(
        table["ci_95_lower"],
        -700,
        700,
    )
    safe_upper = np.clip(
        table["ci_95_upper"],
        -700,
        700,
    )

    table[ratio_name] = np.exp(safe_coefficient)
    table[f"{ratio_name}_ci_95_lower"] = np.exp(
        safe_lower
    )
    table[f"{ratio_name}_ci_95_upper"] = np.exp(
        safe_upper
    )

    dispersion_mask = table["term"].str.lower().isin(
        ["alpha", "lnalpha"]
    )

    table.loc[
        dispersion_mask,
        [
            ratio_name,
            f"{ratio_name}_ci_95_lower",
            f"{ratio_name}_ci_95_upper",
        ],
    ] = np.nan

    return table


def save_text(path: Path, content: str):
    path.write_text(
        content,
        encoding="utf-8",
    )


def main():
    args = parse_args()

    input_file = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"Lendo dataset: {input_file}")

    df = pd.read_parquet(input_file)

    if args.sample_size is not None:
        sample_size = min(
            args.sample_size,
            len(df),
        )

        df = df.sample(
            n=sample_size,
            random_state=args.seed,
        ).copy()

        print(
            f"Amostra de teste: {len(df):,} registros"
        )
    else:
        print(
            f"População do modelo: {len(df):,} registros"
        )

    logistic_formula = (
        "is_reused ~ " + RHS_FORMULA
    )

    print("\nAjustando regressão logística...")

    logistic_model = smf.glm(
        formula=logistic_formula,
        data=df,
        family=sm.families.Binomial(),
    )

    logistic_result = logistic_model.fit(
        cov_type="HC1",
        maxiter=100,
    )

    logistic_table = coefficient_table(
        logistic_result,
        "odds_ratio",
    )

    logistic_table.to_csv(
        output_dir / "logistic_coefficients.csv",
        index=False,
    )

    save_text(
        output_dir / "logistic_summary.txt",
        logistic_result.summary().as_text(),
    )

    reused = df.loc[
        df["extra_reuse"] > 0
    ].copy()

    print(
        "\nRegistros reutilizados para a "
        f"parte de contagem: {len(reused):,}"
    )

    count_formula = (
        "extra_reuse ~ " + RHS_FORMULA
    )

    print(
        "Construindo matriz da binomial "
        "negativa truncada..."
    )

    count_y, count_x = patsy.dmatrices(
        count_formula,
        data=reused,
        return_type="dataframe",
    )

    count_y = count_y.iloc[:, 0].astype(int)

    if (count_y <= 0).any():
        raise ValueError(
            "A variável da parte truncada contém zeros."
        )

    print(
        "Ajustando binomial negativa "
        "truncada em zero..."
    )

    print(
        "Estimando parâmetros iniciais com "
        "binomial negativa não truncada..."
    )

    initial_count_model = sm.NegativeBinomial(
        count_y,
        count_x,
    )

    initial_count_result = initial_count_model.fit(
        method="lbfgs",
        maxiter=500,
        disp=False,
    )

    initial_converged = bool(
        initial_count_result.mle_retvals.get(
            "converged",
            False,
        )
    )

    print(
        "Modelo inicial convergiu: "
        f"{initial_converged}"
    )

    count_model = TruncatedLFNegativeBinomialP(
        count_y,
        count_x,
        truncation=0,
        p=2,
    )

    count_result = count_model.fit(
        start_params=initial_count_result.params,
        method="lbfgs",
        maxiter=1000,
        disp=True,
        cov_type="HC1",
    )

    count_table = coefficient_table(
        count_result,
        "incidence_rate_ratio",
    )

    count_table.to_csv(
        output_dir / "truncated_nb_coefficients.csv",
        index=False,
    )

    save_text(
        output_dir / "truncated_nb_summary.txt",
        count_result.summary().as_text(),
    )

    logistic_converged = bool(
        getattr(logistic_result, "converged", True)
    )

    count_converged = bool(
        count_result.mle_retvals.get(
            "converged",
            False,
        )
    )

    metadata = {
        "total_model_records": int(len(df)),
        "unique_representative_repositories": int(
            df[
                "representative_repository"
            ].nunique()
        ),
        "reused_records": int(len(reused)),
        "reuse_percentage": float(
            100.0 * df["is_reused"].mean()
        ),
        "logistic_converged": logistic_converged,
        "logistic_aic": float(
            logistic_result.aic
        ),
        "logistic_deviance": float(
            logistic_result.deviance
        ),
        "logistic_null_deviance": float(
            logistic_result.null_deviance
        ),
        "logistic_deviance_explained": float(
            1.0
            - logistic_result.deviance
            / logistic_result.null_deviance
        ),
        "count_converged": count_converged,
        "count_aic": float(count_result.aic),
        "count_log_likelihood": float(
            count_result.llf
        ),
        "positive_count_mean": float(
            reused["extra_reuse"].mean()
        ),
        "positive_count_variance": float(
            reused["extra_reuse"].var()
        ),
        "covariance_type": "HC1",
        "logistic_formula": logistic_formula,
        "count_formula": count_formula,
        "sample_size_argument": args.sample_size,
        "random_seed": args.seed,
    }

    with (
        output_dir / "model_metadata.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as output:
        json.dump(
            metadata,
            output,
            ensure_ascii=False,
            indent=2,
        )

    print("\nResultados:")
    print(
        f"Logística convergiu: "
        f"{logistic_converged}"
    )
    print(
        f"Binomial negativa convergiu: "
        f"{count_converged}"
    )
    print(
        "Média da contagem positiva: "
        f"{metadata['positive_count_mean']:.4f}"
    )
    print(
        "Variância da contagem positiva: "
        f"{metadata['positive_count_variance']:.4f}"
    )
    print(f"Arquivos salvos em: {output_dir}")


if __name__ == "__main__":
    main()
