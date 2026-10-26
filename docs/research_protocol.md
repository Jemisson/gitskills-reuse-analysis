# Protocolo de pesquisa e critérios de conclusão

**Estado:** protocolo prospectivo revisado; a emenda automatizada de 26/10/2026 está congelada e não constitui evidência de resultado.  
**Snapshot de referência:** julho de 2026.  
**Data do protocolo:** 16 de outubro de 2026; revisão metodológica em 26 de outubro de 2026.

> A [emenda de validação automatizada](protocol_amendment_automated_validation.md) substitui todas as exigências anteriores de anotação humana, dupla codificação, adjudicação, conjunto-ouro e concordância entre avaliadores. Na ausência de referência humana independente, as categorias de RQ2/RQ3 são definições operacionais automatizadas e seus resultados serão apresentados como exploratórios.

## Convenções de estado

- **VERIFICADO:** sustentado por inspeção/recomputação durante a auditoria.
- **DOCUMENTADO:** relatado nos materiais existentes, sem reprodução completa.
- **PLANEJADO:** decisão metodológica proposta neste protocolo.
- **INCERTO:** decisão que depende de piloto, disponibilidade ou análise de poder/precisão.

## Objetivo e princípio inferencial

O estudo investiga associações entre características de Agent Skills, reúso observável, evolução e mudanças comportamentalmente relevantes. O desenho é observacional. Nenhum modelo autoriza linguagem causal sem estratégia adicional de identificação, que não está planejada neste protocolo.

O estudo separará explicitamente cinco objetos:

1. **identidade de conteúdo:** igualdade byte a byte representada por `file_sha` validado;
2. **similaridade:** proximidade textual ou estrutural usada para recuperar candidatos;
3. **ancestralidade:** relação histórica sustentada por evidência Git/proveniência;
4. **evolução:** sequência temporal de versões dentro de uma linhagem sustentada;
5. **propagação de alteração:** reaparecimento de uma mudança identificável em outra linhagem/repositório, com ordem temporal e oportunidade de observação.

Similaridade não prova ancestralidade. O repositório representante não é autor, doador ou origem. A ocorrência mais antiga observada é apenas um limite superior para a origem real no universo parcialmente observado.

## Modelo de dados analítico planejado

| Entidade | Chave proposta | Significado |
|---|---|---|
| Ocorrência | repositório + path + snapshot | uma skill observada em um local |
| Versão | repositório + path/rename + commit + blob/hash | estado da skill em um commit |
| Evento de mudança | versão pai + versão filha | diff temporal dentro de uma linhagem |
| Âncora de cópia exata | `file_sha` + conjunto de ocorrências | mesmo conteúdo observado em locais distintos |
| Relação candidata | par de versões/linhagens + evidências | hipótese, não fato, de relação evolutiva |
| Família genealógica | componente de relações aceitas sob um nível declarado | conjunto dependente do limiar de evidência |
| Evento de propagação | mudança + adoção posterior compatível em outra linhagem | transmissão inferida com confiança declarada |

Cada tabela deverá conter `source_snapshot`, `retrieved_at`, versão do extrator, checksum da entrada, status de parsing e motivo de ausência/exclusão.

## Escala de confiabilidade genealógica

As relações serão armazenadas com evidências atômicas, não apenas um escore opaco.

| Nível | Uso analítico | Evidência mínima planejada |
|---|---|---|
| A — sustentada | análise principal de ancestralidade dirigida | relação por commits/objetos Git alcançáveis ou proveniência explícita verificável, mais ordem temporal não contraditória |
| B — compatível | análise de família/cópia, sem afirmar doador direto | conteúdo exato compartilhado e cronologia compatível; direção pode permanecer indeterminada |
| C — candidata | recuperação e análise de sensibilidade | similaridade/diff e cronologia compatíveis, sem prova histórica suficiente |
| D — rejeitada/ambígua | excluída da análise dirigida | cronologia contraditória, múltiplos ancestrais equivalentes ou evidência insuficiente |

Os critérios operacionais finais e qualquer limiar numérico serão congelados após piloto e antes da amostra confirmatória. **INCERTO:** os limiares ainda não foram calibrados.

## RQ1

### Definição

**Como a reutilização está distribuída e quais características textuais, estruturais e contextuais estão associadas à ampla propagação?**

### Unidade de análise

**VERIFICADO:** conteúdo exato distinto de `SKILL.md`, identificado por `file_sha`; no modelo, uma linha por conteúdo.

### Dados necessários

- ocorrências válidas e seus hashes;
- repositórios distintos por hash;
- texto, front matter, composição e metadados do repositório representante;
- indicadores de qualidade e ausência.

### Procedimentos implementados

- filtros da população, extração de características e preparação;
- descrição do reúso exato;
- modelo em duas partes: logístico e PPML condicional;
- erros agrupados pelo repositório representante;
- FDR-BH e duas sensibilidades.

### Procedimentos pendentes

- versionar as etapas ausentes da cadeia;
- reproduzir ponta a ponta com manifesto/checksums;
- testar critérios alternativos da população e estrutura de dependência;
- decidir se associações contextuais permanecem no artigo principal ou são apresentadas como exploratórias.

### Resultados existentes

**VERIFICADO:** 1.586.188 conteúdos; 16,0182% reutilizados; 42,0639% das presenças conteúdo–repositório além da primeira; máximo 937; Gini 0,3978. Coeficientes, intervalos e FDR constam das tabelas finais. Consulte a [auditoria](research_audit.md).

### Limitações

- identidade exata não captura variantes;
- desenho transversal e observacional;
- contexto pertence ao representante, não à origem;
- seleção por validade de front matter/hash;
- Flesch orientado ao inglês;
- histórico parcial e agregadores grandes;
- pipeline incompleto no Git.

### Critérios verificáveis de conclusão

- pipeline integral executável do snapshot bruto às tabelas finais;
- todas as entradas com checksum e esquema;
- testes de invariantes e sensibilidades pré-especificadas aprovados;
- tabela de resultados regenerada sem intervenção manual;
- conclusões limitadas a reúso exato e associação;
- desvios do plano inicial documentados.

**Estado:** análise substantiva executada; conclusão reprodutível ainda pendente.

## RQ2

### Definição

**Quais padrões de estabilidade, divergência e propagação de alterações emergem após as skills serem copiadas entre repositórios?**

### Unidade de análise

- principal: evento de mudança em uma linhagem dentro de uma família genealógica;
- secundárias: versão, linhagem repositório–path e família;
- para tempo até divergência: cópia/linhagem com início e censura definidos.

Uma “família” não será formada apenas por similaridade; sua composição dependerá do nível de evidência declarado.

### Dados necessários

- todas as ocorrências dos hashes-âncora amostrados;
- histórico Git completo, commits pais, blobs, renomes e timestamps;
- relações de fork/commit compartilhado quando disponíveis;
- snapshots do `SKILL.md` e de siblings relevantes;
- status de indisponibilidade, branch e censura;
- classificações automatizadas versionadas, evidências atômicas e status de incerteza.

### Procedimentos implementados

**VERIFICADO:** nenhum procedimento específico de RQ2. Existem somente descrição na proposta e infraestrutura vazia de diretórios.

### Procedimentos pendentes

- amostragem estratificada e análise de recuperabilidade;
- mineração/versionamento dos históricos;
- geração de candidatos similares;
- reconstrução e classificação das genealogias;
- extração/classificação de diffs;
- validação automatizada por fixtures, invariantes, repetibilidade e sensibilidades;
- estimação descritiva/longitudinal e sensibilidades.

### Resultados existentes

**VERIFICADO:** nenhum resultado de RQ2. A cobertura histórica resumida de 24,64% na população da RQ1 não equivale a genealogias completas.

### Limitações previstas

- truncamento à branch/default snapshot e repositórios públicos;
- repositórios removidos, reescrita de história e timestamps não equivalentes à autoria;
- cópia fora do Git, fonte comum não observada e múltiplos ancestrais possíveis;
- viés de recuperabilidade e censura à direita;
- vazamento entre treino/validação se versões da mesma família forem separadas.

### Critérios verificáveis de conclusão

- amostra e frame congelados com fluxograma de inclusão;
- taxa de recuperação e motivos de perda reportados por estrato;
- cada aresta genealógica possui evidências e nível de confiança auditáveis;
- duplicatas, renomes, merges, relógios e empates tratados por regras versionadas;
- codebook executável congelado, com evidência por decisão, fixtures e casos incertos preservados;
- métricas RQ2 calculadas com denominadores explícitos e incerteza;
- análises repetidas por nível A, A+B e A+B+C, sem transformar C em fato;
- tabelas/figuras regeneráveis pelo pipeline.

**Estado:** PLANEJADO; não iniciado cientificamente.

## RQ3

### Definição

**Quais características estão associadas a mudanças que introduzem ou removem comandos, acesso externo ou artefatos executáveis?**

### Unidade de análise

Principal: evento de mudança pai→filho validado em uma linhagem. Os desfechos são multirrótulo e direcionais (`adiciona`, `remove`, `modifica`) para comandos, acesso externo e artefatos executáveis. Agregações por família serão secundárias.

### Dados necessários

- eventos de mudança e genealogias provenientes da RQ2;
- diff bruto e representação estruturada de Markdown/front matter;
- alterações em siblings e permissões/tipos de arquivo quando recuperáveis;
- candidatos de comandos, URLs/domínios, downloads, execução e arquivos executáveis;
- covariáveis medidas antes da mudança;
- conjunto de fixtures sintéticas e casos de regressão versionados, sem alegação de padrão-ouro independente.

### Procedimentos implementados

**VERIFICADO:** nenhum. Contagens estáticas de URLs, blocos de código, scripts e referências na RQ1 não são mudanças e não respondem à RQ3.

### Procedimentos pendentes

- taxonomia e regras automatizadas executáveis;
- parser/detector de candidatos com status de falha;
- amostra de validação enriquecida para eventos raros, com pesos ou avaliação separada;
- cobertura das fixtures, determinismo e sensibilidade das regras automatizadas;
- modelos associativos com dependência por família/repositório;
- robustez a classificação, genealogia e eventos raros.

### Resultados existentes

**VERIFICADO:** nenhum resultado de RQ3.

### Limitações previstas

- texto de comando não implica execução real;
- URL não implica acesso de rede, e remoção textual não garante remoção comportamental;
- arquivos “executáveis” exigem definição por conteúdo, extensão/permissão e contexto;
- erros de classificação podem ser diferenciais;
- mudanças raras podem impedir modelos multivariados estáveis;
- associações não estabelecem que uma característica causou a alteração.

### Critérios verificáveis de conclusão

- taxonomia congelada e exemplos-limite documentados;
- fixtures positivas, negativas, limítrofes e de falha no nível de família/evento;
- repetibilidade exata, cobertura das regras e proporção de casos incertos reportadas;
- estabilidade das classificações sob definições estrita e ampla, sem precisão/recall/F1 na ausência de padrão-ouro independente;
- modelo escolhido após examinar prevalência, sem seleção oportunista por significância;
- covariáveis temporalmente anteriores ao evento;
- erros agrupados/efeitos de família e correção de multiplicidade definidos;
- resultados repetidos sob limiares de confiança genealógica e cenários de erro de classificação.

**Estado:** PLANEJADO e dependente da conclusão mínima de RQ2.

## Estratégia de amostragem comum a RQ2–RQ3

1. Construir o frame a partir de âncoras de cópia exata da RQ1, preservando todas as ocorrências, não somente representantes.
2. Estratificar por intensidade de reúso, disponibilidade histórica, localização da skill, status de fork/agregador e contexto temporal. Faixas finais serão congeladas antes da seleção.
3. Sortear famílias/âncoras com seed e probabilidade conhecida; manter todas as ocorrências das unidades sorteadas.
4. Separar uma amostra de prevalência representativa de uma amostra enriquecida para eventos raros de RQ3. Não misturar estimativas sem ponderação apropriada.
5. Definir tamanho após piloto de recuperabilidade e precisão desejada dos intervalos. **INCERTO:** o tamanho ainda não pode ser justificado com as informações presentes.
6. Dividir treino/calibração/validação por família, nunca por diff individual.

## Validação automatizada e limites de interpretação

- regras, precedência e limiares são congelados antes das análises associativas;
- cada classificação preserva trecho/offset, regra acionada, versão do classificador e confiança operacional;
- casos sem evidência suficiente recebem `incerto` ou status de falha, sem imputação semântica;
- fixtures sintéticas cobrem positivos, negativos, limites, renames, merges e falhas de parser;
- reexecuções devem reproduzir exatamente as classificações para a mesma entrada e configuração;
- análises de sensibilidade usam definições estrita/ampla e cenários de erro especificados antes da interpretação dos resultados;
- não serão reportados κ, acordo entre avaliadores, precisão, recall ou F1 como evidência de validade, pois não haverá referência humana independente;
- inspeções realizadas nesta interação servem apenas para depuração e auditoria interna, não como validação humana independente.

## Regras de análise e rastreabilidade

- preregistrar hipóteses confirmatórias; rotular o restante como exploratório;
- manter tabela `claim_id → dataset → script → tabela/figura → conclusão`;
- armazenar decisões de inclusão/exclusão como dados, nunca apenas no log;
- controlar FDR dentro de famílias de hipóteses definidas previamente;
- reportar estimativas, IC e denominadores, não somente significância;
- preservar saídas imutáveis por `run_id`; novas execuções criam novos diretórios;
- não sobrescrever os resultados científicos existentes.

## Critério global de prontidão para artigo

O artigo estará pronto para consolidação somente quando as três RQs possuírem cadeia de evidência reproduzível, critérios de conclusão atendidos, matriz de evidências completa, limitações explícitas e distinção consistente entre fatos observados, relações inferidas e hipóteses incertas.

Para RQ2/RQ3, “critério de conclusão atendido” significa conclusão sob definições operacionais automatizadas. Não significa validade semântica externa nem substitui replicação independente futura.
