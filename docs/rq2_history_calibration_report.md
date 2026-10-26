# Relatório da calibração estratificada de história — RQ2

**Data:** 26 de outubro de 2026  
**Estado:** calibração técnica; não constitui resultado substantivo da RQ2.

## O que foi verificado

- O frame técnico elegível contém 603 repositórios classificados como acessíveis em ambas as sondagens anteriores, 997 ocorrências e 51 âncoras nos 11 estratos do piloto.
- A seleção usou seed `20261026`, ranking SHA-256 dentro de cada estrato, alocação round-robin de uma vaga por estrato e deduplicação por repositório.
- Foram selecionados 11 repositórios únicos e 14 ocorrências, cobrindo os 11 estratos.
- A repetição reproduziu exatamente os CSVs de repositórios, ocorrências e cobertura (SHA-256 iniciados por `77769072`, `29ba7b96` e `9cf426dc`).
- O coletor recuperou 11/11 repositórios e processou 14/14 ocorrências em 41,3 segundos. O cache final da primeira execução ocupou 238.312.796 bytes.
- Os 14 blobs-âncora estavam disponíveis, os 14 históricos eram não vazios e os 14 paths no HEAD correspondiam ao hash-âncora.
- Uma repetição via cache produziu `history_recovery_summary.csv` idêntico por SHA-256: `1689df85ab8feb5a576f7512fbb68005477e0be2450aed02da31e590ae34ada4`.
- A extração revisada produziu 35 comparações de pais em 26 commits: 26 mudanças, seis contextos com blob inalterado e três contextos em que o path não existia nos dois lados.
- Doze comparações pertencem a commits com múltiplos pais. Não houve seleção ambígua nem comparação não resolvida.
- A repetição do extrator produziu CSV idêntico por SHA-256: `f9e1dd7fa261527651488e24f09d19b649b5ab825300eebd6edacc4dfe1e8e90`.
- O classificador estrutural validou os hashes dos 26 diffs, classificou todos sem falha e preservou 4.483 linhas de evidência.
- As contagens estruturadas reconciliaram exatamente 4.252 linhas adicionadas e 231 removidas do Git.
- A repetição independente reproduziu exatamente eventos, evidências e contagens agregadas (`0a04af31…`, `977df687…`, `377b4c1c…`).

## O que foi apenas documentado

- A interseção das duas sondagens foi usada como frame operacional para evitar reposição oportunista durante a coleta.
- A ordenação por nome no coletor define apenas a ordem de execução; a seleção anterior foi estratificada e pseudoaleatória.
- Os limites executados foram 400 MB por repositório, 1,5 GB globais, 20 minutos globais, 180 segundos por clone e 60 segundos por operação Git.
- Os unified diffs e históricos brutos são artefatos regeneráveis locais; os CSVs registram seus paths e hashes.

## O que está planejado

1. implementar regras RQ3 estritas/amplas para comandos, acesso externo e executáveis;
2. recuperar e comparar siblings quando disponíveis;
3. ampliar fixtures para renames com edição, links de referência e falhas de encoding/parser;
4. usar a calibração para estimar custo e preparar, mas não substituir, a amostra confirmatória.

## O que permanece incerto

- A taxa de recuperação na população: 11/11 e 14/14 não são estimativas populacionais.
- O viés introduzido por condicionar a seleção a duas sondagens anônimas instáveis.
- A cobertura de branches não alcançáveis pelo HEAD e de objetos ausentes no clone parcial.
- A interpretação de merges complexos, renames com edição e paths divergentes entre pais.
- Qualquer ancestralidade ou direção de propagação entre repositórios.

## Artefatos rastreáveis

- seleção: `scripts/11_select_rq2_history_calibration.py`;
- manifesto de seleção: `outputs/rq2/history_calibration_sample/selection_manifest.json`;
- lista selecionada: `outputs/rq2/history_calibration_sample/selected_repositories.csv`;
- cobertura: `outputs/rq2/history_calibration_sample/stratum_coverage.csv`;
- coleta repetida/corrigida: `outputs/rq2/history_calibration_20261026_v2/`;
- eventos de diff: `outputs/rq2/diff_calibration_20261026_v2/diff_events.csv`;
- manifesto de diff: `outputs/rq2/diff_calibration_20261026_v2/diff_manifest.json`.
- classificação estrutural: `outputs/rq2/structured_diff_calibration_v3/`;
- relatório específico: [rq2_structured_diff_report.md](rq2_structured_diff_report.md).

## Critério de conclusão desta etapa

A calibração técnica está concluída porque seleção, orçamento, coleta, repetição e diffs estão ligados por manifests e checksums. R2.03 permanece parcial cientificamente até haver protocolo de não resposta e amostra apropriada para inferência; R2.11 permanece parcial até a classificação estrutural e sua validação automatizada. Não haverá validação humana independente.
