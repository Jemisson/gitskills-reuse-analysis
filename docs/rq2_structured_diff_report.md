# Relatório da classificação estrutural de diffs — RQ2

**Data:** 26 de outubro de 2026  
**Classificador:** `rq2-structured-diff-v1.0`  
**Estado:** calibração técnica automatizada; não é estimativa populacional nem validação semântica externa.

## O que foi verificado

- Os 26 eventos de mudança da calibração foram processados sem falhas.
- Os hashes dos 26 unified diffs foram verificados antes da classificação.
- Foram preservadas 4.483 linhas de evidência: 4.252 adicionadas e 231 removidas.
- As contagens estruturadas são exatamente iguais ao churn do Git para todos os eventos.
- Operações observadas na calibração: 18 adições de arquivo, sete modificações e um movimento puro.
- A classificação cobre front matter, cabeçalhos, listas, cercas/blocos de código, código indentado, blockquotes, tabelas, parágrafos e linhas vazias.
- Escopos são candidatos operacionais: nome, descrição, outros metadados, instrução, exemplo, código/comando, URL/rede e referência.
- Vinte e dois eventos acionaram ao menos uma regra candidata de código/comando ou URL/rede.
- A reexecução independente reproduziu exatamente os três CSVs:
  - eventos: `0a04af31a6f0b4c5d5e8760a364b7ec634d3a5bf909beb699ef0b763dff350cb`;
  - evidências: `977df6877fce47e0225a8e5ea69b2d6a1b1f65ef237fb01342eaa32450031812`;
  - contagens: `377b4c1c7732eeb1daab107879548885574f177ac23b99b2e0db135c2082ff6e`.

## O que foi apenas documentado

- `instruction_candidate` identifica prosa/lista fora de seção de exemplos; não prova que o texto seja uma instrução executável.
- `command_code_candidate` identifica regiões de código ou código inline; não prova que contenham comando nem que tenham sido executadas.
- `network_url_candidate` identifica URL com esquema explícito; não prova acesso de rede.
- `behavior_relevance_candidate` é união operacional de candidatos de código/comando, rede/URL e, futuramente, scripts.
- O alinhamento estrutural usa os hunks produzidos pelo Git, não realinhamento textual independente.

## O que está planejado

1. ampliar fixtures e cenários de erro do classificador RQ3 já implementado;
2. aplicar o pipeline em amostra maior antes de qualquer estimativa destinada ao artigo;
3. calcular métricas RQ2/RQ3 somente com denominadores e escopo amostral explícitos.

## O que permanece incerto

- validade semântica externa dos escopos candidatos, pois não haverá referência humana independente;
- desempenho em documentos com Markdown malformado, encoding inválido ou construções aninhadas complexas;
- cobertura de movimentos internos de blocos em documentos também editados;
- prevalência populacional de qualquer categoria;
- relação entre evidência textual e comportamento efetivamente executado.

## Artefatos

- implementação: `scripts/12_classify_rq2_structured_diffs.py`;
- eventos: `outputs/rq2/structured_diff_calibration_v3/structured_diff_events.csv`;
- evidências atômicas: `outputs/rq2/structured_diff_calibration_v3/structured_diff_evidence.csv`;
- contagens agregadas: `outputs/rq2/structured_diff_calibration_v3/structured_diff_category_counts.csv`;
- manifesto: `outputs/rq2/structured_diff_calibration_v3/structured_diff_manifest.json`.

## Critério de conclusão desta etapa

A classificação estrutural da calibração está tecnicamente concluída: entradas, regras, evidências, agregações, testes e repetição estão rastreados. R2.11 permanece parcial no escopo total porque siblings/scripts, cenários estrito/amplo e aplicação a uma amostra apropriada para inferência ainda não foram executados.
