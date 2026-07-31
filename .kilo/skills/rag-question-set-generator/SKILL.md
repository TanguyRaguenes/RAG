---
name: rag-question-set-generator
description: Cette skill doit être utilisée lorsque la demande concerne la création, l'amélioration, la vérification ou l'écriture dans `rag_evaluator/dataset.json` d'un jeu de questions de référence pour évaluer le RAG avec `rag_evaluator`, notamment à partir des wikis d'exemple stockés dans `/Users/tanguyraguenes/RAG/wikis_exemple` pour la démarche PDCA du M3 EADL.
---

# RAG Question Set Generator

## Rôle

Construire un jeu de questions de référence exploitable par `rag_evaluator` pour mesurer la qualité du RAG interne, produire une baseline et alimenter une démarche d'amélioration continue PDCA.

Garder les wikis comme source documentaire externe. Ne pas copier le contenu complet des wikis dans la skill.

## Quand utiliser cette skill

Utiliser cette skill pour :

- générer un dataset de questions à partir des wikis du projet ;
- écrire ou mettre à jour `rag_evaluator/dataset.json` lorsque la demande le précise ;
- préparer une baseline qualité pour le M3 EADL ;
- relier des questions aux documents sources attendus ;
- définir des critères de réponse attendue ;
- vérifier qu'un jeu de questions couvre plusieurs thèmes, difficultés et KPI ;
- produire un format de sortie utilisable ou adaptable pour `rag_evaluator`.

Ne pas utiliser cette skill pour modifier le code de `rag_evaluator`, générer des tests unitaires ou réaliser une refactorisation Python.

## Source documentaire

Utiliser par défaut :

```text
/Users/tanguyraguenes/RAG/wikis_exemple
```

Avant de générer un dataset, inspecter la structure du dossier et identifier les fichiers Markdown disponibles.

Le dataset de sortie principal est :

```text
/Users/tanguyraguenes/RAG/rag_evaluator/dataset.json
```

## Workflow

1. Charger `references/question-set-methodology.md`.
2. Inspecter les wikis source sans les dupliquer dans la skill.
3. Inspecter le format réellement attendu par `rag_evaluator` avant d'écrire le fichier.
4. Identifier les thèmes importants, procédures, concepts, configurations et limites.
5. Générer des questions traçables vers un ou plusieurs documents sources.
6. Associer chaque question à des points de réponse attendus.
7. Varier les catégories, difficultés et KPI ciblés.
8. Ajouter quelques questions de refus lorsque le dataset doit couvrir le KPI `safe_refusal`.
9. Produire un JSON dont la racine est une liste d'objets, compatible avec `rag_evaluator`.
10. Valider le JSON et signaler les points nécessitant une validation humaine.

## Critères qualité

- Préférer des questions concrètes et vérifiables.
- Éviter les questions trop générales ou purement théoriques.
- Éviter les questions dont la réponse n'est pas présente dans les wikis.
- Relier chaque question à une source attendue.
- Inclure des points de réponse attendus, pas seulement une réponse longue rédigée.
- Prévoir des questions simples, intermédiaires et difficiles.
- Couvrir les KPI utiles au PDCA : pertinence documentaire, réponse correcte, fidélité aux sources, refus de réponse et latence si mesurable.
- Conserver les champs actuellement exploités par `rag_evaluator` : `question`, `keywords`, `reference_answer`, `category`.
- Ajouter les champs de pilotage PDCA : `id`, `expected_sources`, `expected_answer_points`, `expected_behavior`, `difficulty`, `kpi_focus`.

## Ressources

- `references/question-set-methodology.md` : méthode détaillée de génération et de revue.
- `references/question-set-template.md` : structure JSON recommandée pour le dataset.

## Sortie attendue

Produire ou mettre à jour un jeu de questions exploitable, accompagné d'un court bilan indiquant les thèmes couverts, les fichiers sources utilisés, les KPI couverts, les limites et les points à valider manuellement avant utilisation dans le rapport M3.
