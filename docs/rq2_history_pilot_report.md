# Relatório técnico do piloto de recuperação de história — RQ2

**Data:** 16 de outubro de 2026  
**Estado:** diagnóstico técnico; não é resultado substantivo da RQ2.  
**Escopo:** três repositórios e sete ocorrências selecionados deterministicamente entre repositórios que responderam como acessíveis em duas sondagens anteriores.

## Objetivo

Validar, em escala mínima, se o coletor consegue:

1. reutilizar cache Git sem nova consulta de rede;
2. reconciliar o `file_sha` do snapshot com um blob Git;
3. localizar o path no HEAD atual;
4. recuperar commits associados ao path;
5. preservar merges e renomes sem linearização silenciosa;
6. produzir saídas idempotentes.
7. extrair diffs pai→filho sem converter similaridade em ancestralidade.

## O que foi verificado

- Fixtures locais cobrem adição, rename, mudanças em dois ramos, merge com dois pais e remoção.
- `git log --follow` isoladamente omitiu o merge na fixture.
- O coletor passou a unir evidência de `--follow` com `--full-history`, registrando `evidence_modes` por commit.
- Três clones bare parciais foram recuperados e armazenados em cache.
- Sete de sete `file_sha` foram encontrados como blobs nos repositórios recuperados.
- Seis de sete paths ainda apontavam para o hash-âncora no HEAD atual.
- Um path não existia mais no HEAD; seu histórico continha dois commits.
- Todas as sete ocorrências apresentaram pelo menos um commit recuperado.
- Uma segunda execução usando o mesmo cache gerou `history_recovery_summary.csv` e `repository_collection_status.csv` com SHA-256 idênticos aos da primeira execução corrigida.
- O extrator compara cada commit separadamente com cada pai, registra hashes dos blobs, status/path e churn, e mantém o unified diff bruto fora do Git.
- As sete ocorrências produziram oito comparações em quatro commits únicos, sem seleção ambígua ou evento não resolvido.
- Um rename puro foi registrado como continuidade de path com zero linha adicionada/removida; isso não implica ancestralidade entre repositórios.
- A repetição do extrator reproduziu `diff_events.csv` com SHA-256 `a30de929b5a0d28c205f82249e64ba796a61613b7d65061ed75b7c65fce96e0c`.
- Adição raiz, rename puro, remoção e suporte a múltiplos pais foram verificados em fixture local; o smoke externo não continha merge.

## O que foi apenas documentado

- Os três repositórios foram os primeiros em ordenação lexicográfica dentro da interseção de respostas acessíveis. Essa escolha testa software, não representa a população.
- Os históricos brutos ficam fora do Git e são referenciados por nomes relativos em `histories/`.
- O maior cache chegou a aproximadamente 163 MB depois da recuperação preguiçosa de blobs. Medir o tamanho apenas após o clone subestimava o custo; a medição foi movida para depois da inspeção das ocorrências.

## O que permanece incerto

- disponibilidade persistente dos demais repositórios;
- recuperação do path correspondente exatamente ao snapshot de julho de 2026;
- cobertura de branches não alcançáveis pelo HEAD/default;
- interpretação de merges complexos e múltiplos renomes;
- proporção real de paths removidos, divergentes ou sem histórico;
- custo de armazenamento e rede em escala;
- qualquer relação de ancestralidade entre repositórios.
- desempenho do extrator em merges reais, renames com edição e histórias não lineares complexas;
- validade de uma classificação semântica/estrutural de mudanças, ainda não implementada.

## Sondagem com cache e retries

A versão revisada da sondagem inclui:

- cache apenas de respostas acessíveis com HEAD conhecido;
- até três tentativas;
- backoff exponencial;
- jitter determinístico;
- limite global de requisições por segundo;
- classe `inconclusive_access_failure` para respostas anônimas ambíguas.

Um smoke test com 20 repositórios reutilizou 19 respostas do cache e repetiu três vezes a consulta restante, que continuou inconclusiva. O teste confirma o mecanismo, mas não valida ainda uma taxa de disponibilidade.

## Critério para expansão

O coletor não deve ser executado nos 973 repositórios de uma só vez antes de:

1. estabelecer intervalo de resfriamento e protocolo de retries para falhas;
2. selecionar uma subamostra aleatória/estratificada em vez de ordem lexicográfica;
3. impor orçamento total de bytes, tempo e requisições;
4. registrar o estado do cache antes e depois da recuperação preguiçosa;
5. ampliar fixtures e implementar o diff estruturado por regiões;
6. testar reexecução após falha parcial.

## Artefatos

- implementação: `scripts/09_collect_rq2_histories.py`;
- resumo corrigido: `outputs/rq2/history_pilot_v2/history_recovery_summary.csv`;
- estado dos repositórios: `outputs/rq2/history_pilot_v2/repository_collection_status.csv`;
- manifesto: `outputs/rq2/history_pilot_v2/history_recovery_manifest.json`;
- repetição idempotente: `outputs/rq2/history_pilot_v2_repeat/`;
- diagnóstico da sondagem: `outputs/rq2/probe_retry_smoke/`.
- implementação dos diffs: `scripts/10_extract_rq2_diffs.py`;
- eventos de diff corrigidos: `outputs/rq2/diff_pilot_v2/diff_events.csv`;
- manifesto dos diffs: `outputs/rq2/diff_pilot_v2/diff_manifest.json`.
- esquema revisado dos diffs: `outputs/rq2/diff_pilot_v3/`;
- expansão de calibração: consulte [rq2_history_calibration_report.md](rq2_history_calibration_report.md).

