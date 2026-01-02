from pydantic import BaseModel

# Métriques d'évaluation pour la performance de la recherche (Retrieval).
class RetrievalEvaluationBase(BaseModel):
    # Mean Reciprocal Rank - Moyenne des inverses des rangs.
    mrr: float
    # Normalized Discounted Cumulative Gain - Pertinence positionnelle.
    ndcg: float 
    # Nombre de mots-clés trouvés dans les documents.
    keywords_found: int
    # Nombre total de mots-clés attendus.
    total_keywords: int
    # Pourcentage de couverture des mots-clés.
    keyword_coverage: float