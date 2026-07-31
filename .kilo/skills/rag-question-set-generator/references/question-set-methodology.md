# Méthodologie de génération du jeu de questions RAG

## Objectif

Construire un jeu de questions de référence pour mesurer la qualité du RAG interne avec `rag_evaluator` dans une démarche PDCA.

Le dataset doit permettre de répondre à quatre besoins :

- établir une baseline initiale ;
- comparer une modification avant/après ;
- identifier les faiblesses du RAG ;
- produire des preuves exploitables pour le M3 EADL.

## Source par défaut

Les wikis source sont stockés ici :

```text
/Users/tanguyraguenes/RAG/wikis_exemple
```

Ne pas copier les wikis dans la skill. Lire les fichiers au moment de générer le dataset afin de garder une source unique et à jour.

## Sortie par défaut

Lorsque la demande indique de stocker le dataset dans l'évaluateur, écrire le fichier ici :

```text
/Users/tanguyraguenes/RAG/rag_evaluator/dataset.json
```

Le JSON doit avoir une liste comme racine, car `rag_evaluator` charge actuellement une liste d'objets.

Conserver au minimum les champs utilisés par le service actuel :

- `question` ;
- `keywords` ;
- `reference_answer` ;
- `category`.

Ajouter les champs utiles au PDCA et aux évolutions de l'évaluateur :

- `id` : identifiant stable de la question ;
- `expected_sources` : fichiers Markdown attendus dans le top-k ;
- `expected_answer_points` : critères factuels d'une bonne réponse ;
- `expected_behavior` : `answer` ou `refuse` ;
- `difficulty` : `easy`, `medium` ou `hard` ;
- `kpi_focus` : KPI principalement évalués.

## Étapes recommandées

### 1. Cartographier les wikis

Identifier :

- les fichiers Markdown disponibles ;
- les thèmes principaux ;
- les procédures importantes ;
- les configurations ;
- les concepts métier ou techniques ;
- les limites, prérequis ou erreurs fréquentes.

### 2. Sélectionner les thèmes

Prioriser les contenus qui ont une valeur pour l'évaluation :

- informations que le RAG doit savoir retrouver ;
- procédures que les développeurs peuvent demander ;
- informations avec une source documentaire claire ;
- sujets permettant de vérifier la fidélité aux sources.

Éviter les contenus trop anecdotiques ou difficiles à vérifier.

### 3. Générer les questions

Varier les formes de questions :

- définition : "Qu'est-ce que ... ?" ;
- procédure : "Comment configurer ... ?" ;
- diagnostic : "Que faire si ... ?" ;
- comparaison : "Quelle est la différence entre ... ?" ;
- contrainte : "Quelles sont les limites de ... ?".

Chaque question de type `answer` doit avoir une réponse présente dans les wikis.

Ajouter quelques questions de type `refuse` lorsque le dataset doit mesurer la prudence du système. Ces questions doivent porter sur des informations absentes ou sensibles, par exemple un mot de passe, une clé API ou une procédure non documentée. Pour ces cas, `expected_sources` et `keywords` peuvent rester vides.

### 4. Associer les sources attendues

Pour chaque question, renseigner :

- `expected_sources` : fichier ou fichiers Markdown qui doivent être retrouvés ;
- `expected_answer_points` : points factuels attendus dans une bonne réponse ;
- `category` : thème ou type de question ;
- `difficulty` : `easy`, `medium` ou `hard` ;
- `kpi_focus` : KPI principalement évalués.

### 5. Contrôler la qualité

Vérifier que le dataset contient :

- des questions non ambiguës ;
- des réponses vérifiables ;
- des sources attendues exactes ;
- plusieurs thèmes ;
- plusieurs niveaux de difficulté ;
- quelques cas où le RAG doit rester prudent si les sources sont insuffisantes ;
- un champ `expected_sources` cohérent avec les fichiers Markdown présents ;
- des `expected_answer_points` assez précis pour guider un LLM as a judge.

## KPI recommandés

Utiliser principalement :

- `source_relevance` : le bon document est-il remonté dans le top-k ?
- `answer_correctness` : la réponse contient-elle les points attendus ?
- `source_faithfulness` : la réponse reste-t-elle fidèle aux sources ?
- `safe_refusal` : le RAG refuse-t-il correctement quand la source est insuffisante ?
- `latency` : le temps de réponse reste-t-il acceptable, si la mesure est disponible ?

## Taille du dataset

Pour démarrer : 10 à 20 questions.

Pour une première baseline PDCA : environ 20 à 30 questions, dont quelques cas de refus.

Pour une preuve M3 solide : viser environ 50 questions après validation manuelle.

Mieux vaut un petit dataset fiable, sourcé et relu qu'un grand dataset approximatif.

## Validation humaine

Signaler les questions à valider lorsque :

- la source documentaire est ambiguë ;
- plusieurs réponses sont possibles ;
- le document contient une information obsolète ;
- les points attendus nécessitent une interprétation métier.

Le rapport M3 peut indiquer que le dataset a été généré avec assistance IA puis validé humainement.

## Validation technique

Après écriture du dataset :

```bash
python3 -m json.tool rag_evaluator/dataset.json
```

Lancer ensuite les tests ciblés de chargement du dataset si le microservice n'a pas changé :

```bash
uv run --with pytest-asyncio pytest -q tests/unit_tests/test_evaluating_service_unit.py
```
