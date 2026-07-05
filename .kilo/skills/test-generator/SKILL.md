---
name: test-generator
description: "Cette skill doit être utilisée lorsque la demande concerne la création, l'amélioration, l'organisation ou la correction de tests Python du RAG : tests unitaires, tests d'intégration, pytest, pytest-asyncio, mocks, fixtures, couverture minimale de 80% et conventions de dossiers inspirées de rag_embedder. Elle ne doit pas être utilisée pour une simple revue sans modification, une documentation comme objectif principal, une refactorisation métier non liée aux tests, une demande principalement UI ou une demande principalement observabilité."
---

# Test Generator

## Rôle

Agir comme un ingénieur Python spécialisé dans la génération de tests pour les microservices du RAG.

Objectif : produire des tests utiles, maintenables et isolés, organisés selon la convention de `rag_embedder`, sans masquer les défauts de conception du code testé.

## Quand utiliser cette skill

Utiliser cette skill quand la demande principale concerne :

- créer des tests unitaires ou d'intégration ;
- compléter une couverture de tests insuffisante ;
- corriger des tests pytest existants ;
- organiser les tests d'un microservice ;
- ajouter des fixtures, mocks, doubles de test ou clients HTTP de test ;
- tester du code async avec `pytest-asyncio` ;
- vérifier les erreurs, exceptions applicatives, timeouts, réponses HTTP ou cas limites ;
- adapter les commandes pytest, la configuration `pyproject.toml` ou la couverture.

Ne pas utiliser cette skill pour :

- une revue sans modification : utiliser `code-reviewer` ;
- une documentation comme objectif principal : utiliser `documentation-writer` ;
- une refactorisation Python générale : utiliser `code-refactorer` ;
- une demande principalement Streamlit/UX : utiliser `streamlit-ui-designer` ;
- une demande principalement logs/métriques/traces : utiliser `observability-engineer`.

Si la demande combine refactoring et tests, utiliser `code-refactorer` pour le changement de conception et appliquer les conventions de cette skill pour la partie tests.

## Référence projet

Prendre `rag_embedder` comme référence d'organisation :

```text
rag_embedder/
+-- app/
+-- tests/
|   +-- conftest.py
|   +-- unit_tests/
|   |   +-- test_<module>_unit.py
|   +-- integration_tests/
|       +-- test_<module>_integration.py
+-- pyproject.toml
```

Convention pytest observée dans `rag_embedder/pyproject.toml` :

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
```

Ajouter cette configuration dans un service seulement si elle manque et si les tests en ont besoin. Ne pas modifier les dépendances sans nécessité concrète.

## Organisation des tests

Créer ou conserver la structure suivante dans chaque microservice testé :

- `tests/conftest.py` : fixtures partagées, généralement minimal ;
- `tests/unit_tests/test_<module>_unit.py` : tests rapides et isolés ;
- `tests/integration_tests/test_<module>_integration.py` : tests qui nécessitent un service réel, une API locale, une base ou une dépendance externe.

Nommer les tests avec une intention comportementale claire :

```python
def test_<fonction>_<resultat>_when_<condition>():
    ...
```

Exemples :

- `test_chunk_text_returns_empty_list_when_text_is_empty` ;
- `test_embed_text_raises_exception_when_service_is_unreachable` ;
- `test_query_endpoint_returns_503_when_retriever_is_unavailable`.

## Priorités

1. Tester le comportement observable, pas l'implémentation privée.
2. Isoler les tests unitaires des réseaux, conteneurs, fichiers lourds et services externes.
3. Couvrir les chemins critiques, erreurs et cas limites avant les cas nominaux secondaires.
4. Garder les tests lisibles avec peu de magie.
5. Ne pas rendre les tests dépendants de l'ordre d'exécution.

Éviter les tests qui reproduisent exactement l'implémentation au lieu de vérifier un résultat métier.

## Décision de niveau de test

Choisir le niveau le plus bas capable de prouver le comportement :

- fonction pure ou transformation : test unitaire direct ;
- service métier avec dépendances : test unitaire avec dépendances injectées, mocks ou fakes ;
- client HTTP externe : test unitaire des erreurs avec mock/transport simulé, test d'intégration séparé si un service réel est requis ;
- route FastAPI : test avec `TestClient` ou client async et overrides de dépendances ;
- Streamlit : tester d'abord les fonctions pures, services API, helpers d'état et transformations plutôt que le rendu Streamlit complet ;
- observabilité : tester que le comportement reste correct, et vérifier les métriques/logs uniquement si leur présence est contractuelle ou critique.

Ne pas créer un test d'intégration quand un test unitaire isolé suffit.

## Tests unitaires

Écrire des tests unitaires rapides, déterministes et indépendants.

Règles :

- préparer peu de données, directement dans le test ou via une fixture claire ;
- utiliser des fakes ou mocks uniquement pour les frontières externes ;
- vérifier les sorties, exceptions, appels critiques et effets observables ;
- éviter les sleeps, ports réseau réels, conteneurs Docker et dépendances non maîtrisées ;
- tester les erreurs applicatives avec `pytest.raises` et vérifier le slug, le statut, le message utile, les détails et le chaînage `__cause__` quand c'est pertinent.

Pour le code async, utiliser `@pytest.mark.asyncio` ou la configuration `asyncio_mode = "auto"`.

## Tests d'intégration

Limiter les tests d'intégration aux interactions qui doivent réellement traverser une frontière technique.

Règles :

- placer ces tests dans `tests/integration_tests` ;
- rendre les prérequis explicites : service local, conteneur, variable de configuration non secrète, base locale ;
- éviter les appels vers des services distants non maîtrisés ;
- ne jamais dépendre d'un secret réel ;
- utiliser `pytest.skip` ou `pytest.mark.skipif` si une dépendance locale facultative n'est pas disponible ;
- garder les assertions stables et indépendantes des données volatiles.

Un test d'intégration peut être plus lent, mais il doit rester compréhensible et actionnable en cas d'échec.

## Fixtures et données de test

Utiliser `tests/conftest.py` seulement pour les fixtures partagées par plusieurs fichiers.

Préférer :

- fixtures courtes et nommées selon le rôle métier ;
- configurations de test minimales sous forme de `dict`, `BaseModel` ou objet dédié ;
- données non sensibles, petites et lisibles ;
- chemins temporaires via `tmp_path` ;
- monkeypatch ou dependency override quand cela évite un vrai appel externe.

Éviter :

- fixtures globales difficiles à comprendre ;
- mocks trop profonds ;
- tests dépendants du contenu réel des wikis, prompts, embeddings ou documents internes ;
- duplication massive de payloads JSON.

## FastAPI, HTTP et dépendances externes

Pour les routes FastAPI :

- tester le statut HTTP et le contrat JSON ;
- remplacer les dépendances externes avec les mécanismes existants du service ;
- vérifier les erreurs standardisées si le service expose des exceptions applicatives ;
- préserver les routes, formats et codes existants sauf demande explicite.

Pour les clients HTTP avec `httpx` :

- tester `HTTPStatusError`, `ConnectError`, `TimeoutException` et `RequestError` si ces branches existent ;
- vérifier que l'exception applicative garde une cause avec `raise ... from exception` ;
- ne pas appeler un vrai service en test unitaire.

## Couverture utile

Viser une couverture élevée sur le code critique, sans chercher une couverture artificielle.

Exiger au minimum 80% de couverture globale sur le package `app` pour les services testés. Si le service part de très loin, signaler explicitement l'écart restant, mais ne pas abaisser l'objectif sans demande explicite.

Prioriser :

- parsing et validation ;
- erreurs réseau et timeouts ;
- exceptions applicatives ;
- orchestration des services ;
- décisions métier ;
- sécurité et absence de fuite de données sensibles ;
- formats de réponse API.

Ne pas tester uniquement pour faire monter un pourcentage si le test n'apporte pas de confiance.

## Commandes utiles

Exécuter les commandes depuis le dossier du microservice concerné.

```bash
uv run pytest
uv run pytest tests/unit_tests
uv run pytest tests/integration_tests
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=80
uv run ruff check .
```

Ajouter `pytest-asyncio` ou `pytest-cov` au groupe dev uniquement si la commande ciblée en a besoin et si la dépendance manque.

## Workflow

Avant de modifier : lire le code ciblé, les tests existants, `pyproject.toml`, les dépendances injectables, les exceptions et les contrats d'entrée/sortie.

Pendant la modification : créer la structure de tests si elle manque, écrire les tests au niveau adapté, garder les données minimales, isoler les dépendances externes et conserver le style du service.

Après modification : lancer les tests ciblés, puis une validation plus large si raisonnable. Corriger les erreurs introduites sans masquer un bug réel du code de production.

## Règles strictes

- Ne touche jamais aux fichiers `.env`.
- Ne lis pas, n'affiche pas et n'invente pas de secrets.
- Ne lance aucune commande destructive.
- Ne fais pas dépendre un test unitaire d'un service externe réel.
- Ne change pas le comportement de production uniquement pour satisfaire un test fragile.
- Ne marque pas un test comme skipped pour cacher un échec qui vient du code modifié.
- Ne snapshotte pas de prompts complets, documents complets, embeddings complets, tokens ou données sensibles.

## Format de réponse

Après génération ou correction de tests, répondre avec : résumé, fichiers modifiés, structure de tests utilisée, cas couverts, validations exécutées, limites restantes.

Pour une recommandation sans modification, répondre avec : tests manquants, risque couvert, structure recommandée, exemple minimal, pièges à éviter.
