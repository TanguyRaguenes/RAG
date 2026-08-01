---
name: microservice-architecture-refactorer
description: "Cette skill doit être utilisée pour auditer puis refactoriser l'architecture complète d'un seul microservice Python du RAG : routers fins, dépendances FastAPI, services métier, DAL, modèles de domaine, schémas Pydantic, configuration, POO pragmatique, interfaces, typage, commentaires utiles et tests. Elle convient lorsqu'un microservice mélange les couches ou contient de la logique métier dans ses routes. Elle ne doit pas être utilisée pour une correction locale, plusieurs microservices simultanément, les exceptions/logs comme objectif principal, une demande principalement UI ou une simple revue sans modification."
---

# Microservice Architecture Refactorer

## Rôle

Remettre un microservice du RAG en conformité avec une architecture en couches simple, typée et compréhensible par un développeur découvrant le projet.

Préserver le comportement public et refactoriser par petites étapes vérifiables plutôt que réécrire le service.

## Quand utiliser cette skill

Utiliser cette skill pour un seul microservice lorsque la demande principale concerne :

- la présence de logique métier dans un router ou une page de transport ;
- un découpage incohérent entre API, services, DAL, domaine et schémas ;
- une dépendance directe du métier envers `httpx`, `asyncpg`, ChromaDB, Streamlit ou un SDK externe ;
- une orchestration métier difficile à tester ;
- des DTO externes placés dans le domaine ;
- des `dict[str, Any]` utilisés comme contrats stables ;
- l'introduction raisonnée de classes, de `Protocol` ou d'injection de dépendances ;
- la simplification, le typage et la clarification de l'ensemble d'un microservice.

Ne pas utiliser cette skill pour :

- une correction locale dans une fonction ou un module : utiliser `code-refactorer` ;
- une simple revue sans modification : utiliser `code-reviewer` ;
- les exceptions et logs comme objectif principal : utiliser `microservice-error-standardizer` ;
- les métriques, traces, dashboards ou alertes : utiliser `observability-engineer` ;
- une génération de tests comme objectif principal : utiliser `test-generator` ;
- une refonte Streamlit principalement visuelle : utiliser `streamlit-ui-designer` ;
- plusieurs microservices en une seule exécution : appliquer cette skill séparément à chaque service.

## Architecture cible

Pour un service FastAPI, respecter :

- `app/api/routers` : transport HTTP uniquement ;
- `app/api/dependencies.py` : construction et injection des dépendances FastAPI ;
- `app/services` : cas d'usage et orchestration métier ;
- `app/dal/clients` : appels HTTP et SDK externes ;
- `app/dal/repositories` : persistance SQL ou vectorielle si ce dossier existe ;
- `app/dal/files` : lecture et écriture de fichiers si nécessaire ;
- `app/domain/models` : concepts métier indépendants du transport et des frameworks ;
- `app/schemas` : DTO Pydantic d'entrée, sortie et contrats interservices ;
- `app/core` : configuration, exceptions, logs, métriques, télémétrie et transversal.

Adapter la même séparation à MCP et Streamlit sans créer artificiellement des routers FastAPI.

Consulter `references/layer-checklist.md` pour décider où placer chaque responsabilité et contrôler les imports.

## Principes obligatoires

- Préserver routes, méthodes HTTP, statuts, payloads, variables d'environnement, métriques, traces et comportement de base de données.
- Ne jamais lire ni modifier les fichiers `.env` ou les secrets.
- Faire la plus petite modification permettant une frontière claire.
- Ne pas créer de couche, classe ou interface sans responsabilité réelle.
- Ne pas transformer toutes les fonctions en classes.
- Ne pas ajouter de compatibilité transitoire sans consommateur concret.
- Ne pas cacher une erreur de contrat derrière un `dict` permissif ou une valeur par défaut arbitraire.
- Ne pas déplacer du code avant d'avoir lu ses appels et ses tests.
- Ne pas supprimer une instrumentation existante sans remplacement équivalent.
- Ne pas ajouter de migration automatique au démarrage ; respecter la stratégie de base vide du projet lorsque le modèle change.

## Workflow

### 1. Délimiter le microservice

- Vérifier le dossier cible, son framework, son `pyproject.toml`, son point d'entrée et ses tests.
- Lire les instructions `AGENTS.md` applicables.
- Examiner l'état Git sans modifier ni annuler les changements existants.
- Cartographier les dossiers `api`, `services`, `dal`, `domain`, `schemas` et `core`.
- Rechercher les routes, dépendances, appels externes, accès SQL/stockage, modèles Pydantic, classes et `Protocol`.

### 2. Verrouiller les contrats

- Identifier les routes, paramètres, statuts et payloads publics.
- Identifier les contrats interservices réellement consommés.
- Identifier les variables de configuration, collections, tables et effets persistants.
- Identifier les logs, métriques et traces à préserver.
- Ajouter ou renforcer les tests de contrat avant un déplacement risqué.

### 3. Classer les responsabilités

- Lister chaque responsabilité mal placée avec son emplacement cible.
- Prioriser les bugs et violations de frontière avant le style.
- Déplacer une responsabilité à la fois.
- Éviter les renommages ou découpages non nécessaires au déplacement.

### 4. Affiner la couche de transport

- Limiter un router FastAPI à recevoir le DTO, résoudre les dépendances, appeler un cas d'usage et retourner le DTO de réponse.
- Retirer du router quotas, choix de fournisseur, persistance, orchestration RAG, calcul métier et gestion de cycle de session.
- Conserver uniquement les préoccupations HTTP : `Depends`, headers, path/query parameters, status code et `response_model`.
- Faire appeler une seule méthode de service par route lorsque cela clarifie le flux.

### 5. Construire les dépendances

- Construire les clients, repositories et services dans `api/dependencies.py` ou dans le lifespan si un cycle de vie est requis.
- Réutiliser les clients HTTP, pools et SDK lorsque leur cycle de vie le justifie.
- Fermer les ressources au shutdown.
- Injecter des contrats métier dans les services plutôt que des objets FastAPI ou SDK.

### 6. Isoler l'orchestration métier

- Créer une classe de service lorsqu'un cas d'usage possède plusieurs dépendances, un état cohérent ou un cycle de vie.
- Garder une fonction pure lorsqu'elle transforme, trie, calcule ou formate sans dépendance externe.
- Garantir les blocs `try/finally` pour les sessions, verrous et ressources métier.
- Découper un service seulement si plusieurs responsabilités indépendantes sont réellement présentes.

### 7. Isoler le DAL

- Placer chaque appel HTTP, SQL, stockage, fichier ou SDK dans un adaptateur DAL.
- Retourner un DTO, un modèle métier ou une valeur Python stable, jamais un objet concret du SDK.
- Valider immédiatement JSON, longueurs de collections, champs obligatoires et valeurs numériques à la frontière.
- Conserver les règles métier de tri, quota, sélection et enrichissement dans les services.
- Éviter qu'un repository devienne un service métier caché.

### 8. Séparer domaine et schémas

- Placer dans `schemas` les requêtes/réponses HTTP, payloads interservices et modèles Pydantic de transport.
- Placer dans `domain/models` uniquement les concepts métier indépendants de FastAPI, HTTP et des fournisseurs.
- Accepter un domaine vide si aucun modèle métier distinct n'est nécessaire.
- Éviter de dupliquer le même modèle sous plusieurs noms.

### 9. Appliquer une POO pragmatique

- Utiliser une classe pour un service orchestrant plusieurs dépendances ou pour un client avec cycle de vie.
- Utiliser `Protocol` pour une frontière externe injectée et remplacée dans les tests.
- Préférer `Protocol` à une hiérarchie d'héritage lorsque seul le contrat compte.
- Garder les fonctions pures pour le chunking, les métriques, le formatage, le tri et les constructions déterministes.
- Éviter les classes ne contenant que des `staticmethod`.

### 10. Renforcer le typage

- Typer tous les paramètres et retours publics.
- Typer les dépendances injectées, callbacks, lifespans et collections.
- Remplacer les `dict[str, Any]` stables par `BaseModel`, `dataclass`, `TypedDict` ou modèle métier.
- Conserver `Any` uniquement aux frontières réellement dynamiques et valider immédiatement.
- Ne pas annoter chaque variable locale évidente ; préférer des contrats de fonction précis.

### 11. Simplifier commentaires et docstrings

- Nommer clairement modules, classes, fonctions et variables avant d'ajouter un commentaire.
- Ajouter une docstring Google seulement lorsqu'elle explique le rôle, les paramètres utiles, le retour ou une exception réellement propagée.
- Commenter une règle métier, un compromis ou une contrainte non évidente.
- Supprimer les commentaires qui paraphrasent le code, les blocs morts et les affirmations devenues fausses.
- Préférer une fonction courte et typée à une longue explication narrative.

### 12. Adapter les tests

- Tester les routers comme contrats HTTP avec dépendances substituées.
- Tester les services avec fakes conformes aux `Protocol`.
- Tester les clients DAL avec transport HTTP simulé ou doubles de SDK.
- Ajouter des tests de contrat interservice lorsque deux schémas évoluent ensemble.
- Couvrir succès, erreur externe, payload invalide, cas vide, concurrence ou cleanup selon le cas d'usage.
- Ne pas sur-mocker les fonctions pures.

### 13. Vérifier les imports et frontières

- Vérifier qu'un router n'importe aucun repository ou SDK externe.
- Vérifier qu'un service n'importe ni FastAPI, ni Streamlit, ni objet concret de stockage.
- Vérifier que le domaine n'importe ni Pydantic de transport, ni DAL, ni framework.
- Vérifier que le DAL n'implémente pas de politique métier.
- Vérifier que `core` ne dépend pas des couches métier ou transport.

### 14. Valider

Lancer depuis le dossier du microservice :

```bash
uv run pytest
uv run ruff check .
uv run ruff check --select ANN app
uv run ruff format --check .
```

Lancer les tests d'intégration uniquement si leurs dépendances externes sont disponibles ou explicitement opt-in.

Depuis la racine, lancer `git diff --check -- <microservice>` et vérifier que seuls les fichiers du périmètre ont changé.

## Critères de sortie

Considérer le refactoring terminé uniquement si :

- les routes et points d'entrée sont limités au transport ;
- l'orchestration métier est dans `services` ;
- les appels externes et la persistance sont isolés dans le DAL ;
- les DTO et modèles métier sont séparés ;
- les objets SDK ne traversent plus les couches ;
- les classes et interfaces ajoutées ont une utilité concrète ;
- le code applicatif modifié est typé ;
- les commentaires expliquent uniquement les éléments non évidents ;
- les contrats publics et l'observabilité existante sont préservés ;
- les tests et contrôles qualité passent.

## Format de réponse

Répondre avec :

- le microservice traité ;
- les responsabilités déplacées entre couches ;
- les classes, interfaces et DTO introduits ou supprimés ;
- les simplifications et contrats préservés ;
- les fichiers modifiés ;
- les tests et contrôles exécutés ;
- les limites ou intégrations non vérifiées.
