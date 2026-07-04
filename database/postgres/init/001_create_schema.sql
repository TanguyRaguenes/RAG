-- ============================================================
-- Table : utilisateur
-- Objectif : identifier un utilisateur sans stocker son email
-- id = HMAC-SHA256(email normalisé)
-- ============================================================

CREATE TABLE utilisateur (
    id TEXT PRIMARY KEY,

    CONSTRAINT chk_utilisateur_id_hash
        CHECK (id ~ '^[a-f0-9]{64}$')
);

-- ============================================================
-- Table : canal
-- Objectif : identifier le canal d'utilisation du RAG
-- ============================================================

CREATE TABLE canal (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom VARCHAR(50) NOT NULL UNIQUE
);

-- ============================================================
-- Table : session_usage
-- Objectif : représenter une session d'utilisation du RAG
-- ============================================================

CREATE TABLE session_usage (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utilisateur_id TEXT NOT NULL,
    canal_id INTEGER NOT NULL,
    demarree_le TIMESTAMPTZ NOT NULL DEFAULT now(),
    finie_le TIMESTAMPTZ NULL,

    CONSTRAINT fk_session_usage_utilisateur
        FOREIGN KEY (utilisateur_id)
        REFERENCES utilisateur(id),

    CONSTRAINT fk_session_usage_canal
        FOREIGN KEY (canal_id)
        REFERENCES canal(id),

    CONSTRAINT chk_session_usage_dates
        CHECK (finie_le IS NULL OR finie_le >= demarree_le)
);

-- ============================================================
-- Table : interaction_rag
-- Objectif : stocker une question/réponse RAG
-- ============================================================

CREATE TABLE interaction_rag (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    reponse TEXT NULL,
    statut VARCHAR(30) NOT NULL,
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now(),
    duree_ms INTEGER NULL,

    CONSTRAINT fk_interaction_rag_session
        FOREIGN KEY (session_id)
        REFERENCES session_usage(id),

    CONSTRAINT chk_interaction_rag_statut
        CHECK (statut IN ('success', 'error', 'timeout', 'quota_exceeded')),

    CONSTRAINT chk_interaction_rag_duree
        CHECK (duree_ms IS NULL OR duree_ms >= 0)
);

-- ============================================================
-- Table : modele_llm
-- Objectif : référencer les modèles LLM utilisés
-- ============================================================

CREATE TABLE modele_llm (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    nom VARCHAR(100) NOT NULL,

    CONSTRAINT uq_modele_llm_provider_nom
        UNIQUE (provider, nom)
);

-- ============================================================
-- Table : tarif_modele
-- Objectif : stocker les tarifs des modèles dans le temps
-- ============================================================

CREATE TABLE tarif_modele (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    modele_id INTEGER NOT NULL,
    prix_input_million NUMERIC(12, 6) NOT NULL,
    prix_output_million NUMERIC(12, 6) NOT NULL,
    date_debut TIMESTAMPTZ NOT NULL,
    date_fin TIMESTAMPTZ NULL,

    CONSTRAINT fk_tarif_modele_modele
        FOREIGN KEY (modele_id)
        REFERENCES modele_llm(id),

    CONSTRAINT chk_tarif_modele_prix_input
        CHECK (prix_input_million >= 0),

    CONSTRAINT chk_tarif_modele_prix_output
        CHECK (prix_output_million >= 0),

    CONSTRAINT chk_tarif_modele_dates
        CHECK (date_fin IS NULL OR date_fin > date_debut)
);

-- ============================================================
-- Table : consommation_tokens
-- Objectif : stocker la consommation de tokens d'une interaction
-- ============================================================

CREATE TABLE consommation_tokens (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    interaction_id BIGINT NOT NULL UNIQUE,
    modele_id INTEGER NOT NULL,
    prompt_tokens BIGINT NOT NULL,
    completion_tokens BIGINT NOT NULL,
    total_tokens BIGINT NOT NULL,
    cout_estime_eur NUMERIC(12, 6) NULL,

    CONSTRAINT fk_consommation_tokens_interaction
        FOREIGN KEY (interaction_id)
        REFERENCES interaction_rag(id),

    CONSTRAINT fk_consommation_tokens_modele
        FOREIGN KEY (modele_id)
        REFERENCES modele_llm(id),

    CONSTRAINT chk_consommation_prompt_tokens
        CHECK (prompt_tokens >= 0),

    CONSTRAINT chk_consommation_completion_tokens
        CHECK (completion_tokens >= 0),

    CONSTRAINT chk_consommation_total_tokens
        CHECK (total_tokens >= 0),

    CONSTRAINT chk_consommation_total_coherent
        CHECK (total_tokens >= prompt_tokens + completion_tokens),

    CONSTRAINT chk_consommation_cout
        CHECK (cout_estime_eur IS NULL OR cout_estime_eur >= 0)
);

-- ============================================================
-- Table : chunk
-- Objectif : stocker les chunks documentaires utilisés par le RAG
-- ============================================================

CREATE TABLE chunk (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_chunk_id VARCHAR(255) NOT NULL UNIQUE,
    page_titre TEXT NOT NULL,
    page_chemin TEXT NOT NULL,
    contenu TEXT NOT NULL
);

-- ============================================================
-- Table : interaction_rag_chunk
-- Objectif : associer une interaction RAG aux chunks utilisés
-- ============================================================

CREATE TABLE interaction_rag_chunk (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    interaction_id BIGINT NOT NULL,
    chunk_id BIGINT NOT NULL,
    rang INTEGER NOT NULL,
    score NUMERIC(10, 6) NULL,

    CONSTRAINT fk_interaction_rag_chunk_interaction
        FOREIGN KEY (interaction_id)
        REFERENCES interaction_rag(id),

    CONSTRAINT fk_interaction_rag_chunk_chunk
        FOREIGN KEY (chunk_id)
        REFERENCES chunk(id),

    CONSTRAINT uq_interaction_rag_chunk
        UNIQUE (interaction_id, chunk_id),

    CONSTRAINT chk_interaction_rag_chunk_rang
        CHECK (rang > 0)
);

-- ============================================================
-- Table : avis
-- Objectif : stocker le feedback utilisateur sur une réponse
-- Convention :
--   1  = like
--  -1  = dislike
-- ============================================================

CREATE TABLE avis (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    interaction_id BIGINT NOT NULL UNIQUE,
    note INTEGER NOT NULL,
    commentaire TEXT NULL,

    CONSTRAINT fk_avis_interaction
        FOREIGN KEY (interaction_id)
        REFERENCES interaction_rag(id),

    CONSTRAINT chk_avis_note
        CHECK (note IN (-1, 1))
);

-- ============================================================
-- Table : quota_utilisateur
-- Objectif : définir les quotas de tokens par utilisateur et par période
-- ============================================================

CREATE TABLE quota_utilisateur (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utilisateur_id TEXT NOT NULL,
    max_tokens BIGINT NOT NULL,
    date_debut TIMESTAMPTZ NOT NULL,
    date_fin TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_quota_utilisateur_utilisateur
        FOREIGN KEY (utilisateur_id)
        REFERENCES utilisateur(id),

    CONSTRAINT chk_quota_max_tokens
        CHECK (max_tokens > 0),

    CONSTRAINT chk_quota_dates
        CHECK (date_fin > date_debut)
);