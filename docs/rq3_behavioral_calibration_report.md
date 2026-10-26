# Relatório da classificação comportamental automatizada — RQ3

**Data:** 26 de outubro de 2026  
**Classificador:** `rq3-behavioral-candidates-v1.0`  
**Estado:** calibração técnica exploratória; não é resultado populacional nem validação semântica externa.

## O que foi verificado

- Os 26 eventos estruturados foram classificados sem falhas.
- O cenário estrito é subconjunto do cenário amplo para texto e siblings.
- Dez eventos contêm ao menos uma evidência textual estrita; 22 contêm evidência ampla.
- Foram produzidos 813 registros de evidência textual. O mesmo trecho pode aparecer nos dois cenários e em mais de um alvo; portanto, esse total não é número de linhas únicas nem pode ser somado como prevalência.
- Um evento adicionou dois siblings `.py` com shebang; ele é candidato estrito e amplo a mudança em artefato executável.
- A reexecução independente reproduziu exatamente:
  - eventos: `bed0fe90be17195d163a04ae672847163ef6281212bcdb69d095826727fca1bd`;
  - evidência textual: `475c8fd3c8964f9f8888cd567769920c000a4ea1805fa951c6bee912eddaf5dc`;
  - siblings: `8e87cae88a21124f0466cfb137cd80d67d560a32cdfa38d8aa7601441727acff`;
  - contagens: `171358b71e9ee866261094144cac79213b649520d8d0570527dfb1b0137c3dcb`.

### Contagens por evento na calibração

| Alvo/direção | Estrito | Amplo |
|---|---:|---:|
| comando adicionado | 4 | 20 |
| comando removido | 0 | 4 |
| acesso externo adicionado | 6 | 11 |
| acesso externo removido | 2 | 3 |
| referência a script adicionada | 1 | 13 |
| referência a script removida | 0 | 3 |
| sibling executável adicionado | 1 | 1 |

Os eventos são multirrótulo; linhas e colunas não devem ser somadas.

## O que foi apenas documentado

- **Estrito — comandos:** CLI conhecida no início de uma linha em região de código.
- **Amplo — comandos:** regra estrita ou linha com forma de comando em região de código.
- **Estrito — acesso externo:** token operacional como `curl`, `wget`, chamada de API, download/upload, SSH/SCP/rsync.
- **Amplo — acesso externo:** regra estrita ou URL com esquema explícito.
- **Estrito — scripts em texto:** invocação explícita de path com extensão de script/executável.
- **Amplo — scripts em texto:** regra estrita ou menção a path com extensão cadastrada.
- **Estrito — siblings:** modo Git `100755` ou shebang.
- **Amplo — siblings:** regra estrita ou extensão cadastrada.

## O que está planejado

1. ampliar fixtures de negativos difíceis e construções multilíngues;
2. definir amostra analítica maior, com seed e probabilidades registradas;
3. aplicar integralmente os classificadores RQ2/RQ3 nessa amostra;
4. calcular estimativas e intervalos somente depois de medir perdas e denominadores.

## O que permanece incerto

- validade semântica das regras, pois não haverá referência humana independente;
- taxas de falso positivo e falso negativo;
- cobertura de comandos não presentes no vocabulário estrito;
- executabilidade real e execução efetiva dos siblings;
- acesso de rede efetivamente realizado;
- prevalência de qualquer categoria na população.

## Artefatos

- implementação: `scripts/13_classify_rq3_behavioral_changes.py`;
- eventos: `outputs/rq3/behavioral_calibration_v3/rq3_behavioral_events.csv`;
- evidência textual: `outputs/rq3/behavioral_calibration_v3/rq3_text_evidence.csv`;
- evidência de siblings: `outputs/rq3/behavioral_calibration_v3/rq3_sibling_evidence.csv`;
- contagens: `outputs/rq3/behavioral_calibration_v3/rq3_candidate_counts.csv`;
- manifesto: `outputs/rq3/behavioral_calibration_v3/rq3_behavioral_manifest.json`.

A versão `v3` recompõe a calibração após a correção da leitura de siblings binários. Os quatro CSVs permaneceram byte a byte idênticos aos de `v2`; o novo manifesto liga as saídas ao checksum atual do script.

## Critério de conclusão desta etapa

A calibração automatizada de RQ3 está tecnicamente concluída porque regras, cenários, evidências, siblings, invariantes, saídas e repetição estão rastreados. RQ3 científica permanece pendente até aplicação em amostra apropriada e cálculo de estimativas; a ausência de validação humana continuará sendo ameaça à validade de construto.
