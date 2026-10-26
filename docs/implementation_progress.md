# Progresso da continuidade científica

**Atualizado em:** 26 de outubro de 2026  
**Regra:** implementação, execução e conclusão científica são estados distintos.

## Concluído nesta continuidade

### RQ1 — cadeia reprodutível

- **IMPLEMENTADO E VERIFICADO:** `00_build_rq1_inputs.py`, que gera os dois intermediários antes ausentes diretamente do SQLite em modo somente leitura.
- **VERIFICADO:** `reuse_by_content.csv` reproduzido com SHA-256 idêntico ao histórico.
- **VERIFICADO:** 1.586.188 associações a repositório representante semanticamente idênticas ao histórico.
- **IMPLEMENTADO E VERIFICADO:** exportação para R e seleção explícita dos 16 megarepositórios.
- **VERIFICADO:** CSV completo do R idêntico por SHA-256; subconjunto sem megarepositórios semanticamente idêntico, com diferença máxima de serialização de ponto flutuante de `8,88e-16`.
- **IMPLEMENTADO E VERIFICADO:** FDR-BH separado por componente; decisões idênticas e diferença máxima de `2,22e-16`.
- **IMPLEMENTADO:** paths parametrizados em `01`, `03`, `03b` e `05` para execuções isoladas.
- **IMPLEMENTADO:** `sessionInfo()` nos modelos R, `renv.lock`, manifesto do snapshot local e 32 testes automatizados.
- **VERIFICADO:** tabelas descritiva, efeitos principais, efeitos contextuais e sensibilidade finais reproduzidas com SHA-256 idêntico.

### RQ2 — preparação do piloto

- **IMPLEMENTADO E EXECUTADO:** frame de âncoras de cópia exata.
- **VERIFICADO:** 254.078 hashes, 1.894.746 ocorrências, 1.405.714 presenças repositório–conteúdo, 91.529 repositórios e zero divergência entre contagens esperadas/observadas.
- **IMPLEMENTADO E EXECUTADO:** sorteio piloto estratificado, seed 2026.
- **VERIFICADO:** 55 âncoras, 11 estratos, 1.647 ocorrências e 973 repositórios distintos.
- **IMPLEMENTADO E DIAGNOSTICADO:** sondagem de acesso Git anônimo ao HEAD atual.
- **INCERTO:** duas execuções consecutivas classificaram 869 e 603 repositórios como acessíveis; 266 repositórios mudaram de “acessível” para falha anônima. A instabilidade é compatível com controle transitório/rate limiting e invalida uma estimativa de disponibilidade baseada nesse instrumento sem retries e backoff. Os resultados brutos foram preservados, mas não são resultado substantivo.
- **CONGELADO COMO PROTOCOLO:** codebook automatizado v0.2 e emenda metodológica v1.0; não haverá validação humana independente.
- **VERIFICADO:** manifesto `protocol_freeze_manifest.json` registra checksums dos seis documentos metodológicos congelados.
- **IMPLEMENTADO E VERIFICADO EM FIXTURES:** coletor Git idempotente com rename, merge e remoção; a combinação de `--follow` e `--full-history` preserva evidências complementares.
- **VERIFICADO EM SMOKE TEST NÃO REPRESENTATIVO:** três repositórios, sete ocorrências, sete blobs reconciliados e sete históricos não vazios; seis paths iguais ao hash-âncora no HEAD e um ausente.
- **VERIFICADO:** a repetição via cache produziu os dois CSVs de resumo com SHA-256 idêntico.
- **IMPLEMENTADO E VERIFICADO:** extração de diffs pai→filho com seleção de path, hashes dos blobs, churn e unified diff; cada pai de merge é comparado separadamente.
- **VERIFICADO EM FIXTURE:** adição raiz, rename puro, remoção e ambos os pais do merge produzem estados/mudanças resolvidos para o path esperado.
- **VERIFICADO EM SMOKE TEST NÃO REPRESENTATIVO:** sete ocorrências produziram oito comparações, quatro commits únicos, zero seleção ambígua e zero evento não resolvido. O conjunto externo não continha merges.
- **VERIFICADO:** o piloto original foi regenerado no esquema revisado com oito comparações, todas mudanças, e zero ambiguidade/não resolução (`diff_pilot_v3`).
- **IMPLEMENTADO E EXECUTADO:** seleção de calibração por ranking pseudoaleatório SHA-256, seed 20261026, round-robin entre os 11 estratos e deduplicação por repositório.
- **VERIFICADO:** 11 repositórios únicos, um por estrato, e 14 ocorrências selecionadas a partir dos 603 repositórios acessíveis nas duas sondagens.
- **VERIFICADO:** repetição da seleção reproduziu exatamente os três CSVs; hashes da lista, ocorrências e cobertura: `77769072…`, `29ba7b96…` e `9cf426dc…`.
- **VERIFICADO:** 11/11 repositórios coletados e 14/14 ocorrências com blob e histórico; os 14 paths no HEAD correspondiam ao hash-âncora. A recuperação consumiu 238,3 MB e 41,3 s, abaixo dos limites.
- **VERIFICADO:** a repetição via cache produziu `history_recovery_summary.csv` idêntico por SHA-256 (`1689df85ab8feb5a576f7512fbb68005477e0be2450aed02da31e590ae34ada4`).
- **IMPLEMENTADO E VERIFICADO:** limites globais de tempo/cache e estados explícitos para unidades não tentadas por orçamento.
- **VERIFICADO:** 35 comparações pai→filho: 26 mudanças, seis contextos inalterados e três contextos sem o path; 12 comparações pertencem a commits de merge. Não houve seleção ambígua nem comparação não resolvida.
- **VERIFICADO:** repetição dos diffs de calibração com CSV idêntico (`f9e1dd7fa261527651488e24f09d19b649b5ab825300eebd6edacc4dfe1e8e90`).
- **IMPLEMENTADO E VERIFICADO:** classificador estrutural `rq2-structured-diff-v1.0` para front matter, cabeçalhos, listas, blocos/cercas de código, código indentado, citações, tabelas, parágrafos e linhas vazias.
- **VERIFICADO:** os 26 diffs brutos tiveram checksum validado; 26 eventos classificados, zero falhas e 4.483 linhas de evidência. As contagens estruturadas reconciliam exatamente 4.252 adições e 231 remoções do Git.
- **VERIFICADO NA CALIBRAÇÃO, NÃO INFERENCIAL:** 18 adições de arquivo, sete modificações e um movimento puro; 22 eventos acionaram regras candidatas de relevância comportamental. Esses números não estimam prevalência populacional.
- **VERIFICADO:** reexecução independente reproduziu exatamente eventos, evidências e contagens agregadas (SHA-256 `0a04af31…`, `977df687…`, `377b4c1c…`).

### RQ2/RQ3 — amostra analítica exploratória

- **IMPLEMENTADO E VERIFICADO:** amostragem estratificada com estratos primários mutuamente exclusivos, cinco repositórios por estrato, seed e pesos condicionais registrados.
- **VERIFICADO:** 55 repositórios e 122 ocorrências foram selecionados no frame de 603 repositórios acessíveis nas duas sondagens; os quatro CSVs foram reproduzidos byte a byte.
- **VERIFICADO:** 53 repositórios tiveram coleta completa; 82 ocorrências permaneceram elegíveis e 40 foram excluídas pela regra conservadora aplicada aos dois repositórios incompletos.
- **VERIFICADO:** 287 comparações pai→filho foram extraídas, das quais 173 são eventos de mudança; zero ambiguidades e duas comparações não resolvidas.
- **VERIFICADO:** 173/173 eventos receberam classificação estrutural e comportamental, sem falhas. A correção para siblings binários foi exercitada e a saída analítica final é `behavioral_analytic_v2`.
- **SUPERSEDIDO:** `behavioral_analytic_v1` não deve ser usado, pois contém oito falhas de decodificação de siblings binários.
- **VERIFICADO:** 80/82 ocorrências elegíveis tiveram âncora temporal resolvida; seis apresentaram divergência posterior à âncora. Foram identificadas 75 comparações pós-âncora.
- **VERIFICADO, EXPLORATÓRIO:** divergência não ponderada de 7,5% (6/80; IC95% de Wilson 3,5%–15,4%) e ponderada condicional de 1,0% (bootstrap por repositório 0,3%–1,9%).
- **VERIFICADO:** a síntese RQ2/RQ3 foi reproduzida byte a byte. Resultados e limites de interpretação estão em `docs/exploratory_rq2_rq3_results_report.md`.
- **LIMITAÇÃO:** os resultados medem evolução intrarrepositório. Não constituem reconstrução genealógica, propagação entre repositórios ou análise das características associadas aos eventos da RQ3.

### RQ2 — busca inter-repositórios

- **IMPLEMENTADO E VERIFICADO:** assinatura exata normalizada, busca na mesma família-âncora, ordem temporal estrita, colapso por episódio de repositório e confiança A–D.
- **VERIFICADO:** 173 eventos produziram 151 assinaturas elegíveis; 19 grupos aparecem em mais de um repositório no histórico completo observado.
- **VERIFICADO:** restringindo a divergências pós-âncora e colapsando paths/commits repetidos, restou uma relação candidata entre dois repositórios, com atraso de 77,12 dias.
- **VERIFICADO:** zero relações A/B e uma relação C. Trata-se de remoção de baixa especificidade; não sustenta transmissão nem atribuição de origem.
- **NÃO ESTIMÁVEL:** taxa de propagação, pois oportunidade temporal não demonstra que o contexto pré-patch permanecia aplicável nas linhagens não adotantes.
- **VERIFICADO:** reexecução independente reproduziu os dez CSVs finais byte a byte.
- **SUPERSEDIDO:** versões anteriores ao colapso por repositório inflavam uma relação para quatro combinações e não devem ser usadas.

## Não concluído

### RQ1

1. Reexecutar os modelos R completos em um novo `run_id`; isso é computacionalmente pesado e os modelos históricos `.rds` ocupam centenas de MB.
2. Criar um orquestrador único com logs, códigos de saída e manifesto global.
3. Obter ou publicar um checksum oficial do snapshot do dataset; o checksum atual identifica apenas a cópia local auditada.
4. Adicionar sensibilidade da população a front matter/hash e alternativa à unidade de cluster.

### RQ2

1. Executar retries espaçados após período de resfriamento para distinguir falhas transitórias de persistentes; cache, backoff e taxonomia cautelosa já foram implementados.
2. Decidir entre ampliar a coleta para uma amostra confirmatória ou enquadrar formalmente o artigo como estudo exploratório condicionado; a amostra analítica atual não representa a população integral.
3. Modelar a não resposta ou executar reposição/recoleta pré-especificada; os pesos atuais não corrigem as 40 ocorrências excluídas.
4. Tratar falhas persistentes sem inferir motivo individual.
5. Reconstruir o estado das linhagens no instante de cada patch para testar compatibilidade de contexto e, somente então, definir denominadores elegíveis.
6. Ampliar fixtures do extrator para rename com edição e divergência de path entre pais; adição raiz, rename puro, remoção e merge já estão cobertos.
7. Calibrar similaridade somente para geração de candidatos.
8. Implementar integralmente as regras do codebook automatizado congelado e registrar o checksum executável.
9. Executar fixtures, repetibilidade e sensibilidades estrita/ampla; κ, P/R/F1 e adjudicação foram removidos do escopo.
10. Calcular alcance, atraso e consistência somente depois de validar denominadores elegíveis para propagação.

### RQ3

- **IMPLEMENTADO E VERIFICADO NA CALIBRAÇÃO:** classificador `rq3-behavioral-candidates-v1.0` com cenários estrito/amplo para comandos, acesso externo, referências a scripts e siblings executáveis.
- **VERIFICADO:** 26/26 eventos classificados, zero falhas, 813 registros de evidência textual e dois siblings candidatos em um evento.
- **VERIFICADO:** o cenário estrito é subconjunto do amplo. Dez eventos possuem candidato textual estrito e 22 possuem candidato amplo.
- **VERIFICADO:** a calibração corrigida `behavioral_calibration_v3` e sua reexecução reproduziram exatamente os quatro CSVs (`bed0fe90…`, `475c8fd3…`, `8e87cae8…`, `171358b7…`).
- **LIMITAÇÃO:** resultados são candidatos automatizados na calibração, sem validade semântica externa e sem interpretação populacional.
- **IMPLEMENTADO E VERIFICADO NA AMOSTRA ANALÍTICA:** 173/173 eventos classificados, com 4.142 registros textuais, 69 registros de siblings e zero falhas (`behavioral_analytic_v2`).
- **VERIFICADO, EXPLORATÓRIO:** prevalências estritas/amplas foram calculadas para 75 comparações pós-âncora, com estimativas condicionais e bootstrap por repositório.
- **IMPLEMENTADO E VERIFICADO:** base associativa com 75 eventos, 18 repositórios, 25 ocorrências, 17 famílias, 20 desfechos e 14 exposições.
- **VERIFICADO:** nenhum desfecho passou o gate pré-especificado de 30 clusters; regressão multivariada foi corretamente abandonada.
- **VERIFICADO:** 280 contrastes descritivos ponderados, sensibilidade estrita/ampla e matriz de coocorrência foram produzidos sem valores de `p` ou alegação causal.
- **VERIFICADO:** comandos adicionados ocorreram em 11 eventos estritos e 40 amplos; referências a scripts adicionadas, em um e 21. A taxonomia altera materialmente os resultados.
- **VERIFICADO:** três tabelas e duas figuras do artigo foram geradas; 12 artefatos das etapas 21–23 foram reproduzidos byte a byte.
- **LIMITAÇÃO:** a conclusão associativa é descritiva devido a apenas 18 clusters, concentração de 29/75 eventos em um repositório e ausência de validação semântica externa.

## Próxima tarefa recomendada

**CONCLUÍDO:** métodos, resultados, ameaças à validade e conclusão foram consolidados no manuscrito preliminar `IEEE_Conference_Template/gitskills_paper.tex`, usando somente versões finais rastreadas. O PDF tem quatro páginas e foi revisado visualmente; RQ2 declara a taxa de propagação não estimável e RQ3 permanece descritiva.

**CONCLUÍDO:** o manuscrito foi adaptado para entrega na disciplina, com autoria identificada, resumo estruturado, trabalhos relacionados e cinco referências verificadas nos PDFs locais. O limite é de quatro páginas e não há plano de publicação.

**PRÓXIMA TAREFA:** criar o depósito no Zenodo e substituir o marcador explícito pelo DOI/URL persistente; depois, executar a revisão final de entrega. Uma conclusão empírica mais forte continuaria dependente de ampliar a coleta e reconstruir o denominador contextual, mas isso não é requisito para a versão atual.
