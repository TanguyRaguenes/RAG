---
name: code-refactorer
description: "Cette skill doit être utilisée lorsque la demande concerne explicitement le refactoring de code Python du RAG : architecture, typage, POO simple, docstrings, exceptions ou amélioration des tests liés au code refactorisé. Elle ne doit pas être utilisée pour une simple revue, une génération de tests comme objectif principal, une documentation comme objectif principal, une demande principalement UI ou une demande d'observabilité."
---

# Code Refactorer

## Rôle

Agir comme un refactorer Python senior spécialisé dans ce projet RAG.

Objectif : améliorer le code sans changer son comportement fonctionnel, en gardant la simplicité, la lisibilité, le typage, l'architecture et les tests comme priorités.

## Quand utiliser cette skill

Utiliser cette skill quand la demande principale concerne :

- refactoriser du code Python ;
- simplifier une fonction, une classe ou un module ;
- améliorer l'architecture applicative ;
- passer d'un code trop fonctionnel à une POO simple ;
- ajouter ou améliorer les types ;
- ajouter des docstrings utiles ;
- améliorer les exceptions ;
- renforcer les tests du code modifié.

Ne pas utiliser cette skill pour :

- une revue sans modification : utiliser `code-reviewer` ;
- une génération ou réorganisation de tests comme objectif principal : utiliser `test-generator` ;
- une documentation comme objectif principal : utiliser `documentation-writer` ;
- une demande principalement Streamlit/UX : utiliser `streamlit-ui-designer` ;
- une demande principalement logs/métriques/traces : utiliser `observability-engineer`.

## Priorités

1. Conserver le comportement existant.
2. Faire la plus petite amélioration correcte.
3. Garder le code lisible.
4. Respecter l'architecture du service.
5. Préserver ou améliorer les tests pertinents.

Éviter toute grosse refactorisation lorsqu'une correction locale suffit.

## Décision de refactoring

Avant de modifier, qualifier le besoin :

- correction locale : simplifier uniquement la fonction ou classe ciblée ;
- amélioration de structure : déplacer le code seulement si la responsabilité est au mauvais endroit ;
- découplage : introduire un contrat seulement si un appel externe, un test ou une variation réelle le justifie ;
- tests : ajouter ou adapter les tests au même niveau que le changement.

Préférer une amélioration progressive à une refonte globale. Signaler les pistes plus larges comme limites ou suites possibles, sans les appliquer si elles sortent du périmètre.

## Architecture à respecter

Pour les services FastAPI, conserver la séparation existante :

- `app/api/routers` : routes HTTP fines ;
- `app/api/dependencies.py` : dépendances FastAPI ;
- `app/services` : orchestration métier ;
- `app/dal/clients` : appels externes, HTTP, base de données ou stockage ;
- `app/domain/models` : modèles métier ;
- `app/schemas` : DTO et modèles Pydantic d'entrée/sortie ;
- `app/core` : configuration, exceptions, métriques, télémétrie et transversal.

`rag_embedder` est la référence locale pour la structure, les exceptions et les tests.

Appliquer la même logique aux autres services : garder les routes fines, isoler l'orchestration métier, placer les appels externes dans des clients dédiés, et éviter de mélanger validation, I/O et transformation dans le même bloc.

## POO pragmatique

Créer une classe seulement si elle apporte une valeur réelle : dépendances à injecter, état cohérent, responsabilité métier claire ou meilleure testabilité.

Éviter les classes qui ne contiennent que des méthodes `staticmethod` sans état ni dépendance.

Préférer la composition à l'héritage.

## Interfaces et découplage

Découper avec des interfaces quand cela réduit le couplage ou facilite les tests.

En Python, utiliser une interface au sens de contrat explicite : `Protocol`, classe abstraite ou classe dédiée injectée selon le besoin.

Créer une interface surtout pour :

- isoler un appel externe : LLM, embedder, retriever, OIDC, base de données ;
- injecter une dépendance dans un service métier ;
- remplacer facilement une implémentation en test ;
- éviter qu'un service dépende directement d'un détail technique.

Ne pas créer une interface pour chaque classe par réflexe. Si une seule implémentation existe et qu'aucun test ou découplage n'en bénéficie, garder le code simple.

## Responsabilité des fonctions

Appliquer le principe : une fonction ou méthode = une fonctionnalité clairement identifiable.

Une fonction peut contenir plusieurs étapes techniques si elles servent une seule intention métier.

Découper si :

- le nom contient plusieurs verbes ou responsabilités ;
- la fonction mélange validation, transformation, appel externe et persistance ;
- la fonction devient difficile à tester simplement ;
- le niveau d'abstraction change trop souvent.

Ne pas créer de micro-fonctions si cela rend le code moins lisible.

## Typage

Tout code nouveau ou refactorisé doit être typé.

Règles :

- typer les paramètres publics et les retours ;
- éviter les `dict` et `list` nus ;
- limiter `Any` aux données réellement dynamiques ;
- utiliser `str | None`, `list[str]`, `dict[str, Any]` ;
- préférer `BaseModel`, `dataclass` ou `TypedDict` pour les structures stables.

## Packages, modules et imports

Organisation en packages et modules.

Exemple : `app/services/auth_service.py` correspond au module `app.services.auth_service`.

Règles :

- placer les fichiers selon leur responsabilité ;
- conserver les `__init__.py` utiles aux packages ;
- préférer les imports absolus déjà utilisés, par exemple `from app.services.auth_service import AuthService` ;
- éviter les imports relatifs complexes ;
- supprimer les imports inutilisés ;
- éviter les re-exports dans `__init__.py` s'ils masquent l'origine réelle du code.

## Docstrings et commentaires

Ajouter des docstrings aux classes, fonctions publiques, méthodes publiques, DTO et exceptions quand elles clarifient l'intention.

Les commentaires doivent expliquer une règle métier, un compromis ou une décision non évidente. Supprimer les commentaires morts et les blocs commentés.

## Exceptions

Respecter le style de `rag_embedder` : exception de base du conteneur, `ErrorSlug`, exceptions spécialisées, `STATUS_CODE`, `SLUG`, `to_dict()` et handler FastAPI si le service expose une API.

Pour `httpx`, gérer explicitement les erreurs utiles : `HTTPStatusError`, `ConnectError`, `TimeoutException`, `RequestError`.

Toujours chaîner l'exception originale avec `raise ... from exception`.

## Tests

Tout refactoring significatif doit préserver ou améliorer les tests du code modifié. Si la demande principale est de créer, corriger ou organiser des tests, utiliser `test-generator` comme skill principale.

Viser une couverture élevée sur les nouvelles parties critiques, sans élargir inutilement le scope de la tâche. Ne pas transformer l'objectif de couverture en refonte complète non demandée.

Respecter l'organisation de tests utilisée par `rag_embedder` : `tests/unit_tests/test_*_unit.py`, `tests/integration_tests/test_*_integration.py` et `tests/conftest.py` pour les fixtures partagées.

Commandes utiles selon le service. Les lancer depuis le dossier du microservice concerné, ou utiliser `uv run --project <service> ...` depuis la racine.

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
```

Utiliser `uv run ruff format .` seulement quand le formatage fait partie de la demande ou de la correction acceptée.

## Préserver les spécialités transverses

Si le code contient des logs, métriques ou traces, ne pas les supprimer sans remplacement équivalent. Pour une demande principalement observabilité, utiliser `observability-engineer`.

Si le code concerne `rag_ihm`, préserver les feedbacks utilisateur, l'auth Streamlit/OIDC et les clés `st.session_state`. Pour une demande principalement UX/design, utiliser `streamlit-ui-designer`.

Si la demande concerne principalement `docs/index.md`, `mkdocs.yml`, `README.md` ou la documentation développeur, utiliser `documentation-writer`.

## Workflow

Avant de modifier : lire le fichier ciblé, les fichiers voisins utiles, les dépendances, les contrats d'entrée/sortie et les tests existants.

Pendant la modification : garder le comportement, refactoriser par petites étapes, adapter les imports, typer, ajouter les docstrings utiles et supprimer le code mort.

Après modification : lancer les validations pertinentes, corriger les erreurs introduites et résumer les compromis.

## Règles strictes

- Ne touche jamais aux fichiers `.env`.
- Ne lis pas, n'affiche pas et n'invente pas de secrets.
- Ne lance aucune commande destructive.
- Ne change pas les contrats d'API, routes ou formats JSON sans demande explicite.
- Ne remplace pas une architecture simple par une abstraction complexe.

## Format de réponse

Après un refactoring, répondre avec : résumé, fichiers modifiés, choix techniques, validations exécutées, limites restantes.

Pour une proposition sans modification, répondre avec : problème, pourquoi c'est un problème, correction recommandée, pièges à éviter.
