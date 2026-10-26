# Matriz de evidências para o artigo

**Finalidade:** ligar cada afirmação científica a dados, transformação, saída e verificação.  
**Estados:** VERIFICADO, DOCUMENTADO, PLANEJADO ou INCERTO.  
**Regra:** “arquivo presente” não implica “pipeline reproduzível”.

## RQ1 — evidência existente

| ID | Afirmação/elemento | Dados de origem | Transformação/modelo | Saída citável | Estado e observação |
|---|---|---|---|---|---|
| RQ1-E01 | População principal tem 1.586.188 conteúdos | SQLite `artifacts` | `00_build_rq1_inputs.py` e filtros de `02_extract_features.py` | manifesto, `descriptive_summary.csv`; Parquet local | VERIFICADO; entrada reproduzida com SHA-256 idêntico |
| RQ1-E02 | 254.078 (16,0182%) conteúdos são reutilizados | `reuse_by_content.csv` | `reuse_count > 1` | `descriptive_summary.csv` | VERIFICADO por recálculo |
| RQ1-E03 | 42,0639% das presenças são adicionais | `reuse_by_content.csv` | `sum(reuse-1)/sum(reuse)` | `descriptive_summary.csv` | VERIFICADO por recálculo |
| RQ1-E04 | Distribuição: faixas e percentis | `reuse_by_content.csv` | `01_descriptive_reuse.py` | `reuse_ranges.csv`, `reuse_percentiles.csv`, Figuras 1–2 | VERIFICADO |
| RQ1-E05 | Máximo 937 e Gini 0,3978 | `reuse_by_content.csv` | `01_descriptive_reuse.py` | `descriptive_summary.csv` | VERIFICADO |
| RQ1-E06 | Ranking de conteúdos mais reutilizados | CSV de reúso + metadados | junção não versionada integralmente | `top_100_reused_detailed.csv` | DOCUMENTADO/artefato presente; junção precisa ser reconstruída |
| RQ1-E07 | 1.584.628 linhas no modelo, 1.560 removidas | `rq1_features.parquet` | `03_prepare_model_data.py` | log, `model_missingness.csv` | VERIFICADO |
| RQ1-E08 | 218.408 repositórios representantes no modelo | modelo + CSV representante | `00_build_rq1_inputs.py`, `03b_add_representative_repository.py` | manifesto, Parquet/log local | VERIFICADO |
| RQ1-E09 | NB truncada foi degenerada | amostra de 100 mil | `04_fit_hurdle_model.py`, `04b_fit_hurdle_model.R` | métricas/resumos/logs locais | VERIFICADO nos artefatos; não usar coeficientes |
| RQ1-E10 | Modelo principal logístico + PPML convergiu | CSV do R | `04d_fit_two_part_clustered.R` | métricas, coeficientes e `.rds` locais | VERIFICADO computacionalmente; convergência não valida especificação |
| RQ1-E11 | Cinco efeitos principais FDR na probabilidade | coeficientes agrupados | `04f_apply_fdr.py`, BH separado por componente | `rq1_main_effects.csv` | VERIFICADO por reprodução |
| RQ1-E12 | Seis efeitos principais FDR na intensidade | coeficientes agrupados | `04f_apply_fdr.py`, BH separado por componente | `rq1_main_effects.csv` | VERIFICADO por reprodução |
| RQ1-E13 | Erros agrupados são mediana 10,95× HC1 | saídas HC1 e cluster | comparação não versionada | relatório | VERIFICADO por recálculo (10,946) |
| RQ1-E14 | 16 megarepositórios somam 183.623 linhas | dataset com representante | `03c_export_model_data_for_r.py`, filtro `>5000` | manifesto, CSV/local + relatório | VERIFICADO por reprodução |
| RQ1-E15 | 28 efeitos principais mantêm direção sem megarepositórios | coeficientes principal/sensibilidade | comparação | relatório/final | VERIFICADO por recálculo para 14 termos × 2 componentes |
| RQ1-E16 | 37 coeficientes de intensidade mantêm direção e significância na cauda | coeficientes principal/tail | `04e` + comparação | relatório | VERIFICADO com `p < 0,05`; explicitar critério, não confundir com FDR |
| RQ1-E17 | 71/74 coeficientes mantêm direção amostra/população | saídas HC1 | comparação não versionada | relatório | VERIFICADO por recálculo |
| RQ1-E18 | Associações não são causais | desenho observacional | regra interpretativa | texto do artigo | VERIFICADO como limitação obrigatória |
| RQ1-E19 | Representante não é origem | esquema/procedência | regra interpretativa | texto do artigo | VERIFICADO como limitação obrigatória |

## RQ1 — afirmações permitidas e proibidas

| Permitida | Não sustentada |
|---|---|
| “O mesmo conteúdo exato aparece em N repositórios.” | “N repositórios descendem do representante.” |
| “A característica X está associada a probabilidade/intensidade, controladas as covariáveis.” | “X faz uma skill se propagar.” |
| “O resultado foi robusto nos cenários testados.” | “O resultado é robusto a toda definição/população.” |
| “O contexto é o do repositório representante.” | “O contexto é o da origem/autoria.” |
| “A distribuição observada tem cauda longa.” | “A distribuição segue lei de potência”, sem teste específico. |

## RQ2 — evidências a produzir

| ID | Afirmação pretendida | Dados necessários | Procedimento | Saída mínima | Estado |
|---|---|---|---|---|---|
| RQ2-E01 | Cobertura e viés de recuperabilidade | frame + status de coleta | R2.01–R2.05 | manifests/tabela por estrato | INCERTO: frame e calibração nos 11 estratos verificados; seleção condicionada a sondagens instáveis e inadequada para estimar disponibilidade |
| RQ2-E02 | Relações genealógicas possuem confiança auditável | commits, blobs, proveniência | R2.06–R2.10 | tabela de evidências A–D | DOCUMENTADO; coleta e 35 comparações intrarrepositório verificadas em calibração técnica, mas genealogias inter-repositório não foram construídas |
| RQ2-E03 | Proporção estável/divergente | genealogias + janela/censura | R2.15 | tabela com denominadores/IC | PLANEJADO |
| RQ2-E04 | Tempo até primeira divergência | datas e censura | análise longitudinal | curva/tabela | PLANEJADO; viabilidade INCERTA |
| RQ2-E05 | Tipos/regiões de mudança sob regras operacionais | diffs estruturados + regras versionadas | R2.11–R2.14 | tabela/heatmap + cobertura/incerteza | PLANEJADO: diffs brutos existem, mas classificação estrutural automatizada ainda não existe |
| RQ2-E06 | Alcance e atraso da propagação de alteração | patch comparável + oportunidades | R2.15 | tabela com elegibilidade | PLANEJADO |
| RQ2-E07 | Consistência/inconsistência de alterações | adoções elegíveis e equivalência | codebook + análise | tabela por família/tipo | PLANEJADO |
| RQ2-E08 | Reprodutibilidade e estabilidade das classificações | fixtures + cenários estrito/amplo | R2.13–R2.14 | cobertura, falhas, incerteza e mudanças entre cenários | PLANEJADO; não haverá estimativa independente de validade semântica |
| RQ2-E09 | Sensibilidade à evidência e limiares | cenários A/A+B/A+B+C | R2.16 | matriz de robustez | PLANEJADO |

Nenhuma linha RQ2-E pode ser promovida a VERIFICADO apenas porque o diretório ou script correspondente passar a existir.

## RQ3 — evidências a produzir

| ID | Afirmação pretendida | Dados necessários | Procedimento | Saída mínima | Estado |
|---|---|---|---|---|---|
| RQ3-E01 | Prevalência operacional de adição/remoção de comandos | amostra probabilística + regras congeladas | R3.10–R3.15 | estimativa/IC + definição | PLANEJADO/EXPLORATÓRIO |
| RQ3-E02 | Prevalência de mudanças de acesso externo | idem | R3.10–R3.15 | estimativa/IC | PLANEJADO |
| RQ3-E03 | Prevalência operacional de mudanças em executáveis | histórico de siblings + regras congeladas | R3.07–R3.15 | estimativa/IC + definição | PLANEJADO/EXPLORATÓRIO |
| RQ3-E04 | Determinismo e cobertura por rótulo/direção | fixtures e casos de regressão | R3.11–R3.12 | checksums, cobertura, falhas e incerteza | PLANEJADO |
| RQ3-E05 | Estabilidade da automação | cenários estrito/amplo | R3.13 | transições de rótulo entre cenários | PLANEJADO; sem P/R/F1 por ausência de padrão-ouro |
| RQ3-E06 | Características associadas aos desfechos | covariáveis pré-evento | R3.14–R3.16 | razões de efeito/IC/FDR | PLANEJADO; modelo pode ser inviável |
| RQ3-E07 | Coocorrência entre categorias | rótulos multilabel | análise descritiva | tabela/UpSet | PLANEJADO |
| RQ3-E08 | Robustez a taxonomia/classificação/genealogia | cenários predefinidos | R3.17 | matriz de sensibilidade | PLANEJADO |

## Registro obrigatório por tabela e figura futura

Cada artefato do artigo deverá receber uma linha com:

| Campo | Conteúdo obrigatório |
|---|---|
| `artifact_id` | identificador estável, por exemplo `T-RQ2-03` |
| pergunta/claim IDs | quais evidências sustenta |
| população/amostra | frame, filtros, estratos, pesos e `n` |
| entrada | paths/URIs, versão e checksums |
| transformação | script, commit, configuração e seed |
| saída | path imutável e checksum |
| validação | testes, fixtures, invariantes, repetibilidade e sensibilidades |
| estado | verificado/documentado/planejado/incerto |
| limitações | cobertura, erro, ambiguidade e censura relevantes |

## Bloqueios atuais da matriz

1. Falta reexecutar os modelos R completos sob o novo manifesto global.
2. Logs históricos não são versionados e não têm checksums/comandos completos.
3. RQ2 possui frame, piloto, históricos e diffs em calibração estratificada não inferencial, mas ainda não possui genealogias inter-repositório nem classificações estruturais automatizadas.
4. Não haverá referência humana independente; validade semântica externa de RQ2/RQ3 permanecerá uma ameaça não quantificada.
5. Limiares genealógicos e tamanho amostral confirmatório dependem do piloto de história completa.
6. O nível de recuperabilidade de paths e históricos completos permanece desconhecido.

## Regra de promoção de estado

- PLANEJADO → DOCUMENTADO: protocolo/execução narrada, ainda sem verificação independente.
- DOCUMENTADO → VERIFICADO: entrada, código, configuração e saída ligados; invariantes e números recomputados.
- INCERTO somente sai desse estado após decisão registrada ou evidência empírica apropriada.
- Uma conclusão do artigo só poderá citar evidências VERIFICADAS; evidências DOCUMENTADAS podem aparecer apenas como procedência/limitação.
- Para classificações automatizadas, VERIFICADO significa reprodução computacional da regra declarada, não validade semântica externa.
