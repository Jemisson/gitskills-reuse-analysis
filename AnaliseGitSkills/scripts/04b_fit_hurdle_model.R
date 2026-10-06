#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(pscl)
  library(sandwich)
  library(lmtest)
})

set.seed(2026)

input_file <- "outputs/rq1/models_r_test/hurdle_sample_100k.csv"
output_dir <- "outputs/rq1/models_r_test"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

cat("Lendo amostra:\n", input_file, "\n\n")
dados <- fread(input_file)

dados[, location_class := relevel(
  factor(location_class),
  ref = "canonical"
)]

dados[, repo_language_group := relevel(
  factor(repo_language_group),
  ref = "Unknown"
)]

formula_modelo <- extra_reuse ~
  location_class +
  repo_language_group +
  z_log_text_length +
  z_log_description_length +
  z_readability_flesch_english +
  z_log_url_count +
  z_log_code_block_count +
  z_log_heading_count +
  z_log_list_item_count +
  has_scripts +
  has_references +
  z_log_sibling_count +
  z_log_repo_stars +
  z_log_repo_age_days +
  z_log_repo_inactivity_days +
  composition_truncated

cat("Registros totais:", nrow(dados), "\n")
cat("Registros com extra_reuse > 0:",
    sum(dados$extra_reuse > 0), "\n\n")

cat("Ajustando modelo hurdle logit + binomial negativa truncada...\n")

modelo <- hurdle(
  formula = formula_modelo,
  data = dados,
  dist = "negbin",
  zero.dist = "binomial",
  link = "logit",
  method = "BFGS",
  maxit = 1000,
  x = TRUE,
  y = TRUE,
  model = TRUE
)

cat("Modelo ajustado. Calculando erros-padrão robustos HC1...\n")

vcov_robusta <- sandwich(modelo, meat. = function(x, ...) meat(x, adjust = TRUE))
teste_robusto <- coeftest(modelo, vcov. = vcov_robusta)

coeficientes <- data.table(
  term = rownames(teste_robusto),
  coefficient = teste_robusto[, 1],
  standard_error = teste_robusto[, 2],
  statistic = teste_robusto[, 3],
  p_value = teste_robusto[, 4]
)

coeficientes[, confidence_low := coefficient - 1.96 * standard_error]
coeficientes[, confidence_high := coefficient + 1.96 * standard_error]
coeficientes[, effect_ratio := exp(coefficient)]
coeficientes[, effect_ratio_low := exp(confidence_low)]
coeficientes[, effect_ratio_high := exp(confidence_high)]

fwrite(
  coeficientes,
  file.path(output_dir, "hurdle_coefficients_robust.csv")
)

captura_resumo <- capture.output(summary(modelo))
writeLines(
  captura_resumo,
  file.path(output_dir, "hurdle_summary.txt")
)

theta <- as.numeric(modelo$theta)
alpha_equivalente <- 1 / theta

convergencia_count <- modelo$optim$count$convergence
convergencia_zero <- modelo$optim$zero$convergence

metricas <- data.table(
  metric = c(
    "total_records",
    "positive_records",
    "positive_mean",
    "positive_variance",
    "log_likelihood",
    "aic",
    "theta",
    "statsmodels_alpha_equivalent",
    "count_convergence_code",
    "zero_convergence_code"
  ),
  value = c(
    nrow(dados),
    sum(dados$extra_reuse > 0),
    mean(dados$extra_reuse[dados$extra_reuse > 0]),
    var(dados$extra_reuse[dados$extra_reuse > 0]),
    as.numeric(logLik(modelo)),
    AIC(modelo),
    theta,
    alpha_equivalente,
    convergencia_count,
    convergencia_zero
  )
)

fwrite(
  metricas,
  file.path(output_dir, "hurdle_model_metrics.csv")
)

saveRDS(
  modelo,
  file.path(output_dir, "hurdle_model.rds")
)

cat("\nResultados principais:\n")
print(metricas)

cat("\nArquivos gerados em:\n", normalizePath(output_dir), "\n")
