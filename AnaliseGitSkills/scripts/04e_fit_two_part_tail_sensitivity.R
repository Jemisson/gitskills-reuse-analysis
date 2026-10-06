#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(sandwich)
  library(lmtest)
})

set.seed(2026)

args <- commandArgs(trailingOnly = TRUE)

input_file <- if (length(args) >= 1) args[1] else
  "outputs/rq1/models_r_test/hurdle_sample_100k.csv"

output_dir <- if (length(args) >= 2) args[2] else
  "outputs/rq1/models_r_test/two_part_robust"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

cat("Lendo amostra:\n", input_file, "\n\n")
dados <- fread(input_file)

limite_cauda <- as.numeric(
  quantile(
    dados$extra_reuse[dados$extra_reuse > 0],
    probs = 0.995,
    names = FALSE
  )
)

valores_alterados <- sum(dados$extra_reuse > limite_cauda)
dados[extra_reuse > limite_cauda, extra_reuse := limite_cauda]

cat("Limite P99,5 da contagem positiva:", limite_cauda, "\n")
cat("Valores winsorizados:", valores_alterados, "\n\n")

dados[, location_class := relevel(
  factor(location_class),
  ref = "canonical"
)]

dados[, repo_language_group := relevel(
  factor(repo_language_group),
  ref = "Unknown"
)]

preditores <- c(
  "location_class",
  "repo_language_group",
  "z_log_text_length",
  "z_log_description_length",
  "z_readability_flesch_english",
  "z_log_url_count",
  "z_log_code_block_count",
  "z_log_heading_count",
  "z_log_list_item_count",
  "has_scripts",
  "has_references",
  "z_log_sibling_count",
  "z_log_repo_stars",
  "z_log_repo_age_days",
  "z_log_repo_inactivity_days",
  "composition_truncated"
)

formula_logistica <- reformulate(
  preditores,
  response = "is_reused"
)

formula_contagem <- reformulate(
  preditores,
  response = "extra_reuse"
)

cat("Registros totais:", nrow(dados), "\n")
cat("Registros reutilizados:", sum(dados$is_reused == 1), "\n\n")

cat("Parte 1: ajustando regressão logística...\n")

modelo_logistico <- glm(
  formula = formula_logistica,
  data = dados,
  family = binomial(link = "logit"),
  model = TRUE,
  x = TRUE,
  y = TRUE
)

vcov_logistica <- vcovCL(
  modelo_logistico,
  cluster = dados$representative_repository,
  type = "HC1"
)
teste_logistica <- coeftest(
  modelo_logistico,
  vcov. = vcov_logistica
)

cat("Parte 2: ajustando PPML nos registros reutilizados...\n")

dados_positivos <- dados[extra_reuse > 0]

modelo_ppml <- glm(
  formula = formula_contagem,
  data = dados_positivos,
  family = poisson(link = "log"),
  model = TRUE,
  x = TRUE,
  y = TRUE
)

vcov_ppml <- vcovCL(
  modelo_ppml,
  cluster = dados_positivos$representative_repository,
  type = "HC1"
)
teste_ppml <- coeftest(
  modelo_ppml,
  vcov. = vcov_ppml
)

extrair_coeficientes <- function(teste, componente, medida) {
  resultado <- data.table(
    component = componente,
    term = rownames(teste),
    coefficient = teste[, 1],
    standard_error = teste[, 2],
    statistic = teste[, 3],
    p_value = teste[, 4]
  )

  resultado[, confidence_low :=
              coefficient - 1.96 * standard_error]

  resultado[, confidence_high :=
              coefficient + 1.96 * standard_error]

  resultado[, effect_measure := medida]
  resultado[, effect_ratio := exp(coefficient)]
  resultado[, effect_ratio_low := exp(confidence_low)]
  resultado[, effect_ratio_high := exp(confidence_high)]

  resultado
}

coef_logistica <- extrair_coeficientes(
  teste_logistica,
  "reuse_probability",
  "odds_ratio"
)

coef_ppml <- extrair_coeficientes(
  teste_ppml,
  "positive_reuse_intensity",
  "conditional_mean_ratio"
)

coeficientes <- rbind(
  coef_logistica,
  coef_ppml,
  use.names = TRUE
)

fwrite(
  coeficientes,
  file.path(output_dir, "two_part_coefficients_cluster_robust.csv")
)

dispersao_pearson <- sum(
  residuals(modelo_ppml, type = "pearson")^2
) / df.residual(modelo_ppml)

metricas <- data.table(
  metric = c(
    "total_records",
    "positive_records",
    "positive_mean",
    "positive_variance",
    "logistic_converged",
    "ppml_converged",
    "logistic_log_likelihood",
    "logistic_aic",
    "ppml_log_likelihood",
    "ppml_aic",
    "ppml_pearson_dispersion"
  ),
  value = c(
    nrow(dados),
    nrow(dados_positivos),
    mean(dados_positivos$extra_reuse),
    var(dados_positivos$extra_reuse),
    as.integer(modelo_logistico$converged),
    as.integer(modelo_ppml$converged),
    as.numeric(logLik(modelo_logistico)),
    AIC(modelo_logistico),
    as.numeric(logLik(modelo_ppml)),
    AIC(modelo_ppml),
    dispersao_pearson
  )
)

fwrite(
  metricas,
  file.path(output_dir, "two_part_model_metrics.csv")
)

writeLines(
  capture.output(summary(modelo_logistico)),
  file.path(output_dir, "logistic_summary.txt")
)

writeLines(
  capture.output(summary(modelo_ppml)),
  file.path(output_dir, "ppml_summary.txt")
)

saveRDS(
  modelo_logistico,
  file.path(output_dir, "logistic_model.rds")
)

saveRDS(
  modelo_ppml,
  file.path(output_dir, "ppml_model.rds")
)

cat("\nResultados principais:\n")
print(metricas)

cat(
  "\nArquivos gerados em:\n",
  normalizePath(output_dir),
  "\n"
)
