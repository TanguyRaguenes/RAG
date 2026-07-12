---
name: project-quality-runner
description: "Cette skill doit être utilisée lorsque la demande concerne la maintenance qualité globale du RAG : mettre à jour les locks uv, synchroniser les dépendances, lancer les tests pytest de chaque microservice avec une couverture minimale de 70 %, puis exécuter ruff check --fix, ruff format et ruff check à la racine du projet."
---

# Project Quality Runner

## Rôle

Agir comme un ingénieur qualité chargé de vérifier l'état global du monorepo RAG sans modifier le code métier inutilement.

Objectif : exécuter de façon méthodique les commandes de maintenance `uv`, les tests avec couverture et les contrôles `ruff`, puis restituer clairement les services en succès, les échecs et les actions nécessaires.

## Quand utiliser cette skill

Utiliser cette skill quand la demande principale concerne :

- mettre à jour les fichiers `uv.lock` du projet ou des microservices ;
- synchroniser les dépendances avec `uv sync` ;
- lancer tous les tests des microservices ;
- vérifier que la couverture pytest atteint au moins 70 % ;
- appliquer `ruff check --fix` et `ruff format` à la racine ;
- valider ensuite que `ruff check` passe sans erreur.

Ne pas utiliser cette skill pour :

- créer ou corriger des tests comme objectif principal : utiliser `test-generator` ;
- refactoriser du code Python : utiliser `code-refactorer` ;
- faire une simple revue sans exécution : utiliser `code-reviewer` ;
- modifier la documentation comme objectif principal : utiliser `documentation-writer`.

## Périmètre projet

Exécuter les commandes depuis la racine du dépôt `D:\Projets\RAG`, puis dans chaque microservice Python disposant d'un `pyproject.toml`.

Microservices actuellement attendus :

- `rag_embedder` ;
- `rag_retriever` ;
- `rag_reranker` ;
- `rag_orchestrator` ;
- `rag_evaluator` ;
- `rag_ihm` ;
- `rag_mcp`.

Si la liste évolue, détecter les microservices par la présence d'un fichier `pyproject.toml` dans un dossier de premier niveau `rag_*`. Ne pas traiter les dossiers d'environnement virtuel, caches, build, documentation ou observabilité comme des microservices Python.

## Règles de sécurité

- Ne jamais lire, afficher ou modifier les fichiers `.env` ni les secrets.
- Ne jamais utiliser de commande destructive comme `git reset --hard`, `git clean`, `Remove-Item` sur des fichiers du projet ou suppression de locks.
- Ne pas corriger du code métier automatiquement si l'objectif est uniquement d'exécuter la qualité globale.
- Ne pas masquer un échec de test, de couverture, de lock ou de lint.
- Signaler les fichiers modifiés par `uv lock --upgrade`, `uv sync`, `ruff check --fix` ou `ruff format`.

## Workflow obligatoire

### 1. Préparation

Vérifier l'état de travail avec `git status --short` avant de lancer les commandes.

Identifier les microservices Python avec `pyproject.toml` :

```powershell
Get-ChildItem -Directory -Filter "rag_*" | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "pyproject.toml") }
```

Préférer les outils de recherche Kilo (`glob`, `grep`, `read`) pour inspecter les fichiers. Utiliser le shell uniquement pour les commandes de validation, `uv`, `pytest`, `ruff` et `git`.

### 2. Mise à jour des dépendances

À la racine du projet, exécuter dans cet ordre :

```powershell
uv lock --upgrade
uv sync
```

Dans chaque microservice, exécuter dans cet ordre avec le répertoire de travail du service :

```powershell
uv lock --upgrade
uv sync
```

Si `uv lock --upgrade` ou `uv sync` échoue dans un service, noter l'échec et ne pas lancer les tests de ce service avant résolution de la synchronisation.

### 3. Tests et couverture

Dans chaque microservice synchronisé avec succès, lancer les tests avec un seuil de couverture minimal de 70 %.

Commande préférée si la configuration pytest/cov du service est déjà définie dans `pyproject.toml` :

```powershell
uv run pytest --cov-fail-under=70
```

Commande de repli si le service n'a pas de configuration coverage exploitable :

```powershell
uv run pytest --cov=. --cov-fail-under=70
```

Vérifier explicitement trois points pour chaque service :

- la commande `pytest` se termine avec un code de sortie 0 ;
- aucun test n'est en erreur ou en échec ;
- le seuil de couverture de 70 % est atteint.

Si `pytest-cov` n'est pas installé, signaler que la couverture ne peut pas être vérifiée et considérer le service comme non validé tant que la dépendance ou la configuration n'est pas corrigée.

### 4. Ruff à la racine

Après les tests des microservices, revenir à la racine du projet et exécuter :

```powershell
uv run ruff check --fix
uv run ruff format
uv run ruff check
```

Si `ruff` n'est pas disponible via `uv run`, essayer uniquement si cohérent avec le projet :

```powershell
ruff check --fix
ruff format
ruff check
```

Ne pas lancer `ruff` service par service sauf demande explicite ou configuration projet l'exigeant.

### 5. Vérification finale

Relancer `git status --short` après les commandes pour lister les fichiers modifiés.

Produire un bilan court avec :

- résultat de `uv lock --upgrade` et `uv sync` à la racine ;
- résultat de `uv lock --upgrade` et `uv sync` par microservice ;
- résultat pytest et couverture par microservice ;
- résultat final de `ruff check` ;
- fichiers modifiés ;
- erreurs restantes et action recommandée.

## Bonnes pratiques d'exécution

- Utiliser le paramètre `workdir` des outils d'exécution plutôt que `cd` dans les commandes.
- Exécuter les services un par un pour isoler clairement les erreurs.
- Conserver les sorties utiles des commandes en cas d'échec, surtout les erreurs de résolution `uv`, les tests échoués et le rapport de couverture.
- Ne pas interpréter un simple `uv sync` réussi comme une validation fonctionnelle : seuls tests, couverture et `ruff check` final valident la qualité.
- Ne pas annoncer que tout est OK si un service n'a pas été testé ou si sa couverture n'a pas été mesurée.

## Pièges à éviter

- Oublier la racine du monorepo avant les microservices.
- Lancer `pytest` sans vérifier le seuil `--cov-fail-under=70`.
- Confondre `ruff check --fix` avec une validation finale : toujours relancer `ruff check` après le formatage.
- Continuer à tester un microservice dont les dépendances ne sont pas synchronisées.
- Modifier les fichiers `.env`, secrets ou configurations locales non demandées.
