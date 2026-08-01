-- ============================================================
-- Données de référence minimales
-- ============================================================

INSERT INTO canal (nom)
VALUES
    ('streamlit'),
    ('mcp'),
    ('api')
ON CONFLICT (nom) DO NOTHING;

INSERT INTO modele_llm (provider, nom)
VALUES
    ('OpenAi', 'gpt-5-mini'),
    ('OpenAi', 'gpt-5'),
    ('KiloCode', 'mcp-retrieval')
ON CONFLICT (provider, nom) DO NOTHING;
