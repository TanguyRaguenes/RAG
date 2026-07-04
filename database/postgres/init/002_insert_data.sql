-- ============================================================
-- Données de référence minimales
-- ============================================================

INSERT INTO canal (nom)
VALUES
    ('streamlit'),
    ('mcp'),
    ('api')
ON CONFLICT (nom) DO NOTHING;