# Plano de implementação da RQ3

**RQ3:** Quais características estão associadas a mudanças que introduzem ou removem comandos, acesso externo ou artefatos executáveis?  
**Estado:** PLANEJADO. Nenhum resultado de RQ3 existe atualmente.  
**Dependência crítica:** eventos de mudança e genealogias operacionalmente classificados pela RQ2.

> Conforme a [emenda metodológica](protocol_amendment_automated_validation.md), RQ3 será exclusivamente automatizada e exploratória, sem anotação humana independente ou conjunto-ouro.

## Escopo e unidade

A unidade principal será o evento de mudança `versão pai → versão filha` dentro de uma linhagem validada. Um evento pode receber múltiplos rótulos. A análise distinguirá:

- **alvo:** comando, acesso externo ou artefato executável;
- **direção:** adição, remoção ou modificação;
- **região:** front matter, instruções, exemplo, bloco de código, script/sibling ou referência;
- **evidência:** textual, estrutural e histórica observável;
- **confiança:** ordinal, mantida separada do rótulo substantivo.

“Comando presente” não significa “comando executado”; “URL presente” não significa “rede acessada”; extensão ou permissão isolada não prova executabilidade. As conclusões usarão “mudança textual/estrutural compatível com”, salvo evidência mais forte.

## Taxonomia planejada

### Comandos

- invocação de shell/CLI;
- instalação/gerenciamento de dependência;
- manipulação de arquivos/processos/permissões;
- execução de linguagem, build, teste ou implantação;
- comando privilegiado ou destrutivo como subclasse, definido no codebook.

### Acesso externo

- URL/domínio/endereço adicionado, removido ou alterado;
- download/upload, chamada de API, webhook ou conexão remota;
- mudança de protocolo, host, endpoint ou credencial-placeholder;
- referência documental simples separada de instrução operacional de acesso.

### Artefatos executáveis

- script sibling adicionado/removido/modificado;
- binário ou arquivo com permissão executável quando essa informação estiver disponível;
- bloco de código transformado em script referenciado, ou inverso;
- dependência executável/referência a ferramenta, como classe distinta de arquivo executável.

O codebook executável decidirá casos-limite antes da análise associativa. **INCERTO:** prevalência e granularidade sustentável ainda dependem do piloto.

## Extração de candidatos

1. Consumir somente eventos RQ2 com IDs e proveniência estáveis.
2. Separar front matter e árvore Markdown, preservando offsets no texto original.
3. Extrair linhas adicionadas/removidas e contexto de blocos cercados/inline.
4. Detectar candidatos de comandos com parser específico quando a linguagem for conhecida; usar heurísticas versionadas com rótulo de incerteza nos demais casos.
5. Extrair URLs/domínios/protocolos e distinguir referências de instruções operacionais por regras versionadas e cenários estrito/amplo.
6. Comparar manifestos de siblings, tipo, hash, tamanho, conteúdo e permissão quando disponível.
7. Produzir um JSON por evento com evidência, offset, regra, versão do parser e status de falha.
8. Nunca descartar silenciosamente eventos que o parser não compreende.

## Estratégia de amostragem e validação automatizada

Serão mantidas duas amostras:

- **prevalência:** probabilística, derivada da amostra confirmatória da RQ2, para estimativas populacionais;
- **enriquecida:** sobreamostra candidatos positivos e casos difíceis para testar cobertura operacional e aperfeiçoar regras, sem estimar acurácia externa.

Estimativas de prevalência não usarão a amostra enriquecida sem pesos. Fixtures e casos de regressão serão separados por família quando derivados de dados reais. As regras serão congeladas antes da análise associativa; revisões posteriores gerarão nova versão e novas saídas.

Serão reportados, por rótulo e direção:

- prevalência sob a definição operacional;
- cobertura das regras, falhas e proporção `incerto`;
- estabilidade entre definições estrita e ampla;
- nenhuma métrica de concordância ou desempenho contra padrão-ouro inexistente.

## Variáveis explicativas candidatas

Somente variáveis medidas antes do evento poderão ser usadas como associadas à mudança:

- características da versão pai: tamanho, estrutura, comandos/URLs/scripts existentes;
- características da linhagem/família: idade observada, número de versões/linhagens, intensidade de reúso e divergência prévia;
- características do evento: tempo desde a versão anterior e tamanho total do diff (quando não for parte definicional do desfecho);
- contexto do repositório no momento observável: estrelas, atividade, linguagem, fork/agregador, com cautela temporal;
- nível de confiança genealógica e cobertura do histórico como controles/estratos.

Características pós-evento, identidade do representante e informação futura não serão preditores. O conjunto final será congelado antes dos modelos confirmatórios e reduzido conforme frequência de eventos para evitar sobreajuste.

## Desfechos e métricas

### Desfechos primários

Para cada alvo, indicadores separados de adição e remoção. Modificação será um desfecho separado ou composição adição+remoção, conforme regra congelada no codebook. Como os rótulos podem coexistir, um único desfecho multinomial não será imposto sem verificar exclusividade.

### Métricas descritivas

- incidência por 100 eventos observados, com IC;
- distribuição por região e direção;
- coocorrência entre comandos, rede e executáveis;
- tempo desde cópia/última mudança;
- alcance posterior da variante, descrito sem causalidade;
- taxa de reversão/correção posterior quando observável.

### Modelos associativos

O modelo será escolhido após conhecer prevalência e estrutura de clusters, conforme regra pré-especificada:

- regressão logística/GEE ou modelo misto para desfecho binário, com dependência por família e possivelmente repositório;
- penalização ou método apropriado a eventos raros se separação/baixa contagem ocorrer;
- análise descritiva, sem regressão multivariada, quando o número efetivo de eventos não sustentar o modelo;
- razões de efeito, IC de 95%, diagnóstico e FDR por família de hipóteses;
- nenhuma seleção automática baseada apenas em `p`.

## Testes de robustez

1. Definições estrita versus ampla e diferentes limiares congelados do classificador.
2. Definições estrita e ampla de comando, acesso externo e executável.
3. Relações genealógicas A versus A+B; C apenas em sensibilidade.
4. Eventos intrarrepositório apenas versus eventos ligados entre repositórios.
5. Exclusão de mudanças de formatação e diffs grandes.
6. Exclusão de forks, templates, mirrors e agregadores.
7. Agrupamento por família, repositório e agrupamento cruzado quando suportado.
8. Casos completos versus cenários de falha de parser/histórico.
9. Análise de erro de classificação por cenários hipotéticos explícitos, sem alegar taxas observadas de falso positivo/negativo.
10. Modelos alternativos para eventos raros e especificações reduzidas.
11. Controle FDR com e sem categorias exploratórias.
12. Holdout temporal, se cobertura e tamanho permitirem.

## Tarefas e critérios de aceitação

| ID | Tarefa | Dependências | Critério objetivo de aceitação |
|---|---|---|---|
| R3.01 | Definir schema do evento RQ3 | R2.11 | schema versionado contempla multilabel, direção, offsets, evidência, confiança e falha. |
| R3.02 | Escrever taxonomia/codebook v0 | R3.01 | exemplos positivos, negativos e limítrofes para cada classe; linguagem não causal. |
| R3.03 | Construir fixtures de diffs | R3.02 | casos sintéticos e reais licenciáveis cobrem Markdown, shell, URLs e siblings. |
| R3.04 | Implementar parser estrutural | R3.03 | testes preservam offsets e texto; falhas são retornadas como dados. |
| R3.05 | Implementar detector de comandos | R3.04 | regras/parsers versionados; saída contém evidência e linguagem inferida. |
| R3.06 | Implementar detector de acesso externo | R3.04 | distingue candidato operacional de referência; domínio/protocolo normalizados sem perder original. |
| R3.07 | Implementar detector de executáveis/siblings | R2.11, R3.04 | compara manifesto pai/filho e registra limitações de permissão/tipo. |
| R3.08 | Executar piloto automatizado | R3.05–R3.07 | fixtures e casos de regressão executados; falhas, incertezas e lacunas de regra enumeradas. |
| R3.09 | Congelar codebook e regras | R3.08 | versão, checksum e decisões registrados antes da análise associativa. |
| R3.10 | Selecionar amostras de prevalência e enriquecida | R2.05, R3.09 | probabilidades/pesos conhecidos; split por família; sem vazamento. |
| R3.11 | Classificar amostras automaticamente | R3.10 | toda decisão contém regra/evidência/versão ou status explícito de incerteza/falha. |
| R3.12 | Avaliar determinismo e cobertura | R3.11 | reexecução idêntica; cobertura de fixtures, falhas e proporção incerta reportadas. |
| R3.13 | Avaliar sensibilidade da classificação | R3.11 | cenários estrito/amplo e limiares predefinidos comparados; mudanças de rótulo quantificadas. |
| R3.14 | Congelar desfechos/covariáveis/modelos | R3.12–R3.13 | plano assinado antes de consultar associações confirmatórias. |
| R3.15 | Gerar dataset analítico | R3.14 | uma linha por evento, chaves únicas, covariáveis pré-evento e checksums. |
| R3.16 | Estimar resultados | R3.15 | estimativas/IC, diagnósticos, clusters e FDR reproduzíveis; modelos inviáveis explicitamente abandonados. |
| R3.17 | Executar robustez | R3.16 | todos os cenários predefinidos executados ou justificados; instabilidades reportadas. |
| R3.18 | Gerar artefatos do artigo | R3.17 | tabelas/figuras por comando único, ligadas à matriz de evidências. |

## Tabelas e figuras necessárias

### Tabelas

1. Taxonomia operacional com exemplos e exclusões.
2. Fluxo da amostra de prevalência e da amostra enriquecida.
3. Prevalência por alvo, direção e região.
4. Cobertura das regras, falhas e casos incertos por classe.
5. Estabilidade das classificações entre definições estrita e ampla.
6. Coocorrência de rótulos.
7. Estimativas associativas com IC e FDR.
8. Sensibilidades a taxonomia, genealogia, clustering e classificação.

### Figuras

1. Diagrama do pipeline diff→candidato→classificação automatizada→modelo.
2. UpSet plot ou matriz compacta de coocorrência multilabel.
3. Distribuição temporal das mudanças por direção.
4. Forest plots separados por desfecho, se modelos forem sustentáveis.
5. Distribuição de escores/confiança operacional, sem interpretação como probabilidade calibrada.
6. Heatmap de estabilidade das estimativas nos testes de robustez.

## Critério de encerramento da RQ3

RQ3 só será concluída quando R3.01–R3.18 forem aceitas, a sensibilidade a cenários explícitos de erro estiver quantificada, as genealogias usadas tiverem nível explícito de confiança e as conclusões permanecerem associativas e exploratórias. A ausência de validação humana independente será uma ameaça à validade de construto. Se a frequência de eventos for insuficiente, uma resposta descritiva rigorosa será considerada conclusão válida; forçar um modelo instável não será.

