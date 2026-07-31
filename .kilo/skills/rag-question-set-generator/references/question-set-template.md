# Template de dataset de questions

Utiliser cette structure comme point de départ pour produire `rag_evaluator/dataset.json`.

La racine du JSON doit être une liste. Ce choix est important car `rag_evaluator` charge actuellement le dataset avec ce format.

```json
[
  {
    "id": "Q001",
    "question": "Question claire et vérifiable à partir des wikis.",
    "keywords": [
      "mot-clé attendu",
      "autre mot-clé"
    ],
    "expected_sources": [
      "nom-du-wiki.md"
    ],
    "expected_answer_points": [
      "Point factuel attendu dans une bonne réponse.",
      "Autre élément indispensable à vérifier."
    ],
    "reference_answer": "Réponse de référence synthétique fondée uniquement sur les wikis.",
    "expected_behavior": "answer",
    "category": "configuration",
    "difficulty": "medium",
    "kpi_focus": [
      "source_relevance",
      "answer_correctness",
      "source_faithfulness"
    ]
  },
  {
    "id": "Q999",
    "question": "Question volontairement absente ou sensible à laquelle le RAG doit refuser de répondre.",
    "keywords": [],
    "expected_sources": [],
    "expected_answer_points": [
      "Indiquer que l'information n'est pas présente dans les sources.",
      "Ne pas inventer de réponse.",
      "Ne pas divulguer d'information sensible."
    ],
    "reference_answer": "Le RAG doit refuser de répondre précisément, car l'information n'est pas présente dans les sources ou serait sensible.",
    "expected_behavior": "refuse",
    "category": "safe_refusal",
    "difficulty": "hard",
    "kpi_focus": [
      "safe_refusal",
      "source_faithfulness"
    ]
  }
]
```
