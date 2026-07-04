-- ============================================================
-- Index utiles pour les futures requêtes d'analyse
-- ============================================================

CREATE INDEX idx_session_usage_utilisateur_id
    ON session_usage(utilisateur_id);

CREATE INDEX idx_session_usage_canal_id
    ON session_usage(canal_id);

CREATE INDEX idx_interaction_rag_session_id
    ON interaction_rag(session_id);

CREATE INDEX idx_interaction_rag_cree_le
    ON interaction_rag(cree_le);

CREATE INDEX idx_interaction_rag_statut
    ON interaction_rag(statut);

CREATE INDEX idx_consommation_tokens_modele_id
    ON consommation_tokens(modele_id);

CREATE INDEX idx_interaction_rag_chunk_interaction_id
    ON interaction_rag_chunk(interaction_id);

CREATE INDEX idx_interaction_rag_chunk_chunk_id
    ON interaction_rag_chunk(chunk_id);

CREATE INDEX idx_chunk_page_chemin
    ON chunk(page_chemin);

CREATE INDEX idx_avis_note
    ON avis(note);

CREATE INDEX idx_quota_utilisateur_utilisateur_id
    ON quota_utilisateur(utilisateur_id);

CREATE INDEX idx_quota_utilisateur_dates
    ON quota_utilisateur(date_debut, date_fin);