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

INSERT INTO tarif_modele (
    modele_id,
    prix_input_million,
    prix_output_million,
    date_debut,
    date_fin
)
SELECT
    id,
    0.66,
    3.94,
    TIMESTAMPTZ '2026-07-04 00:00:00+02',
    NULL
FROM modele_llm
WHERE provider = 'OpenAi'
  AND nom = 'gpt-5-mini'
  AND NOT EXISTS (
      SELECT 1
      FROM tarif_modele
      WHERE modele_id = modele_llm.id
        AND date_fin IS NULL
  );

INSERT INTO tarif_modele (
    modele_id,
    prix_input_million,
    prix_output_million,
    date_debut,
    date_fin
)
SELECT
    id,
    4.37,
    26.25,
    TIMESTAMPTZ '2026-07-04 00:00:00+02',
    NULL
FROM modele_llm
WHERE provider = 'OpenAi'
  AND nom = 'gpt-5'
  AND NOT EXISTS (
      SELECT 1
      FROM tarif_modele
      WHERE modele_id = modele_llm.id
        AND date_fin IS NULL
  );

INSERT INTO tarif_modele (
    modele_id,
    prix_input_million,
    prix_output_million,
    date_debut,
    date_fin
)
SELECT
    id,
    0.000000,
    0.000000,
    TIMESTAMPTZ '2026-07-04 00:00:00+02',
    NULL
FROM modele_llm
WHERE provider = 'KiloCode'
  AND nom = 'mcp-retrieval'
  AND NOT EXISTS (
      SELECT 1
      FROM tarif_modele
      WHERE modele_id = modele_llm.id
        AND date_fin IS NULL
  );
