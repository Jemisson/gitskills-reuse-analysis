# Plano de implementação da RQ2

**RQ2:** Quais padrões de estabilidade, divergência e propagação de alterações emergem após as skills serem copiadas entre repositórios?  
**Estado:** PLANEJADO. Nenhuma tarefa abaixo é evidência de execução.  
**Dependência:** protocolo e cadeia da população/RQ1 congelados antes da coleta confirmatória.

> **Progresso em 26/10/2026:** R2.01 e R2.02 foram implementadas e executadas; R2.03 permanece parcial. Além do smoke inicial, uma calibração com seed 20261026 selecionou 11 repositórios, um por estrato, e recuperou 14 ocorrências. Foram separadas 26 mudanças reais de nove registros de contexto de travessia do grafo. A seleção está condicionada à interseção de duas sondagens instáveis e não admite inferência populacional. O diff estruturado e a amostra confirmatória permanecem pendentes. Consulte [implementation_progress.md](implementation_progress.md), [rq2_history_pilot_report.md](rq2_history_pilot_report.md) e [rq2_history_calibration_report.md](rq2_history_calibration_report.md).

## Resultado esperado

Um pipeline auditável que parte de ocorrências amostradas, recupera histórias Git, constrói versões e diffs, registra evidências genealógicas e produz estimativas descritivas/longitudinais com incerteza. O pipeline não atribuirá origem ao representante, nem converterá similaridade textual em ancestralidade.

## Estratégia de amostragem

### Frame

O frame primário será o conjunto de hashes exatos presentes em pelo menos dois repositórios, ligado a **todas** as ocorrências `repo_full_name + path`. O representante serve somente como ponte técnica para artefatos da RQ1 e não como origem.

### Desenho em dois estágios

1. **Piloto de recuperabilidade:** sorteio estratificado pequeno, usado somente para medir disponibilidade, custo, renomes, profundidade de história e prevalência preliminar de divergência. Seus resultados definirão tamanho e alocação da amostra confirmatória, não conclusões substantivas.
2. **Amostra confirmatória:** sorteio com probabilidades registradas e seed, estratificado por intensidade de reúso, disponibilidade histórica no dataset, localização, fork/agregador e período observado. Todas as ocorrências das âncoras sorteadas serão preservadas.

O tamanho será calculado após o piloto visando precisão de intervalos para proporções e viabilidade de modelos com cluster por família. **INCERTO:** não há base atual para fixar um número defensável. Famílias grandes poderão receber amostragem interna adicional, com pesos e regra congelada, para não dominar custo e estimativas.

### Controle de viés

- comparar respondentes e não respondentes por estrato e covariáveis da RQ1;
- registrar motivo de falha: removido, privado, rate limit, clone incompleto, LFS/submódulo, branch ausente, arquivo sem história ou erro de parsing;
- estimar resultados ponderados pelo desenho; ponderação por não resposta somente com modelo pré-especificado e diagnóstico;
- executar sensibilidades incluindo/excluindo forks, agregadores e famílias extremas.

## Protocolo de reconstrução de genealogias

### 1. Recuperação

- resolver a branch observada no snapshot e registrar a branch/default atual separadamente;
- clonar/baixar sem modificar o remoto, preservando objetos e metadados necessários;
- localizar o path do snapshot e seguir renomes com evidência de similaridade de arquivo apenas dentro da história Git;
- enumerar commits que alteram o arquivo, pais, merges, blob SHA, autor anonimizado se permitido e timestamps de autor/commit;
- registrar a data de coleta e a possível diferença entre estado atual e snapshot.

### 2. Linhagem intrarrepositório

Cada aresta pai→filho será derivada do grafo de commits. Em merges, cada pai será preservado; uma regra explícita decidirá qual diferença representa a mudança introduzida, sem linearizar silenciosamente a história. Renomes serão relações de continuidade com evidência registrada, não igualdade presumida por nome.

### 3. Âncoras inter-repositório

Conteúdo exato compartilhado forma uma âncora de cópia compatível. A direção será atribuída somente quando sustentada por Git alcançável/proveniência explícita e cronologia. A primeira ocorrência observada sem essa evidência não será chamada de origem.

### 4. Variantes candidatas

- normalização leve e versionada somente para recuperação (line endings, front matter/corpo e tokens); o original permanece imutável;
- geração de candidatos por shingles/MinHash ou técnica equivalente de alta revocação;
- comparação estrutural por seções Markdown e diff de tokens/linhas;
- limiares calibrados no piloto e congelados antes da amostra confirmatória;
- candidatos similares permanecem nível C até receber evidência histórica independente.

### 5. Montagem da família

O grafo armazenará nós de versão e arestas tipadas, com evidências atômicas, confiança A–D e razões de rejeição. Serão produzidas visões A, A+B e A+B+C. Ciclos temporais, múltiplos pais plausíveis e empates serão preservados como ambiguidade, não resolvidos por conveniência.

## Extração e classificação de diffs

Para cada aresta intrarrepositório e relação comparável:

- salvar hash dos textos pai/filho e unified diff;
- produzir diff estruturado de front matter, títulos, parágrafos, listas, blocos de código, links e referências;
- classificar `adição`, `remoção`, `modificação`, `movimento` e `formatação apenas`;
- rotular regiões: nome/descrição, instruções, exemplos, comandos/código, rede/URLs, scripts, referências e metadados;
- calcular tamanho bruto e normalizado, churn e distância textual/estrutural;
- registrar parser, versão, falhas e fallback;
- preservar rótulo automático, regra acionada, evidência e confiança operacional em campos separados.

## Métricas quantitativas

### Estabilidade e divergência

- proporção de linhagens sem mudança após a âncora, com janela de observação;
- tempo até primeira mudança e até primeira divergência, com censura à direita;
- número de versões e eventos por linhagem/família;
- churn por evento e acumulado;
- distância entre variantes contemporâneas;
- largura/profundidade e número de ramos do grafo;
- proporção de mudanças por região/tipo.

### Propagação de alterações

Uma alteração propagada exige assinatura de patch ou efeito estruturado comparável, adoção posterior e oportunidade de observação. Serão reportados:

- alcance: número/proporção de linhagens elegíveis que adotam a alteração;
- atraso entre primeira observação e adoções subsequentes;
- consistência: adoções equivalentes / adoções elegíveis;
- divergência pós-adoção e reversões;
- fração de casos com direção indeterminada.

O denominador “elegível” exige que a linhagem existisse, estivesse observável e ainda contivesse o contexto ao qual o patch se aplica. Sem esse denominador, não se alegará taxa de propagação.

### Análise

- estatísticas descritivas ponderadas pelo desenho amostral;
- Kaplan–Meier ou estimador equivalente para tempo até divergência, se os pressupostos e a cobertura temporal permitirem;
- modelos com dependência por família/repositório somente após diagnóstico de tamanho e eventos;
- resultados principais restritos a níveis de evidência A/B apropriados à afirmação;
- estimativas com IC; valores de `p` são secundários e sujeitos a FDR quando houver famílias de hipóteses.

## Validação automatizada

- fixtures versionadas cobrem classes positivas, negativas, limítrofes e falhas;
- regras produzem evidência atômica, versão e status `incerto` quando não puderem decidir;
- a mesma entrada/configuração deve reproduzir exatamente a classificação;
- casos ambíguos permanecem uma classe válida;
- definições estrita e ampla medem estabilidade dos resultados;
- não serão calculados κ, precisão, recall ou F1 sem referência humana independente;
- a ausência dessa validação será declarada ameaça à validade de construto.

## Testes de robustez

1. Famílias A apenas versus A+B e A+B+C.
2. Limiares alternativos de geração de candidatos.
3. Diff por linha, token e estrutura Markdown.
4. Datas de autor versus commit; exclusão de relógios impossíveis/empates.
5. Exclusão de forks, mirrors, templates e agregadores, separadamente.
6. Exclusão de famílias extremas e ponderação para tamanho da família.
7. Janelas mínimas comuns de observação e diferentes regras de censura.
8. Casos completos versus ajuste/ponderação por recuperabilidade.
9. Definições estrita e ampla de “mesma alteração”.
10. Bootstrap por família, quando computacionalmente viável.

## Tarefas e critérios de aceitação

| ID | Tarefa | Dependências | Critério objetivo de aceitação |
|---|---|---|---|
| R2.01 | Versionar frame de ocorrências | RQ1-P0 | SQL/script somente leitura; uma linha por ocorrência; invariantes e checksums passam. |
| R2.02 | Definir estratos e seed | R2.01 | arquivo de configuração versionado; cada unidade tem estrato e probabilidade de seleção. |
| R2.03 | Executar piloto de recuperabilidade | R2.02 | relatório por estrato com sucesso, motivo de falha, custo e nenhuma conclusão substantiva. **PARCIAL:** calibração cobriu os 11 estratos, mas a elegibilidade depende de sondagens instáveis. |
| R2.04 | Calcular tamanho/alocação confirmatória | R2.03 | notebook/script registra pressupostos, precisão-alvo e análise de sensibilidade. |
| R2.05 | Congelar amostra | R2.04 | manifesto imutável com IDs, seed, pesos e checksum. |
| R2.06 | Implementar coletor Git idempotente | R2.03 | reexecução não duplica; registra commit/branch/status; testes com fixtures de rename/merge. |
| R2.07 | Extrair versões intrarrepositório | R2.06 | todos os nós têm blob/text hash; arestas apontam para commits pais válidos ou motivo de exceção. **PARCIAL:** calibração de 14 ocorrências reconciliou blobs e gerou 35 comparações de pais, sem validade amostral. |
| R2.08 | Implementar candidatos de variantes | R2.03 | fixtures e sensibilidades documentam cobertura operacional; limiar congelado; original preservado; sem alegar recall/precisão externos. |
| R2.09 | Extrair evidências inter-repositório | R2.06–R2.08 | cada relação possui evidências atômicas, cronologia e nível A–D. |
| R2.10 | Construir genealogias | R2.07–R2.09 | grafos validam schema; ciclos/ambiguidades reportados; nenhuma origem inferida do representante. |
| R2.11 | Implementar diffs estruturados | R2.07 | fixtures cobrem front matter, Markdown, código, links, rename e merge; falhas têm status. **PARCIAL:** unified diff, hashes, churn e separação entre mudança/contexto implementados; estrutura Markdown/classificação pendentes. |
| R2.12 | Congelar codebook executável | R2.10–R2.11 | versão e checksum registrados antes da análise; exemplos e casos-limite incluídos. |
| R2.13 | Executar fixtures e regressão automatizada | R2.12 | classes/regras cobertas; determinismo comprovado; falhas e casos incertos preservados. |
| R2.14 | Avaliar estabilidade das regras | R2.13 | matriz estrita/ampla e cenários de erro completos; sem métricas contra padrão-ouro inexistente. |
| R2.15 | Calcular métricas RQ2 | R2.10–R2.14 | cada métrica possui numerador, denominador, IC e nível de evidência. |
| R2.16 | Executar robustez | R2.15 | matriz de cenários completa; mudanças materiais identificadas, não ocultadas. |
| R2.17 | Gerar artefatos do artigo | R2.16 | tabelas/figuras reproduzidas por comando único e ligadas à matriz de evidências. |

## Tabelas e figuras necessárias

### Tabelas

1. Fluxo de seleção, recuperação e exclusão por estrato.
2. Caracterização da amostra versus frame e análise de não resposta.
3. Distribuição dos níveis de confiança e tipos de evidência.
4. Estabilidade, divergência, churn e tempo por estrato.
5. Tipos/regiões de mudança.
6. Alcance, atraso e consistência de propagação, com denominadores elegíveis.
7. Cobertura das regras, casos incertos e estabilidade entre definições automatizadas.
8. Matriz de sensibilidades.

### Figuras

1. Fluxograma de amostragem e recuperação.
2. Exemplo classificado de genealogia, sem atribuir origem não comprovada.
3. Distribuição de tamanhos/profundidade de famílias.
4. Curvas de tempo até primeira divergência, se aplicáveis.
5. Heatmap de tipos de mudança × regiões.
6. Distribuição do atraso de propagação.
7. Forest plot de estimativas associativas, se modelos forem justificáveis.

## Critério de encerramento da RQ2

RQ2 só poderá ser marcada como concluída quando R2.01–R2.17 estiverem aceitas, as limitações de recuperabilidade, ancestralidade e ausência de validação humana estiverem explícitas, e todas as conclusões indicarem o nível de evidência e a definição operacional que as sustenta. A conclusão será exploratória quanto às categorias automatizadas.

