#!/usr/bin/env python3
"""
gitskills_phase1_analysis.py
-------------------------------------------------------------------------
Script de extração de métricas e ajuste do Hurdle Model para a Fase 1 (RQ1)
do projeto de pesquisa: "Da cópia à divergência: Reutilização, propagação 
e evolução de Agent Skills no GitHub".

Baseado nas especificações do dataset GitSkills (Destefanis et al., 2026) 
e na proposta metodológica do projeto.
-------------------------------------------------------------------------
"""

import os
import re
import math
import sqlite3
import yaml
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


def calculate_flesch_reading_ease(text: str) -> float:
    """
    Calcula o índice Flesch Reading Ease para medir a legibilidade 
    das instruções em linguagem natural da skill.
    """
    if not text or not text.strip():
        return 0.0
    
    # Remove blocos de código markdown e símbolos especiais
    clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    clean_text = re.sub(r'`.*?`', '', clean_text)
    clean_text = re.sub(r'[#*_\-\[\]\(\)]', ' ', clean_text)
    
    words = re.findall(r'\b\w+\b', clean_text)
    sentences = re.split(r'[.!?]+', clean_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    num_words = len(words)
    num_sentences = max(len(sentences), 1)
    
    if num_words == 0:
        return 0.0
    
    def count_syllables(word):
        word = word.lower()
        if len(word) <= 3:
            return 1
        word = re.sub(r'(?:[^laeiouy]es|ed|[^laeiouy]e)$', '', word)
        word = re.sub(r'^y', '', word)
        syllables = len(re.findall(r'[aeiouy]{1,2}', word))
        return max(syllables, 1)

    num_syllables = sum(count_syllables(w) for w in words)
    score = 206.835 - (1.015 * (num_words / num_sentences)) - (84.6 * (num_syllables / num_words))
    return round(score, 2)


def extract_textual_features(text: str, front_matter_raw: str = None) -> dict:
    """
    Extrai métricas textuais do arquivo SKILL.md e de seu YAML front matter.
    """
    text = text or ""
    desc_length = 0
    name_length = 0
    
    if front_matter_raw:
        try:
            fm_data = yaml.safe_load(front_matter_raw)
            if isinstance(fm_data, dict):
                desc_length = len(str(fm_data.get('description', '')))
                name_length = len(str(fm_data.get('name', '')))
        except Exception:
            pass
            
    urls_count = len(re.findall(r'https?://[^\s><"]+|www\.[^\s><"]+', text))
    code_blocks_count = len(re.findall(r'```', text)) // 2
    inline_code_count = len(re.findall(r'`[^`]+`', text))
    sections_count = len(re.findall(r'^#{1,6}\s+', text, re.MULTILINE))
    lists_count = len(re.findall(r'^\s*[\*\-\+]\s+|\s*\d+\.\s+', text, re.MULTILINE))
    readability = calculate_flesch_reading_ease(text)
    
    return {
        "text_length": len(text),
        "word_count": len(text.split()),
        "description_length": desc_length,
        "name_length": name_length,
        "urls_count": urls_count,
        "code_blocks_count": code_blocks_count,
        "inline_code_count": inline_code_count,
        "sections_count": sections_count,
        "lists_count": lists_count,
        "readability_flesch": readability
    }


def extract_dataset(db_path: str, output_csv: str = "phase1_skills_dataset.csv", limit: int = None) -> pd.DataFrame:
    """
    Conecta ao banco SQLite do GitSkills (44 GB), executa a consulta agregada 
    por content_hash e gera a tabela de métricas explicativas.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Arquivo do banco de dados '{db_path}' não foi encontrado.")

    print(f"Conectando ao banco SQLite: {db_path}...")
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT 
        a.content_hash,
        COUNT(DISTINCT a.repository) AS reuse_count,
        a.text,
        a.front_matter,
        a.body_size,
        a.has_scripts,
        a.has_references,
        a.first_commit_date,
        a.last_commit_date,
        a.commit_count,
        r.stars,
        r.primary_language,
        r.is_fork,
        r.created_at AS repo_created_at,
        r.pushed_at AS repo_pushed_at
    FROM artifacts a
    LEFT JOIN repos r ON a.repository = r.repository
    WHERE a.is_representative = 1
    GROUP BY a.content_hash
    """
    if limit:
        query += f" LIMIT {limit}"

    print("Executando consulta SQL no banco GitSkills...")
    df_raw = pd.read_sql_query(query, conn)
    conn.close()

    print(f"Extraindo métricas de {len(df_raw)} conteúdos distintos de skills...")
    features_list = []
    
    for idx, row in df_raw.iterrows():
        txt_feats = extract_textual_features(row['text'], row['front_matter'])
        
        reuse_cnt = row['reuse_count']
        is_reused = 1 if reuse_cnt > 1 else 0
        
        feat = {
            "content_hash": row['content_hash'],
            "reuse_count": reuse_cnt,           # VD: Contagem de Reúso
            "is_reused": is_reused,             # VD: Probabilidade de Adoção P(reuse > 1)
            "body_size": row['body_size'],
            "has_scripts": 1 if row['has_scripts'] else 0,
            "has_references": 1 if row['has_references'] else 0,
            "commit_count": row['commit_count'] or 1,
            "repo_stars": row['stars'] or 0,
            "primary_language": row['primary_language'] or 'Unknown',
            "is_fork": 1 if row['is_fork'] else 0,
        }
        feat.update(txt_feats)
        features_list.append(feat)

    df_final = pd.DataFrame(features_list)
    df_final.to_csv(output_csv, index=False)
    print(f"Dataset salvo em '{output_csv}' com {len(df_final)} registros.")
    return df_final


def fit_hurdle_model(csv_path: str):
    """
    Ajusta o Hurdle Model de 2 partes (Regressão Logística + Binomial Negativa).
    """
    print(f"Carregando dataset: {csv_path}...")
    df = pd.read_csv(csv_path)

    df['log_stars'] = df['repo_stars'].apply(lambda x: math.log1p(x))
    
    # Parte 1: Regressão Logística P(Reuse > 1)
    print("\n=======================================================")
    print("PARTE 1: Regressão Logística - Probabilidade de Adoção P(Reuse > 1)")
    print("=======================================================")
    formula_logit = (
        "is_reused ~ text_length + description_length + readability_flesch + "
        "urls_count + code_blocks_count + sections_count + lists_count + "
        "has_scripts + has_references + log_stars + is_fork + C(primary_language)"
    )
    model_logit = smf.logit(formula_logit, data=df).fit()
    print(model_logit.summary())

    # Odds Ratios e IC 95%
    params = model_logit.params
    conf = model_logit.conf_int()
    conf['Odds Ratio'] = params
    conf.columns = ['2.5%', '97.5%', 'Odds Ratio']
    odds_ratios = conf.applymap(lambda x: math.exp(x))
    print("\n--- Odds Ratios (IC 95%) ---")
    print(odds_ratios)

    # Parte 2: Binomial Negativa (Contagem entre reutilizadas)
    df_reused = df[df['is_reused'] == 1].copy()
    print("\n=======================================================")
    print(f"PARTE 2: Regressão Binomial Negativa - Intensidade do Reúso (N = {len(df_reused)})")
    print("=======================================================")
    formula_negbin = (
        "reuse_count ~ text_length + description_length + readability_flesch + "
        "urls_count + code_blocks_count + sections_count + lists_count + "
        "has_scripts + has_references + log_stars + is_fork + C(primary_language)"
    )
    model_negbin = smf.glm(
        formula_negbin, 
        data=df_reused, 
        family=sm.families.NegativeBinomial()
    ).fit()
    print(model_negbin.summary())


if __name__ == "__main__":
    import sys
    print("GitSkills Phase 1 Extraction & Modeling Script")
    print("Uso: python gitskills_phase1_analysis.py <caminho_sqlite>")
    if len(sys.argv) > 1:
        sqlite_file = sys.argv[1]
        extract_dataset(sqlite_file, "phase1_skills_dataset.csv")
        fit_hurdle_model("phase1_skills_dataset.csv")
