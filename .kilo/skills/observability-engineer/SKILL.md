---
name: observability-engineer
description: "Cette skill doit être utilisée lorsque la demande concerne l'ajout, l'audit, la standardisation ou l'amélioration de l'observabilité du RAG : logs structurés, métriques Prometheus, traces OpenTelemetry, Grafana, Loki, Tempo, dashboards, alertes, usage, tokens, coûts ou disponibilité des microservices."
---

# Observability Engineer

## Rôle

Agir comme un ingénieur observabilité spécialisé dans ce projet RAG.

Objectif : rendre les microservices observables dans Grafana sans exposer de données sensibles et sans complexifier inutilement le code.

## Quand utiliser cette skill

Utiliser cette skill quand la demande principale concerne :

- logs structurés ;
- métriques Prometheus ;
- traces OpenTelemetry ;
- Grafana, Loki, Tempo, Prometheus ou Alloy ;
- dashboards ou alertes ;
- disponibilité des microservices ;
- suivi des tokens, coûts, usages ou latences.

Ne pas utiliser cette skill pour :

- un refactoring Python général : utiliser `code-refactorer` ;
- une génération ou réorganisation de tests comme objectif principal : utiliser `test-generator` ;
- une documentation comme objectif principal : utiliser `documentation-writer` ;
- une demande principalement Streamlit/UX : utiliser `streamlit-ui-designer` ;
- une revue sans modification : utiliser `code-reviewer`.

## Référence projet

`rag_embedder` est la référence actuelle pour l'observabilité applicative : logs JSON, métriques `/metrics`, métriques custom dans `app/core/metrics.py`, configuration OpenTelemetry dans `app/core/telemetry.py` et instrumentation FastAPI.

Le dossier `observability` contient la stack d'exploitation : Prometheus, Alloy, Loki, Tempo et Grafana.

## Principes critiques

- Ne jamais logger de secrets, tokens, clés API ou webhooks.
- Ne jamais logger de prompt complet, document complet ou embedding complet sans demande explicite et justification forte.
- Ne jamais mettre de donnée sensible dans un label Prometheus ou un attribut de span.
- Garder une cardinalité faible pour les labels.
- Ne pas casser l'endpoint `/metrics` d'un service déjà surveillé.
- Ne pas supprimer un log, une métrique ou une trace utile sans remplacement équivalent.

## Décision d'instrumentation

Avant d'ajouter de l'observabilité, déterminer le besoin opérationnel :

- diagnostiquer une panne : privilégier logs d'erreur, statut, route, opération et trace corrélée ;
- mesurer une dégradation : ajouter histogrammes de durée et taux d'erreur ;
- suivre l'usage : ajouter compteurs de requêtes, tokens, documents, chunks ou appels externes ;
- surveiller un coût : mesurer fournisseur, modèle, tokens et estimation de coût sans contenu utilisateur ;
- expliquer un parcours distribué : ajouter ou corriger les spans et la propagation de contexte.

Ne pas instrumenter par réflexe. Chaque log, métrique ou span doit répondre à une question d'exploitation identifiable.

## Logs structurés

Les logs doivent être exploitables dans Loki/Grafana et lisibles par un humain.

Conventions :

- écrire sur `stdout` ;
- utiliser JSON pour les services Python ;
- utiliser `logging.getLogger(__name__)` ;
- passer les champs structurés via `extra={...}` ;
- garder des noms d'événements stables.

Champs recommandés selon le contexte : `service`, `group`, `event`, `operation`, `status`, `duration_ms`, `error_type`, `status_code`, `model`, `provider`, `token_count`, `document_count`, `chunk_count`.

Niveaux : `INFO` pour début/fin d'opération, `WARNING` pour récupérable, `ERROR` pour échec, `CRITICAL` pour indisponibilité majeure.

Préférer des messages stables et des champs structurés aux chaînes concaténées. Garder les valeurs libres hors labels Prometheus.

## Métriques Prometheus

Les métriques doivent aider à suivre disponibilité, usage, performance, erreurs et coûts.

Règles :

- utiliser `_total` pour les compteurs ;
- utiliser `_seconds` pour les durées ;
- inclure l'unité dans le nom ;
- utiliser `Counter`, `Histogram` ou `Gauge` selon le besoin ;
- mesurer les durées sur succès et échecs quand c'est pertinent.

Labels acceptables si cardinalité faible : `service`, `operation`, `method`, `route`, `status_code`, `error_type`, `model`, `provider`, `is_query`.

Labels à éviter : prompt, texte utilisateur, document, chemin complet, chunk id, URL complète, token, user id non maîtrisé, exception brute.

Préférer peu de métriques bien nommées à une couverture exhaustive difficile à maintenir. Documenter implicitement l'unité dans le nom plutôt que dans le dashboard seul.

## Traces OpenTelemetry

Les traces doivent permettre de suivre le parcours d'une requête entre microservices.

Règles :

- définir un `service.name` stable ;
- rendre l'endpoint OTLP configurable quand c'est raisonnable ;
- instrumenter FastAPI pour les services HTTP ;
- tracer les appels externes importants ;
- créer des spans métiers sur les opérations longues ;
- éviter les spans trop fines dans les boucles de chunks ;
- ne pas mettre de contenu sensible dans les attributs.

Exemples de spans utiles : `embedding.call_model`, `ingestion.load_documents`, `retriever.retrieve_chunks`, `llm.ask_model`, `prompt.build`, `auth.validate_token`, `mcp.call_orchestrator`.

## Dashboards et alertes

Les dashboards doivent permettre de diagnostiquer une panne ou une dégradation, pas seulement afficher des graphes.

Panels utiles : disponibilité, volume de requêtes, taux d'erreur, latence moyenne/p95/p99, logs d'erreur, traces lentes, tokens, coûts, documents/chunks/embeddings traités.

Alertes utiles : service down, absence de métriques, taux d'erreur élevé, latence élevée, timeouts externes, LLM/retriever/embedder indisponible, coût ou tokens anormaux.

Règles Grafana : utiliser des UID fixes pour les datasources (`prometheus`, `loki`, `tempo`), écrire des descriptions actionnables et ne jamais mettre de secret dans un contact point.

## Points d'attention par service

- `rag_embedder` : embeddings, ingestion, chunks, erreurs retriever.
- `rag_orchestrator` : questions, appels embedder/retriever/LLM, tokens, coûts, auth.
- `rag_retriever` : recherches, chunks retournés, sauvegardes, erreurs ChromaDB.
- `rag_mcp` : appels d'outil, appels orchestrator, auth machine, cache token sans exposer le token.
- `rag_ihm` : erreurs OAuth/OIDC, questions envoyées, latence perçue.

## Workflow

Avant de modifier : identifier le service, lire l'observabilité existante, repérer les opérations métier importantes, les dépendances externes, les métriques déjà exposées et les données sensibles.

Pendant la modification : ajouter uniquement les logs, métriques et spans utiles, préserver le comportement, garder une cardinalité faible et adapter Prometheus/Grafana si nécessaire.

Après modification : vérifier les tests pertinents en respectant l'organisation `rag_embedder` (`tests/unit_tests`, `tests/integration_tests`, `tests/conftest.py`), `/metrics` si exposé, l'absence de données sensibles, la cardinalité des labels et la lisibilité dans Grafana/Loki/Tempo lorsque la stack est disponible.

## Commandes utiles

```bash
uv run pytest
uv run ruff check .
docker compose config
```

Ne pas lancer ou redémarrer toute la stack Docker si ce n'est pas nécessaire.

## Format de réponse

Après une modification de l'observabilité, répondre avec : résumé, fichiers modifiés, logs/métriques/traces ajoutés, dashboards/alertes touchés, validations, limites.

Pour une recommandation sans modification, répondre avec : manque identifié, intérêt opérationnel, solution recommandée, pièges à éviter.
